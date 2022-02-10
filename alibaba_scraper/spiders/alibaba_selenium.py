import scrapy
from scrapy import signals

import urllib.parse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException

import mysql.connector
import time
import re
from alibaba_scraper.items import AlibabaItem


def get_scraperapi_url(url):
    payload = {'api_key': 'c998d00e5914afe1b2c86d1313a4d890', 'url': url}
    proxy_url = 'http://api.scraperapi.com/?' + urllib.parse.urlencode(payload)
    return proxy_url


def get_trailing_num(s):
    n = re.search(r'\d+$', s)
    return int(n.group()) if n else None


def get_item_xpath(row, search_page_url):
    """通过搜索结果页面xpath元素中的信息生成阿里巴巴商品对象"""

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
    """通过搜索结果页面selenium元素中的信息生成阿里巴巴商品对象"""

    item = AlibabaItem()
    item['productLink'] = element.find_element_by_xpath(
        './/a[@class="elements-title-normal one-line"]').get_attribute('href')
    item['name'] = element.find_element_by_xpath(
        './/a[@class="elements-title-normal one-line"]').get_attribute('title')
    try:
        item['price'] = element.find_element_by_xpath(
            './/span[@class="elements-offer-price-normal__price"]').text
    except NoSuchElementException:
        item['price'] = element.find_element_by_xpath(
            './/span[@class="elements-offer-price-normal__promotion"]').text
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
        """爬虫初始化建立数据库连接池"""

        super().__init__(**kwargs)
        dbconfig = {
            'host': 'localhost',
            'user': 'root',
            'password': 'root',
            'database': 'alibaba_scraper',
        }
        self.conn = mysql.connector.connect(pool_name="alibaba_pool", pool_size=32, **dbconfig)
        self.blocked = False
        self.close_time = time.time() + 60

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(AlibabaSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        spider.logger.info('Spider closed: %s', spider.name)

    def get_urls(self):
        """从scrape_progress数据库表格获取目前爬取进度，生成需要爬取的链接"""

        conn = mysql.connector.connect(pool_name="alibaba_pool")
        cursor = conn.cursor()
        cursor.execute('SELECT url, page_num FROM scrape_progress WHERE completed=0')
        rows = cursor.fetchall()
        urls = []
        for i in range(4):
            row = rows[i]
            urls.append(row[0] + str(row[1]))
        return urls

    def start_requests(self):
        urls = self.get_urls()
        for url in urls:
            # url=get_scraperapi_url(url)
            yield scrapy.Request(url=url, callback=self.parse_search_pages)

    # Use xpath to extract information from search pages and store in a product object
    def parse_search_pages(self, response):
        url = response.url

        options = webdriver.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument("window-size=1280,720")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        # options.add_argument("--headless")
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        options.add_experimental_option("excludeSwitches", ['enable-automation'])
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        try:
            WebDriverWait(driver, 2).until(lambda d: len(d.find_elements_by_xpath(
                '//div[contains(@class, "J-offer-wrapper")]'
            )) > 40)
        except TimeoutException as err:
            print(f"Not enough items on page {url}: {err}")
        rows = driver.find_elements(By.XPATH, '//div[contains(@class, "J-offer-wrapper")]')

        # rows = response.xpath('//div[contains(@class, "J-offer-wrapper")]')
        page_num = get_trailing_num(url)
        next_page_num = page_num + 1
        base_url = url[:-len(str(page_num))]
        next_url = base_url + str(next_page_num)

        conn = mysql.connector.connect(pool_name="alibaba_pool")
        cursor = conn.cursor()

        if rows:
            for row in rows:
                item = get_item_selenium(row, url)
                if item['productLink'] is not None:
                    yield item
            driver.close()
            cursor.execute('UPDATE scrape_progress SET page_num=%s WHERE url=%s', (next_page_num, base_url))
            conn.commit()
            conn.close()
            print(f"Scraped from {url}")
            # if time.time()<self.close_time and not self.blocked:
            # yield scrapy.Request(url=next_url, callback=self.parse_search_pages)
            return

        # 若没有滑块验证，表明超过搜索尾页，在scrape_progress数据库表格中标记
        elif response.xpath('//div[@class="txt-wrap"]'):
            print(f"Completed {base_url} at page {page_num}")
            cursor.execute('UPDATE scrape_progress SET completed=1 WHERE url=%s', (base_url,))
            conn.commit()
            conn.close()

        # 若需要滑块验证，启动selenium浏览器引擎进行验证，再通过selenium元素生成阿里巴巴商品对象
        else:
            self.blocked = True
            try:
                WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.ID, "nc_1_n1z")))
                slider = driver.find_element(By.ID, 'nc_1_n1z')
                action = ActionChains(driver)
                action.move_to_element(slider)
                action.move_by_offset(-3, -3)
                action.click_and_hold().perform()
                action.move_by_offset(300, 0).perform()
                WebDriverWait(driver, 2).until(EC.presence_of_element_located(
                    (By.XPATH, '//div[contains(@class, "J-offer-wrapper")]')))
            # 若验证失败，退出方法
            except TimeoutException:
                print("Slider failed")
                driver.close()
                conn.commit()
                conn.close()
                return

            print("Slider success")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            try:
                WebDriverWait(driver, 2).until(lambda d: len(d.find_elements_by_xpath(
                    '//div[contains(@class, "J-offer-wrapper")]'
                )) > 40)
            except TimeoutException as err:
                print(f"Not enough items on page {url}: {err}")
            rows = driver.find_elements(By.XPATH, '//div[contains(@class, "J-offer-wrapper")]')
            for row in rows:
                item = get_item_selenium(row, url)
                if item['productLink'] is not None:
                    yield item
            print(f"Selenium scraped from {url}")
            driver.close()
            cursor.execute('UPDATE scrape_progress SET page_num=%s WHERE url=%s',
                           (next_page_num, base_url))
            conn.commit()
            conn.close()


if __name__ == '__main__':
    pass
