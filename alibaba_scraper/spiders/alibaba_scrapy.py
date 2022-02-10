import scrapy
from scrapy import signals

from alibaba_scraper.items import AlibabaItem

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import ActionChains
from selenium.common.exceptions import TimeoutException

import urllib.parse
import mysql.connector
import time
import re
from random import randint


def get_scraperapi_url(url):
    """Parse url to request from ScraperAPI, API key required"""

    payload = {'api_key': 'Your ScraperAPI Key', 'url': url}
    proxy_url = 'http://api.scraperapi.com/?' + urllib.parse.urlencode(payload)
    return proxy_url


def get_trailing_num(s):
    n = re.search(r'\d+$', s)
    return int(n.group()) if n else None


def get_item_xpath(row, search_page_url):
    """Generate AlibabaItem from xpath of data"""

    item = AlibabaItem()
    item['productLink'] = row.xpath(
        './/a[@class="elements-title-normal one-line"]/@href').get()
    item['name'] = row.xpath(
        './/a[@class="elements-title-normal one-line"]/@title').get()
    item['price'] = (row.xpath(
        './/span[@class="elements-offer-price-normal__price"]/text()'
    ).get() or row.xpath(
        './/span[@class="elements-offer-price-normal__promotion"]/text()').get())
    item['minOrder'] = row.xpath(
        './/span[@class="element-offer-minorder-normal__value"]/text()').get()
    item['sellerYear'] = row.xpath(
        './/span[@class="seller-tag__year flex-no-shrink"]/text()').get()
    item['sellerCountry'] = row.xpath(
        './/span[@class="seller-tag__country flex-no-shrink"]/@title').get()
    item['sellerLink'] = row.xpath(
        './/a[@class="fc3 fs12 text-ellipsis list-no-v2-decisionsup__element"]/@href').get()
    item['searchPageLink'] = search_page_url

    return item


def get_item_selenium(element, search_page_url):
    """Generate AlibabaItem from xpath of selenium element"""

    item = AlibabaItem()
    item['productLink'] = element.find_element_by_xpath(
        './/a[@class="elements-title-normal one-line"]').get_attribute('href')
    item['name'] = element.find_element_by_xpath(
        './/a[@class="elements-title-normal one-line"]').get_attribute('title')

    normal_price = element.find_elements_by_xpath(
        './/span[@class="elements-offer-price-normal__price"]')
    promotion_price = element.find_elements_by_xpath(
        './/span[@class="elements-offer-price-normal__promotion"]')
    if normal_price:
        item['price'] = normal_price[0].text
    elif promotion_price:
        item['price'] = promotion_price[0].text
    else:
        item['price'] = None
    item['minOrder'] = element.find_element_by_xpath(
        './/span[@class="element-offer-minorder-normal__value"]').text
    item['sellerYear'] = element.find_element_by_xpath(
        './/span[@class="seller-tag__year flex-no-shrink"]').text
    item['sellerCountry'] = element.find_element_by_xpath(
        './/span[@class="seller-tag__country flex-no-shrink"]').get_attribute('title')
    item['sellerLink'] = element.find_element_by_xpath(
        './/a[@class="fc3 fs12 text-ellipsis list-no-v2-decisionsup__element"]').get_attribute('href')
    item['searchPageLink'] = search_page_url
    return item


