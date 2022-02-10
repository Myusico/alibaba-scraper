from selenium import webdriver
from selenium.webdriver.common.by import By

options = webdriver.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')

driver = webdriver.Chrome(options=options)
driver.get('https://www.alibaba.com/trade/search?IndexArea=product_en&SearchText=dance&page=1')

elements = driver.find_elements(By.XPATH, '//div[contains(@class, "J-offer-wrapper")]')
if elements:
    print(f"number of elements: {len(elements)}")
