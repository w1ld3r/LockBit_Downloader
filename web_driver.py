import logging

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import logging

__proxy__ = "localhost:9050"
__chromedriver_path__ = "./bin/chromedriver"
__user_agent__ = "Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0"
__download_dir__ = "/home/xinshen/Downloads/DataLeaks/asecna.org/"
logging.getLogger("selenium").setLevel(logging.WARNING)


def get_options(debug=False):
    options = Options()
    if not debug:
        options.add_argument("--headless")
    options.add_argument(f"--proxy-server=socks5://{__proxy__}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--user-agent=" + __user_agent__)
    options.add_experimental_option("prefs", {
        "download.default_directory": __download_dir__,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing_for_trusted_sources_enabled": False,
        "safebrowsing.enabled": False
    })
    return options


def get_driver(debug=False):
    try:
        driver = webdriver.Chrome(executable_path=__chromedriver_path__ ,options=get_options(debug))
        return driver
    except Exception as e:
        logging.warning("Unable to get web browser")
        logging.warning(e)
        return


def navigate_to(driver, url):
    try:
        driver.get(url)
        return True
    except Exception as e:
        logging.warning("Unable to get {}".format(url))
        logging.warning(e)
        try:
            driver.quit()
        except:
            pass
        return False


def get_webpage(url, debug=False):
    driver = get_driver(debug)
    if not navigate_to(driver, url):
        return
    return driver


def get_soup(web_page):
    try:
        html_doc = web_page.page_source
        soup = BeautifulSoup(html_doc, "html.parser")
        return soup
    except Exception as e:
        logging.warning("Unable to get soup")
        logging.debug(e)
        return


def close_web_page(web_page):
    try:
        web_page.close()
    except Exception as e:
        logging.warning("Unable to close web page")
        logging.debug(e)
