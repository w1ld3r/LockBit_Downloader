import datetime
import pathlib
import time
import pycurl
from bs4 import BeautifulSoup
import queue
import requests
import ratelimit
import urllib
import backoff

__proxy__ = "socks5h://localhost:9050"
__useragent__ = "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"
__export_dir__ = "./LockBit_Data"


def get_session():
    session = requests.session()
    session.headers = {}
    session.headers['User-Agent'] = __useragent__
    session.proxies = {}
    session.proxies['http'] = __proxy__
    return session


@backoff.on_predicate(backoff.constant, jitter=None, interval=1, max_tries=8)
@ratelimit.sleep_and_retry
@ratelimit.limits(calls=10, period=60)
def get_soup(session, url) -> BeautifulSoup:
    now = datetime.datetime.now()
    try:
        with session.get(url) as r:
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"Unable to get webpage at {url}")
        print(e)
        return None
    finally:
        after = datetime.datetime.now()
        delay = after-now
        print(f"[^] Tooks {delay} seconds to request {url}")


@backoff.on_predicate(backoff.constant, jitter=None, interval=1, max_tries=8)
@backoff.on_exception(backoff.expo, pycurl.error, max_tries=8)
@ratelimit.sleep_and_retry
@ratelimit.limits(calls=10, period=60)
def download_file(session, url, res_path) -> bool:
    now = datetime.datetime.now()
    res = pathlib.Path(__export_dir__, urllib.parse.unquote(res_path))
    try:
        with open(res, "wb") as f:
            cl = pycurl.Curl()
            cl.setopt(cl.PROXY, __proxy__)
            cl.setopt(cl.URL, url)
            cl.setopt(cl.WRITEDATA, f)
            cl.perform()
            cl.close()
        return True
    except Exception as e:
        print(f"[!] Unable to download file at {url}")
        print(type(e))
        print(e)
        return False
    finally:
        after = datetime.datetime.now()
        delay = after-now
        print(f"[^] Tooks {delay} seconds to download file at {url}")


def create_dir(path_name):
    pathlib.Path(__export_dir__, urllib.parse.unquote(
        path_name)).mkdir(exist_ok=True, parents=True)


def get_content_at_url(session, url, parent_dir="") -> set():
    url_dirs = set()
    count_files = 0
    html = get_soup(session, url)
    if not html:
        return
    link_elements = html.find_all("td", class_="link")
    for link_element in link_elements:
        link = link_element.find("a")
        href_link = link['href']
        new_url = f"{url}{href_link}"
        file_path = f"./{parent_dir}/{href_link}"
        # href_link is file
        if not href_link.endswith("/"):
            download_file(session, new_url, file_path)
            count_files += 1
        # href_link is directory and not parent directory
        elif href_link != "../":
            url_dirs.add(new_url)
            create_dir(file_path)
    print(f"[+] Found {len(url_dirs)} dirs and downloaded {count_files} files")
    return url_dirs


def crawl_lockbit(base_url, company_name):
    session = get_session()
    url = f"{base_url}/{company_name}/"

    iterate_over = queue.Queue()
    iterate_over.put(url)
    while True:
        if iterate_over.empty():
            break
        search_url = iterate_over.get()
        parent_dir = '/'.join(search_url.split("/")[3:-1])
        new_dirs = get_content_at_url(session, search_url, parent_dir)
        if new_dirs:
            for new_dir in new_dirs:
                iterate_over.put(new_dir)


if __name__ == "__main__":
    base_url = "http://lockbit7z6rzyojiye437jp744d4uwtff7aq7df7gh2jvwqtv525c4yd.onion"
    company_name = "thalesgroup.com"
    crawl_lockbit(base_url, company_name)
