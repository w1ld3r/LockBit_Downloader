#!/usr/bin/env python3

import datetime
import multiprocessing
import os
import pathlib
import urllib
from argparse import ArgumentParser, Namespace

import backoff
import pycurl
import ratelimit
import requests
from bs4 import BeautifulSoup

__lockbit7z__ = "http://lockbit7z6rzyojiye437jp744d4uwtff7aq7df7gh2jvwqtv525c4yd.onion"
__default_nb_dl_worker__ = 3
__proxy__ = "socks5h://localhost:9050"
__useragent__ = "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"
__export_dir__ = "./LockBit_Data"
__report_fname__ = f"report_dl_{datetime.datetime.now().timestamp()}.csv"
__request_calls_limit__ = 10
__request_period_limit__ = 60
__request_max_tries__ = 3
__download_max_tries__ = 1


def get_session() -> requests.Session:
    session = requests.session()
    session.headers = {"User-Agent": __useragent__}
    session.proxies = {"http": __proxy__}
    return session


def get_url_path(url: str) -> str:
    return urllib.parse.urlparse(url).path


def get_dl_root_path() -> pathlib.Path:
    return pathlib.Path(f"{pathlib.Path.cwd()}/{__export_dir__}")


def get_dl_path(url: str) -> pathlib.Path:
    return pathlib.Path(
        f"{get_dl_root_path()}{urllib.parse.unquote(get_url_path(url))}"
    )


def get_report_path() -> pathlib.Path:
    return pathlib.Path(f"{get_dl_root_path()}/{__report_fname__}")


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
        print(f"Unable to get webpage at {url}")
        print(e)
        return None
    finally:
        after = datetime.datetime.now()
        delay = after - now
        print(f"[^] Tooks {delay} seconds to request {url}")


@backoff.on_exception(backoff.expo, pycurl.error, max_tries=__download_max_tries__)
@ratelimit.sleep_and_retry
@ratelimit.limits(calls=__request_calls_limit__, period=__request_period_limit__)
def download_file(session: requests.Session, url: str) -> bool:
    now = datetime.datetime.now()
    dl_path = get_dl_path(url)
    cl = pycurl.Curl()
    cl.setopt(cl.PROXY, __proxy__)
    cl.setopt(cl.URL, url)
    if os.path.exists(dl_path):
        f = open(dl_path, "ab")
        cl.setopt(pycurl.RESUME_FROM, os.path.getsize(dl_path))
    else:
        f = open(dl_path, "wb")
    cl.setopt(pycurl.WRITEDATA, f)
    try:
        cl.perform()
        cl.close()
        return True
    except Exception as e:
        print(f"[!] Unable to download file at {url}")
        print(e)
        return False
    finally:
        after = datetime.datetime.now()
        delay = after - now
        print(f"[^] Tooks {delay} seconds to download {dl_path}")


def create_dir(url: str) -> None:
    return pathlib.Path(get_dl_path(url)).mkdir(exist_ok=True, parents=True)


def write_report(file_url, dl_res) -> bool:
    report_path = get_report_path()
    data = f"{datetime.datetime.now().timestamp()},"
    data += f"{file_url},"
    data += f"{get_dl_path(file_url)},"
    data += f"{dl_res}\n"
    with open(report_path, "a") as f:
        f.write(data)


def get_content_at_url(
    session: requests.Session,
    url: str,
    path_urls: multiprocessing.Queue,
    file_urls: multiprocessing.Queue,
) -> int:
    count_files = 0
    count_dirs = 0
    html = get_soup(session, url)
    if not html:
        return 0
    create_dir(url)
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
            path_urls.put(new_url)
            count_dirs += 1
    print(f"[-] Found {count_dirs} dir(s) and {count_files} files(s)")
    return count_files + count_dirs


def spider_crawl(
    url: str, path_urls: multiprocessing.Queue, file_urls: multiprocessing.Queue
) -> bool:
    session = get_session()
    print(f"[-] Start crawling at {url}")
    if not get_content_at_url(session, url, path_urls, file_urls):
        print(f"[!] Nothing to crawl at {url}")
        return False
    while True:
        if path_urls.empty():
            break
        search_url = path_urls.get()
        print(f"[-] Crawling content at {get_url_path(search_url)}")
        get_content_at_url(session, search_url, path_urls, file_urls)
    return True


def files_downloader(file_urls: multiprocessing.Queue) -> bool:
    session = get_session()
    while True:
        file_url = file_urls.get()
        if not file_url:
            break
        print(f"[-] Downloading content at {file_url}")
        dl_res = download_file(session, file_url)
        write_report(file_url, dl_res)
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
    # wait until all files are downloaded
    while True:
        if file_urls.empty():
            for _ in range(nb_downloader):
                file_urls.put(None)
            break
    for downloader in downloaders:
        downloader.join()
    return True


def get_args() -> Namespace:
    parser = ArgumentParser(description="Tool to download leaks from LockBit 7z")
    parser.add_argument(
        "-u",
        "--base-url",
        help="LockBit base URL",
        type=str,
        default=__lockbit7z__,
    )
    parser.add_argument(
        "-e", "--company-name", help="Company Name", type=str, required=True
    )
    parser.add_argument(
        "-k",
        "--nb-downloader",
        help="Number of downloader workers",
        type=int,
        default=__default_nb_dl_worker__,
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    crawl_lockbit(args.base_url, args.company_name, args.nb_downloader)
