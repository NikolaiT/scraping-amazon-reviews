import os
import shutil
import uuid
import json
import logging
import io
import csv
import time
import datetime
from user_agents import random_ua

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException, ElementNotVisibleException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

__author__ = 'Nikolai Tschacher'
__url__ = 'https://incolumitas.com/'
__version__ = '0.2'

class AmazonDetectionException(Exception):
    pass

class WebDriverWrapper:
    def __init__(self):

        self.status = 200
        self.results = {
            'initialized': str(datetime.datetime.now()),
            'data': [],
        }
        self.ipinfo = {}
        self.save_debug_screenshot = False
        self.max_review_pages = 3

        chrome_options = webdriver.ChromeOptions()
        self._tmp_folder = '/tmp/{}'.format(uuid.uuid4())

        if not os.path.exists(self._tmp_folder):
            os.makedirs(self._tmp_folder)

        self.user_data_path = os.path.join(self._tmp_folder, 'user-data/')

        if not os.path.exists(self.user_data_path):
            os.makedirs(self.user_data_path)

        self.data_path = os.path.join(self._tmp_folder, 'data-path/')

        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)

        self.cache_dir = os.path.join(self._tmp_folder, 'cache-dir/')

        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        logging.basicConfig(
            format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("{}.log".format(os.path.join(self.data_path, 'google-scraper'))),
                logging.StreamHandler()
            ])

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1280x1696')
        chrome_options.add_argument('--user-data-dir={}'.format(self.user_data_path))
        chrome_options.add_argument('--hide-scrollbars')
        chrome_options.add_argument('--enable-logging')
        chrome_options.add_argument('--log-level=0')
        chrome_options.add_argument('--v=99')
        chrome_options.add_argument('--single-process')
        chrome_options.add_argument('--data-path={}'.format(self.data_path))
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--homedir={}'.format(self._tmp_folder))
        chrome_options.add_argument('--disk-cache-dir={}'.format(self.cache_dir))
        chrome_options.add_argument('user-agent={}'.format(random_ua))

        chrome_options.binary_location = os.path.join(os.getcwd(), 'bin/headless-chromium')

        self._driver = webdriver.Chrome(chrome_options=chrome_options)

    def get_url(self, url):
        self._driver.get(url)

    def set_input_value(self, xpath, value):
        elem_send = self._driver.find_element_by_xpath(xpath)
        elem_send.send_keys(value)

    def click(self, xpath):
        elem_click = self._driver.find_element_by_xpath(xpath)
        elem_click.click()

    def save_screen(self, fname):
        self._driver.save_screenshot(os.path.join(self.user_data_path, fname))

    def save_html(self, path=''):
        with open(path, 'w') as f:
            f.write(self._driver.page_source)

    def get_inner_html(self, xpath):
        elem_value = self._driver.find_element_by_xpath(xpath)
        return elem_value.get_attribute('innerHTML')

    def get_html(self):
        return self._driver.page_source

    def check_ip(self):
        self.get_url('https://ipinfo.io/json')
        try:
            pre = WebDriverWait(self._driver, 2).until(
                EC.visibility_of_element_located((By.TAG_NAME, 'pre')))
            self.ipinfo = json.loads(pre.text)
            self.results['ipinfo'] = self.ipinfo
        except TimeoutException:
            self.status = 400
            self.logger.warning('Cannot get ipinfo json.')

    def open_amazon_product(self, url):
        self.product_url = url

        self.get_url(url)

        search_input = None
        try:
            search_input = WebDriverWait(self._driver, 5).until(
                EC.visibility_of_element_located((By.ID, 'acrCustomerReviewLink')))
            self.logger.info('Got a customer review link.')
        except TimeoutException:
            self.status = 400
            self.logger.error('No customer review link located after 5 seconds.')

        # check whether google blocked us
        self.handle_detection()

    def scrape_reviews(self):
        try:
            review_link = self._driver.find_element_by_css_selector('a[data-hook="see-all-reviews-link-foot"]')
            link = review_link.get_attribute('href')
            self.get_url(link)
        except WebDriverException as e:
            self.status = 400
            self.logger.error('Cannot locate to amazon all reviews: {}'.format(e))

        # here the page source of the reviews should become available
        try:
            WebDriverWait(self._driver, 5).until(
                EC.visibility_of_element_located((By.ID, 'cm_cr-product_info')))
            self.logger.info('review page loaded')
        except TimeoutException:
            self.status = 400
            self.logger.error('Cannot load review page')

        # check whether google blocked us
        self.handle_detection()

        # debug screenshot
        if self.save_debug_screenshot:
            self.save_screen('{}.png'.format(keyword.strip()))

        self.num_review_page = 0

        while self.num_review_page < self.max_review_pages:
            # now we can scrape the results out of the html
            self.num_review_page += 1
            self.parse_review_results()

            try:
                next_reviews_page = self._driver.find_element_by_css_selector('#cm_cr-pagination_bar .a-last a')
                self.get_url(next_reviews_page.get_attribute('href'))
                WebDriverWait(self._driver, 5).until(
                    EC.visibility_of_element_located((By.ID, 'cm_cr-product_info')))
            except WebDriverException as e:
                self.status = 400
                self.logger.error('Cannot go next page: {}'.format(e))
                break

    def parse_review_results(self):
        # now we can scrape the results out of the html
        data = {
            'product': self.product_url,
            'time': str(datetime.datetime.now()),
            'average_stars': '',
            'total_reviews': '',
            'num_reviews_scraped': 0,
            'reviews': [],
        }
        all_links = []

        try:
            data['average_stars'] = self._driver.find_element_by_css_selector('[data-hook="rating-out-of-text"]').text
            data['total_reviews'] = self._driver.find_element_by_css_selector('[data-hook="total-review-count"]').text
        except NoSuchElementException as e:
            self.logger.warning('Cannot scrape {}'.format(e))

        try:
            all_reviews = self._driver.find_elements_by_css_selector('#cm_cr-review_list div[data-hook="review"]')
        except NoSuchElementException as e:
            self.logger.warning('Cannot find reviews container: {}'.format(e))

        for i, result in enumerate(all_reviews):
            data['reviews'].append(self.scrape_single_review(result))
            data['num_reviews_scraped'] += 1

        # highest voted positive review
        # positive = self._driver.find_element_by_css_selector('.positive-review')
        # data['positive'] = self.scrape_single_review(positive)

        # highest voted critical review
        # critical = self._driver.find_element_by_css_selector('.critical-review')
        # data['critical'] = self.scrape_single_review(critical)

        self.results['review-page-{}'.format(self.num_review_page)] = data
        self.results['last_scrape'] = str(datetime.datetime.now())

    def scrape_single_review(self, result):
        selectors = {
            'title': '[data-hook="review-title"]',
            'author': '[data-hook="review-author"]',
            'date': '[data-hook="review-date"]',
            'rating': '[data-hook="review-star-rating"]',
            'helpful_vote': '[data-hook="helpful-vote-statement"]',
            'verified_buy': '[data-hook="avp-badge"]',
            'body': '[data-hook="review-body"]',
        }
        results = dict()

        for key, selector in selectors.items():
            try:
                element = result.find_element_by_css_selector(selector)
                results[key] = element.text
            except NoSuchElementException as e:
                self.logger.debug('Cannot scrape review results for selector {}'.format(selector))

        try:
            results['author_url'] = result.find_element_by_css_selector('a[data-hook="review-author"]').get_attribute('href')
            results['rating'] = result.find_element_by_css_selector('i[data-hook="review-star-rating"] span').text
        except NoSuchElementException as e:
            self.logger.warning('Cannot scrape addditional data: {}'.format(e))

        return results

    def detected_by_amazon(self):
        """
        I never actually was detected, therefore I this function is still useless.
        """
        needles = {
            'inurl': 'amazondetectionstring17734',
            'inhtml': 'amazondetectionstring674',
        }
        return needles['inurl'] in self._driver.current_url and needles['inhtml'] in self._driver.page_source

    def handle_detection(self):
        if self.detected_by_amazon():
            self.logger.error('Amazon detected us. Stop scraping.')
            self.status = '400'
            raise AmazonDetectionException('Google detected the scraping.')

    def store_json(self, data, fname):
        """Stores a dict in a file in the data directory.
        """
        path = os.path.join(self.data_path, '{}.json'.format(fname))
        with open(path, 'w') as f:
            json.dump(data, f)
        return path

    def close(self):
        # Close webdriver connection
        self._driver.quit()

        # Remove specific tmp dir of this "run"
        shutil.rmtree(self._tmp_folder)

        # Remove possible core dumps
        folder = '/tmp'
        for the_file in os.listdir(folder):
            file_path = os.path.join(folder, the_file)
            try:
                if 'core.headless-chromi' in file_path and os.path.exists(file_path) and os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(e)
