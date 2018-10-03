from __future__ import print_function
import os
import json
import pprint
import time
import random
import logging
from webdriver_wrapper import WebDriverWrapper, AmazonDetectionException

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def random_sleep(r):
    min, max = r
    assert max>min
    sleepy_time = random.randrange(min, max)
    time.sleep(sleepy_time)
    logger.info('sleeping for {} s'.format(sleepy_time))

def scrape_amazon_reviews(config):
    """
    Scrapes amazon reviews.
    """
    urls = config['urls']
    sleep_range = (1, 3)

    driver = WebDriverWrapper()

    try:
        for i, product_url in enumerate(urls):

            driver.open_amazon_product(product_url)
            driver.scrape_reviews()

            # sleep a bit
            if sleep_range:
                random_sleep(sleep_range)

    except AmazonDetectionException as e:
        logger.fatal('Amazon detected the scraping. Aborting.')
        pass

    pprint.pprint(driver.results)

    driver.close()
    logger.info('Got {} results out from {} urls'.format(len(driver.results.keys())-3, len(urls)))

    return driver.results, driver.status


# this is the lambda function
def main(config):
    data, status = scrape_amazon_reviews(config)

    return {
        "statusCode": status,
        "body": json.dumps(data)
    }

if __name__ == '__main__':
    config = {
    "urls": [
      "https://www.amazon.de/Crocs-Crocband-Unisex-Erwachsene-Charcoal-Ocean/dp/B007B9MI8K/ref=sr_1_1?s=shoes&ie=UTF8&qid=1537363983&sr=1-1",
    ]}
    main(config)
