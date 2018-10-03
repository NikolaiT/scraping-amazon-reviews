# Scraping Amazon Reviews

In order to run the scraper, you need to first clone the repository.

```
git clone https://github.com/NikolaiT/scraping-amazon-reviews
```

Then you need to download the headless chrome browser and the chrome driver. You can do so with this command.

```
./setup.sh
```

Now you can scrape amazon reviews by editing the file `scraper.py` and add some amazon product urls you want to have the reviews from:

```
if __name__ == '__main__':
    config = {
    "urls": [
      "https://www.amazon.de/Crocs-Crocband-Unisex-Erwachsene-Charcoal-Ocean/dp/B007B9MI8K/ref=sr_1_1?s=shoes&ie=UTF8&qid=1537363983&sr=1-1",
      "https://www.amazon.de/Samsung-UE55MU6179U-Fernseher-Triple-Schwarz/dp/B06XGS3Q4Y/ref=sr_1_4?s=home-theater&ie=UTF8&qid=1538584798&sr=1-4&keywords=tv",
      "https://www.amazon.de/gp/product/B07BKN76JS/ref=s9_acsd_zwish_hd_bw_bDtHh_cr_x__w?pf_rd_m=A3JWKAKR8XB7XF&pf_rd_s=merchandised-search-8&pf_rd_r=TM716ESMTY46877D33XM&pf_rd_r=TM716ESMTY46877D33XM&pf_rd_t=101&pf_rd_p=5f7031a3-d321-54f0-8d79-d0961244d5fa&pf_rd_p=5f7031a3-d321-54f0-8d79-d0961244d5fa&pf_rd_i=3310781"
    ]}
    main(config)
```

Then just run the scraper:

```
python src/scraper.py
```
