#!/usr/bin/env python3
"""Bootstrap reference catalog data (names, TND prices, packshot URLs, descriptions)
from a Tunisian parapharmacy listing, one brand page at a time.

Output: ref/catalog-raw/<brand-slug>.json  (raw reference data, curated later)
"""
import html as htmod
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "ref", "catalog-raw")
os.makedirs(OUT, exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
BASE = "https://parapharmacie.tn/marque/"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "ignore"), r.status
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "", 404
            time.sleep(2)
        except Exception:
            time.sleep(2)
    return "", 0


def clean(t):
    t = re.sub(r"<[^>]+>", " ", t)
    t = htmod.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def parse_page(s):
    starts = [m.start() for m in re.finditer(r'<li[^>]*class="[^"]*\btype-product\b', s)]
    items = []
    for i, st in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else st + 20000
        b = re.sub(r"\s+", " ", s[st:end])
        cls = re.search(r'class="([^"]*)"', b).group(1)
        title = re.search(r'woocommerce-loop-product__title[^>]*>(.*?)</h2>', b)
        link = re.search(r'href="(https://parapharmacie\.tn/shop/[^"]+)"', b)
        img = re.search(r'<img[^>]+src="([^"]+)"', b)
        srcset = re.search(r'<source[^>]+srcset="([^"]+)"', b)
        # biggest non-webp original: strip -300x300 suffix from the img src
        image = img.group(1) if img else ""
        image = re.sub(r"-\d+x\d+(\.(?:jpe?g|png))$", r"\1", image)
        prices = re.findall(r"<bdi>([\d.,]+)&nbsp;", b)
        regular = sale = None
        if "<del" in b and len(prices) >= 2:
            regular, sale = prices[0], prices[1]
        elif prices:
            regular = prices[0]
        desc = re.search(r'short-description">(.*?)</div>', b)
        bullets = re.findall(r"<li>(.*?)</li>", desc.group(1)) if desc else []
        cats = re.findall(r"product_cat-([\w-]+)", cls)
        items.append({
            "name": clean(title.group(1)) if title else "",
            "url": link.group(1) if link else "",
            "image": image,
            "price": float(regular.replace(",", "")) if regular else None,
            "sale": float(sale.replace(",", "")) if sale else None,
            "instock": "outofstock" not in cls,
            "cats": cats,
            "bullets": [clean(x) for x in bullets][:12],
        })
    return items


def scrape_brand(slug):
    path = os.path.join(OUT, slug + ".json")
    if os.path.exists(path):
        return slug, json.load(open(path))
    allitems, page = [], 1
    while page <= 12:
        url = BASE + slug + "/" + (f"page/{page}/" if page > 1 else "")
        s, code = get(url)
        if code != 200 or not s:
            break
        items = parse_page(s)
        if not items:
            break
        allitems += items
        if f"/marque/{slug}/page/{page + 1}/" not in s:
            break
        page += 1
    json.dump(allitems, open(path, "w"), ensure_ascii=False, indent=1)
    return slug, allitems


if __name__ == "__main__":
    slugs = [a for a in sys.argv[1:]] or [l.strip() for l in open(os.path.join(HERE, "ref", "brands-to-scrape.txt")) if l.strip()]
    with ThreadPoolExecutor(6) as ex:
        for slug, items in ex.map(scrape_brand, slugs):
            print(f"{slug:28s} {len(items):4d}  {sum(1 for i in items if i['image'])} imgs")
