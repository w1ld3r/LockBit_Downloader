import datetime
import pathlib
import time

import requests

file_tree = "files_tree_f6edcd38e9.txt"
base_url = "http://lockbitapt2yfbt7lchxejug47kmqvqqxvvjpqkmevv4l3azl3gy6pyd.onion/ajax/listing-post?file-download=true&post=AZl2fuI5CRGPoyoC63223bd7b0dd3&path="

session = requests.session()
session.proxies = {}
session.proxies['http'] = 'socks5h://localhost:9050'

with open(file_tree, "r") as f:
    for line in f.readlines():
        path = line.split(" - ", 1)[0][1:]
        url = f"{base_url}{path}"
        if pathlib.Path(path).exists() and pathlib.Path(path).stat().st_size != 0:
            print("[-] File already exists, skeeping...")
            continue
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        print(f"[+] Downloading {path}")
        now = datetime.datetime.now()
        with session.get(url, stream=True) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content():
                    f.write(chunk)
        after = datetime.datetime.now()
        delay = after-now
        print(f"[^] Tooks {delay} seconds")
        time.sleep(5)
