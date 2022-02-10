from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import ActionChains

from random import randint
import time

options = webdriver.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument("window-size=1280,720")
# options.add_argument("--headless")

success = 0
for i in range(5):
    driver = webdriver.Chrome(options=options)
    driver.get('https://www.alibaba.com/trade/search?IndexArea=product_en&SearchText=dance&page=1')
    script = "Object.defineProperty(navigator,'webdriver',{get: ()=> false,});"
    # 执行js代码
    driver.execute_script(script)

    print(f"window size: {driver.get_window_size()}")
    action = ActionChains(driver)

    try:
        WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.ID, "nc_1_n1z")))
    except:
        print("no slider found")
        quit()
    slider = driver.find_element(By.ID, 'nc_1_n1z')

    for j in range(3):
        action.move_to_element(slider)
        action.move_by_offset(randint(-3, 3), randint(-3, 3))
    action.click_and_hold()
    action.move_by_offset(300, 0)
    action.perform()

    time.sleep(1)
    if driver.find_elements(By.CLASS_NAME, "errloading"):
        print("failed")
    else:
        print("success")
        success += 1
        driver.close()

print(f"number of success: {success}")