class AlibabaSpider(scrapy.Spider):
    name = 'alibaba'

    def __init__(self, **kwargs):
        """Initiate spider with database connection pool, blocked status, and close time"""

        super().__init__(**kwargs)
        dbconfig = {
            'host': 'localhost',
            'user': 'root',
            'password': 'root',
            'database': 'alibaba_scraper',
        }
        self.conn = mysql.connector.connect(pool_name="alibaba_pool", pool_size=32, **dbconfig)
        self.blocked = False
        # close time indicates the time after which no new request will be yielded
        self.close_time = time.time() + 60

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(AlibabaSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        spider.logger.info('Spider closed: %s', spider.name)

    def get_urls(self):
        """Generate urls according to scrape_progress table in database"""

        conn = mysql.connector.connect(pool_name="alibaba_pool")
        cursor = conn.cursor()
        cursor.execute('SELECT url, page_num FROM scrape_progress WHERE completed=0')
        rows = cursor.fetchall()
        urls = []
        for i in range(16):
            row = rows[i]
            urls.append(row[0] + str(row[1]))
        return urls

    def start_requests(self):
        urls = self.get_urls()
        for url in urls:
            # url=get_scraperapi_url(url)
            yield scrapy.Request(url=url, callback=self.parse_search_pages)

    def parse_search_pages(self, response):
        """
        Inspect page from response
        If there are items on page, yield AlibabaItem, request for the next page, and update scrape_progress
        If there is no search result, update scrape progress and mark the keyword as completed
        If there is CAPTCHA slider, open selenium webdriver to slide and then fetch information
        """
        url = response.url

        rows = response.xpath('//div[contains(@class, "J-offer-wrapper")]')
        page_num = get_trailing_num(url)
        next_page_num = page_num + 1
        base_url = url[:-len(str(page_num))]
        next_url = base_url + str(next_page_num)

        conn = mysql.connector.connect(pool_name="alibaba_pool")
        cursor = conn.cursor()

        # If there are items on page, yield AlibabaItem, request for the next page, and update scrape_progress
        if rows:
            for row in rows:
                cursor.execute('SELECT * FROM alibaba_item WHERE product_link=%s', (url,))
                if cursor.fetchall():
                    continue
                item = get_item_xpath(row, url)
                if item['productLink'] is not None:
                    yield item
            cursor.execute('UPDATE scrape_progress SET page_num=%s WHERE url=%s', (next_page_num, base_url))
            conn.commit()
            conn.close()
            print(f"Scraped from {url}")
            if time.time() < self.close_time and not self.blocked:
                yield scrapy.Request(url=next_url, callback=self.parse_search_pages)

        # If there is no search result, update scrape progress and mark the keyword as completed
        elif response.xpath('//div[@class="txt-wrap"]'):
            print(f"Completed {base_url} at page {page_num}")
            cursor.execute('UPDATE scrape_progress SET completed=1 WHERE url=%s', (base_url,))
            conn.commit()
            conn.close()

        # If there is CAPTCHA slider, open selenium webdriver to slide and then fetch information
        else:
            self.blocked = True
            print("Opening webdriver...")
            options = webdriver.ChromeOptions()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument("window-size=1280,720")
            options.add_argument('log-level=3')
            options.add_argument("--headless")
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
            options.add_experimental_option("excludeSwitches", ['enable-automation'])
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            # script = "Object.defineProperty(navigator,'webdriver',{get: ()=> false,});"
            # driver.execute_script(script)

            # If there are items on page opened by selenium, scrape directly
            if driver.find_elements(By.XPATH, '//div[contains(@class, "J-offer-wrapper")]'):
                print("Scraping with webdriver...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                try:
                    WebDriverWait(driver, 2).until(lambda d: len(d.find_elements_by_xpath(
                        '//div[contains(@class, "J-offer-wrapper")]'
                    )) > 40)
                except TimeoutException:
                    print(f"Not enough items on page {url}")
                rows = driver.find_elements(
                    By.XPATH, '//div[contains(@class, "J-offer-wrapper")]')
                for row in rows:
                    item = get_item_selenium(row, url)
                    if item['productLink'] is not None:
                        yield item
                driver.close()
                cursor.execute('UPDATE scrape_progress SET page_num=%s WHERE url=%s',
                               (next_page_num, base_url))
                return

            try:
                # Hover over the slider button 3 times to bypass CAPTCHA with 70%+ success rate
                WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.ID, "nc_1_n1z")))
                slider = driver.find_element(By.ID, 'nc_1_n1z')
                action = ActionChains(driver)
                for j in range(3):
                    action.move_to_element(slider)
                    action.move_by_offset(randint(-3, 3), randint(-3, 3))
                action.click_and_hold()
                action.move_by_offset(300, 0)
                action.perform()
                WebDriverWait(driver, 2).until(EC.presence_of_element_located(
                    (By.XPATH, '//div[contains(@class, "J-offer-wrapper")]')))
            # If failed to pass CAPTCHA, exit method
            except TimeoutException:
                print("Slider failed")
                driver.close()
                conn.commit()
                conn.close()
                return

            # If passed CAPTCHA, scroll to the bottom of the page to load 40+ items
            print("Slider success")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            try:
                WebDriverWait(driver, 2).until(lambda d: len(d.find_elements_by_xpath(
                    '//div[contains(@class, "J-offer-wrapper")]'
                )) > 40)
            except TimeoutException as err:
                print(f"Not enough items on page {url}: {err}")

            # Yield AlibabaItem from xpath of selenium element
            rows = driver.find_elements(By.XPATH, '//div[contains(@class, "J-offer-wrapper")]')
            for row in rows:
                item = get_item_selenium(row, url)
                if item['productLink'] is not None:
                    yield item
            print(f"Selenium scraped from {url}")
            cursor.execute('UPDATE scrape_progress SET page_num=%s WHERE url=%s',
                           (next_page_num, base_url))
            conn.commit()
            conn.close()
            driver.close()
            # if time.time() < self.close_time:
            #     yield scrapy.Request(url=next_url, callback=self.parse_search_pages)


if __name__ == '__main__':
    pass
