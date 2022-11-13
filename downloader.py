import datetime
import time
import pathlib

from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import web_driver

__base_url__ = "http://lockbitapt2yfbt7lchxejug47kmqvqqxvvjpqkmevv4l3azl3gy6pyd.onion"
__test__ = "qkmevv4l3azl3gy6pyd.onion/ajax/listing-post?file-download=true&post=AZl2fuI5CRGPoyoC63223bd7b0dd3&path=qweq123%2FD%2Fasecna.org%2Fmsg%2Fmsg%2F.iscsi%2Fiscsi_lun_backing_store"
post_id = "AZl2fuI5CRGPoyoC63223bd7b0dd3"
url = f"{__base_url__}/post/{post_id}"

print("Opening webrowser")
driver = web_driver.get_driver(True)
print(f"Browsing {url}")
now = datetime.datetime.now()
driver.get(url)
WebDriverWait(driver, 666).until(EC.presence_of_element_located(
    (By.CLASS_NAME, "file-listing__content")))
after = datetime.datetime.now()
delay = after-now
print(f"Page loaded in {delay}")
file_list = []

current_dir = "./"
count_visited = 0
while True:
    items = driver.find_elements(By.CLASS_NAME, "file-listing__item")
    for item in items:
        file_item = {}
        attributes = item.find_elements(By.TAG_NAME, "div")
        for attribute in attributes:
            attribute_class = attribute.get_attribute("class")
            if "file-listing__name" in attribute_class:
                file_item["file_type"] = attribute_class.split("--")[1]
                file_item["file_name"] = attribute.text
            if "file-listing__date" in attribute_class:
                file_item["file_date"] = attribute.text
            if "file-listing__size" in attribute_class:
                file_item["file_size"] = attribute.text
        file_item["file_path"] = f"{current_dir}/{file_item['file_name']}"
        if file_item["file_path"] in [a["file_path"] for a in file_list]:
            count_visited += 1
            continue
        else:
            break
    if not file_item["file_path"] in [a["file_path"] for a in file_list]:
        if file_item["file_type"] == "folder":
            file_list.append(file_item)
            print(f"[>] Following {file_item['file_name']} directory")
            now = datetime.datetime.now()
            action = ActionChains(driver)
            action.double_click(item).perform()
            WebDriverWait(driver, 666).until(EC.text_to_be_present_in_element_attribute((By.ID, "loading_global"), "style", "none"))
            after = datetime.datetime.now()
            delay = after-now
            print(f"[^] Directory loaded in {delay}")
            current_dir = f"{current_dir}/{file_item['file_name']}"
            count_visited = 0
            continue
        else:
            file_path = pathlib.Path(web_driver.__download_dir__, file_item["file_path"])
            if file_path.exists():
                print(f"[-] Skeeping, {file_item['file_path']} already exists")
                file_list.append(file_item)
                count_visited = 0
                continue
            print(f"[+] Downloading {file_item['file_name']} ({file_item['file_size']}) - {file_item['file_date']}")
            action = ActionChains(driver)
            action.click(item).perform()
            WebDriverWait(driver, 666).until(EC.text_to_be_present_in_element_attribute((By.ID, "loading_global"), "style", "none"))
            before_fd_list = set(pathlib.Path(web_driver.__download_dir__).glob("*"))
            driver.find_element(By.CLASS_NAME, "file-download-btn").click()
            WebDriverWait(driver, 666).until(EC.text_to_be_present_in_element_attribute((By.ID, "loading_global"), "style", "none"))
            after_fd_list = set(pathlib.Path(web_driver.__download_dir__).glob("*"))
            new_files = list(after_fd_list-before_fd_list)
            dl_file = pathlib.Path(web_driver.__download_dir__, "blob")
            while True:
                is_ok = True
                time.sleep(1)
                after_fd_list = set(pathlib.Path(web_driver.__download_dir__).glob("*"))
                new_files = list(after_fd_list-before_fd_list)
                if not new_files:
                    is_ok = False
                dl_file = pathlib.Path(new_files[0])
                if dl_file.suffix == ".crdownload":
                    is_ok = False
                if is_ok:
                    break      
            dl_file = pathlib.Path(new_files[0])
            dl_file_size_now = dl_file.stat().st_size
            time.sleep(1)
            while dl_file.stat().st_size > dl_file_size_now:
                 time.sleep(2)
                 dl_file_size_now = dl_file.stat().st_size
            if dl_file.stat().st_size == 0:
                dl_file.unlink()
                count_visited = 0
                continue
            file_dl_dir = pathlib.Path(web_driver.__download_dir__, current_dir)
            file_dl_dir.mkdir(parents=True, exist_ok=True)
            final_file_path = pathlib.Path(file_dl_dir, file_item["file_name"])
            # print(f"[-] Renaming {dl_file} to {final_file_path}")
            dl_file.rename(final_file_path)
            file_list.append(file_item)
            count_visited = 0

    if count_visited >= len(items):
        page_item = driver.find_element(By.CLASS_NAME, "current")
        page_nb = page_item.text.split("/")
        if page_nb[0] != page_nb[1]:
            print(f"[>] Loading next page")
            now = datetime.datetime.now()
            driver.find_element(By.CLASS_NAME, "next-one-page").click()
            WebDriverWait(driver, 666).until(EC.text_to_be_present_in_element_attribute((By.ID, "loading_global"), "style", "none"))
            after = datetime.datetime.now()
            delay = after-now
            print(f"[^] Next page loaded in {delay}")
            count_visited = 0
            continue

        back_item = driver.find_element(By.CLASS_NAME, "file__back")
        if "active" in back_item.get_attribute("class"):
            print(f"[<] Returning back")
            now = datetime.datetime.now()
            back_item.click()
            WebDriverWait(driver, 666).until(EC.text_to_be_present_in_element_attribute((By.ID, "loading_global"), "style", "none"))
            after = datetime.datetime.now()
            delay = after-now
            print(f"[^] Upper dir loaded in {delay}")
            current_dir = "/".join(current_dir.split("/")[:-1])
            count_visited = 0
            continue


iterate_over_dir()