# Alibaba Scraper

Introduction
---
A web scraper to extract information (URL, name, price etc.) of items on alibaba.com by inspecting search results.

Requirements
---
- Python 3
- Scrapy
- Selenium
- Chrome webdriver
- MySQL (You can modify the code to use a different database)

Usage
---
- Create database tables by running `alibaba_scraper/db.py`  
- Run the spider once by `scrapy crawl alibaba` in your terminal
- Or run the spider periodically by running `alibaba_scraper/twisted_crawl.py`

Functionalities
---
- By default, this web scraper crawls 8 items (loaded statically) on each search result page.  
- If you want to crawl 40+ items fully on each page, 
replace the code in `alibaba_scraper/spiders/alibaba.py` with the code in `alibaba/spiders/alibaba_selenium.py` 
to load dynamic content with selenium webdriver.  
- By default, this web scraper has a 1-second delay between requests 
to avoid CAPTCHA. 
It is recommended to keep this delay for each IP even if you are using proxies.  
- The maximum speed for each IP is 8 items/second by using the delay. 
Encountering CAPTCHA will reduce the overall crawl speed.
