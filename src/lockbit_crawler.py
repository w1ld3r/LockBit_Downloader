import datetime
import multiprocessing
import pathlib
import urllib

import backoff
import pycurl
import ratelimit
import requests
from bs4 import BeautifulSoup

__proxy__ = "socks5h://localhost:9050"
__useragent__ = "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"
__export_dir__ = "./LockBit_Data"

__request_calls_limit__ = 10
__request_period_limit__ = 60
__request_max_tries__ = 8
__download_max_tries__ = 1


def get_session() -> requests.Session:
    session = requests.session()
    session.headers = {"User-Agent": __useragent__}
    session.proxies = {"http": __proxy__}
    return session


@backoff.on_predicate(backoff.constant, jitter=None, max_tries=__request_max_tries__)
@ratelimit.sleep_and_retry
@ratelimit.limits(calls=__request_calls_limit__, period=__request_period_limit__)
def get_soup(session: requests.Session, url: str) -> BeautifulSoup:
    now = datetime.datetime.now()
    try:
        with session.get(url) as r:
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"Unable to get webpage at {url}\n{e}")
        return None
    finally:
        after = datetime.datetime.now()
        delay = after - now
        print(f"[^] Tooks {delay} seconds to request {url}")


@backoff.on_predicate(backoff.fibo, max_tries=__request_max_tries__)
@backoff.on_exception(backoff.expo, pycurl.error, max_tries=__download_max_tries__)
@ratelimit.sleep_and_retry
@ratelimit.limits(calls=__request_calls_limit__, period=__request_period_limit__)
def download_file(session: requests.Session, url: str, res_path: str) -> bool:
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
        print(f"[!] Unable to download file at {url}\n{e}")
        return False
    finally:
        after = datetime.datetime.now()
        delay = after - now
        print(f"[^] Tooks {delay} seconds to download file at {url}")


def create_dir(url: str) -> None:
    new_dir = "/".join(url.split("/")[3:])
    return pathlib.Path(__export_dir__, urllib.parse.unquote(new_dir)).mkdir(
        exist_ok=True, parents=True
    )


def get_content_at_url(
    url: str, path_urls: multiprocessing.Queue, file_urls: multiprocessing.Queue
) -> int:
    count_files = 0
    count_dirs = 0
    session = get_session()
    html = get_soup(session, url)
    if not html:
        return 0
    link_elements = html.find_all("td", class_="link")
    for link_element in link_elements:
        link = link_element.find("a")
        href_link = link["href"]
        new_url = f"{url}{href_link}"
        # href_link is file
        if not href_link.endswith("/"):
            file_urls.put(new_url)
            count_files += 1
        # href_link is directory and not parent directory
        elif href_link != "../":
            create_dir(new_url)
            path_urls.put(new_url)
            count_dirs += 1
    print(f"[-] Found {count_dirs} dir(s) and {count_files} files(s) at {url}")
    return count_files + count_dirs


def spider_crawl(
    url: str, path_urls: multiprocessing.Queue, file_urls: multiprocessing.Queue
) -> bool:
    print(f"[-] Start crawling at {url}")
    if not get_content_at_url(url, path_urls, file_urls):
        print(f"[!] Nothing to crawl at {url}")
        return False
    while True:
        if path_urls.empty():
            break
        search_url = path_urls.get()
        print(f"[-] Crawling content at {search_url}")
        get_content_at_url(search_url, path_urls, file_urls)
    return True


def files_downloader(file_urls: multiprocessing.Queue) -> bool:
    session = get_session()
    while True:
        file_url = file_urls.get()
        if not file_url:
            break
        file_path = "/".join(file_url.split("/")[3:])
        print(f"[-] Downloading content at {file_path}")
        download_file(session, file_url, file_path)
    return True


def crawl_lockbit(base_url: str, company_name: str, nb_downloader: int = 1) -> bool:
    url = f"{base_url}/{company_name}/"

    path_urls: multiprocessing.Queue = multiprocessing.Queue()
    file_urls: multiprocessing.Queue = multiprocessing.Queue()

    crawler = multiprocessing.Process(
        target=spider_crawl, args=(url, path_urls, file_urls)
    )
    crawler.start()
    downloaders = [
        multiprocessing.Process(target=files_downloader, args=(file_urls,))
        for _ in range(nb_downloader)
    ]
    for downloader in downloaders:
        downloader.start()
    crawler.join()
    for downloader in downloaders:
        downloader.join()
    return True


if __name__ == "__main__":
    base_url = "http://lockbit7z6rzyojiye437jp744d4uwtff7aq7df7gh2jvwqtv525c4yd.onion"
    company_name = "thalesgroup.com"
    nb_downloader = 5
    crawl_lockbit(base_url, company_name, nb_downloader)