#!/usr/bin/env python3
"""Build data/products.json from the shop's real inventory (ref/inventaire.json, exported
from the POS: EAN, designation, stock, TTC price) by matching each line to the reference
library in ref/catalog-raw/ (clean names, packshots, descriptions).

  python3 tools/match_inventory.py            # match + download images + write catalog
  python3 tools/match_inventory.py --report   # print a review sample of matches

Prices and stock always come from the inventory; names/images/descriptions come from the
matched reference product when the match is confident, otherwise the POS name is cleaned up
and the product is shown without a photo.
"""
import io
import json
import math
import os
import re
import sys
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curate_catalog import CATEGORIES, classify, clean_name, slugify, strip_accents  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "ref", "catalog-raw")
IMG_DIR = os.path.join(HERE, "images", "products")
OUT = os.path.join(HERE, "data", "products.json")
OVERRIDES = os.path.join(HERE, "data", "overrides.json")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"

DISPLAY = {  # brand slug -> display name (falls back to title-cased slug)
    "la-roche-posay": "La Roche-Posay", "a-derma": "A-Derma", "roge-cavailles": "Rogé Cavaillès", "svr": "SVR",
    "acm": "ACM", "isdin": "ISDIN", "gum": "GUM", "kin": "KIN", "nuk": "NUK", "bibs": "BIBS", "wee": "Wee Baby",
    "avent": "Philips Avent", "curall": "CurALL", "esthelle": "Esth'elle", "eye-care": "Eye Care Cosmetics",
    "phyteal": "Phytéal", "luxeol": "Luxéol", "avene": "Avène", "babe": "Babé", "bio-orient": "Bio Orient",
    "gamarde-soins-bio-dermatologiques": "Gamarde", "oral-b": "Oral-B", "herbi-feet": "Herbi Feet",
    "oligo-ph": "Oligo-pH", "pure-skin": "Pure Skin", "accu-chek": "Accu-Chek", "tommee-tippee": "Tommee Tippee",
    "cerave": "CeraVe", "bioxsine": "Bioxsine", "pharmaceris": "Pharmaceris", "innovaderm": "Innovaderm",
}

# POS first-word(s) -> reference brand slug.  Checked longest-first against the start of the name.
ALIASES = {
    "lrp": "la-roche-posay", "la roche posay": "la-roche-posay", "roche posay": "la-roche-posay",
    "cavailles": "roge-cavailles", "cavalles": "roge-cavailles", "roge cavailles": "roge-cavailles", "roge cavaillese": "roge-cavailles", "roge": "roge-cavailles",
    "aderma": "a-derma", "a derma": "a-derma", "aktiv": "doppelherz", "doppelherz": "doppelherz", "bioxcin": "bioxsine", "bioxsine": "bioxsine",
    "dercos": "vichy", "vichy": "vichy", "calino": "esthelle", "esthelle": "esthelle", "esth elle": "esthelle",
    "eye care": "eye-care", "eyecare": "eye-care", "bio orient": "bio-orient", "bioorient": "bio-orient",
    "gamarde": "gamarde-soins-bio-dermatologiques", "pure skin": "pure-skin", "oral b": "oral-b",
    "tommee tippee": "tommee-tippee", "accu chek": "accu-chek", "herbi feet": "herbi-feet", "oligo ph": "oligo-ph",
    "pullmoll": "pulmoll", "pulmoll": "pulmoll", "phyto": "phyto", "pediakids": "pediakid", "pediakid": "pediakid",
    "wee baby": "wee", "wee": "wee", "nuk": "nuk", "bibs": "bibs", "canpol": "canpol", "chicco": "chicco", "mustela": "mustela",
    "biolane": "biolane", "materna": "materna", "lilas": "lilas", "alphanova": "alphanova", "dodie": "dodie", "avent": "avent",
    "nimo": "nimo", "physiomer": "physiomer", "septanil": "septanil", "auracy": "auracy", "bioherbs": "bioherbs",
    "jouvence": "jouvence", "fiderma": "fiderma", "eveline": "eveline", "anycare": "anycare", "herbex": "herbex",
    "sensodyne": "sensodyne", "silca": "silca", "laino": "laino", "item": "item", "saforelle": "saforelle", "iprad": "iprad",
    "clarelis": "clarelis", "clarenia": "clarenia", "bandlux": "bandlux", "neovix": "neovix", "therapia": "therapia",
    "svr": "svr", "avene": "avene", "gum": "gum", "uriage": "uriage", "isdin": "isdin", "byphasse": "byphasse", "titania": "titania",
    "innovaderm": "innovaderm", "roncey": "roncey", "bioderma": "bioderma", "novexpert": "novexpert", "noreva": "noreva",
    "curall": "curall", "acm": "acm", "eucerin": "eucerin", "dermacare": "dermacare", "alania": "alania", "naturtint": "naturtint",
    "sensilis": "sensilis", "phyteal": "phyteal", "ducray": "ducray", "cerave": "cerave", "nuxe": "nuxe", "dermaceutic": "dermaceutic",
    "luxeol": "luxeol", "novaclear": "novaclear", "cytolnat": "cytolnat", "babe": "babe", "daylong": "daylong", "cetaphil": "cetaphil",
    "ultrasun": "ultrasun", "muriac": "muriac", "vitavea": None, "filorga": "filorga", "beesline": "beesline", "lierac": "lierac",
    "hyfac": "hyfac", "dermedic": "dermedic", "pharmaceris": "pharmaceris", "tartrex": None, "quies": "quies", "rivaderm": "rivaderm",
    "kela": None, "medel": "medel", "techwood": "techwood", "westinghouse": "westinghouse", "klorex": "klorex", "beurer": "beurer",
    "gummybear": "gummybear", "cystiphane": "biorga", "biorga": "biorga", "ecrinal": "ecrinal", "elgydium": "elgydium", "kin": "kin",
    "parodontax": "parodontax", "durex": "durex", "maximum": "maximum", "veet": "veet", "rossmax": "rossmax", "orthomed": "orthomed",
    "orthofix": "orthofix", "mixa": "mixa", "asepta": "asepta", "camomilla": "camomilla", "bebeto": "bebeto", "effiderm": "effiderm",
    "oligogum": "oligogum", "pampers": "pampers", "elmex": "elmex", "listerine": "listerine", "meridol": "meridol", "blevit": "blevit",
    "medela": "medela", "martiderm": "martiderm", "sesderma": "sesderma", "rilastil": "rilastil", "killpoux": "killpoux",
    "momcozy": None, "les secrets de loly": None, "suavinex": None, "ortho claq": None, "j admire": None, "sti light": None,
    "vitonic": None, "fersang": None, "lipofer": None, "dekar": None, "piediab": None, "young": None, "ivory": None,
    "carabol": None, "glamour": None, "arecima": None, "phytothera": None, "oligovit": None, "gh": None,
}
ALIAS_KEYS = sorted(ALIASES, key=len, reverse=True)

ABBREV = {
    "shamp": "shampooing", "shp": "shampooing", "sh": "shampooing", "shampoing": "shampooing", "shampooing": "shampooing", "shampo": "shampooing",
    "nett": "nettoyant", "nettoy": "nettoyant", "demaq": "demaquillant", "cr": "creme", "crm": "creme", "crème": "creme",
    "bib": "biberon", "suc": "sucette", "tet": "tetine", "ecr": "ecran", "inv": "invisible", "hydrat": "hydratant",
    "apais": "apaisant", "repar": "reparateur", "purif": "purifiant", "matif": "matifiant", "protect": "protecteur",
    "sol": "solaire", "spf50": "spf50", "ip50": "spf50", "fps50": "spf50", "spf30": "spf30", "spf": "spf",
    "ap": "ap", "moist": "moisturising", "moiture": "moisture", "renew": "renewing", "sens": "sensible", "pell": "pelliculaire",
    "antichute": "antichute", "anti": "anti", "capil": "capillaire", "capillaire": "capillaire", "gelule": "gelules", "gelules": "gelules",
    "cp": "comprimes", "cps": "comprimes", "comp": "comprimes", "comprime": "comprimes", "caps": "capsules", "buv": "buvables",
    "bte": "", "bt": "", "b": "", "boite": "", "fl": "", "flacon": "", "tube": "", "pot": "", "nf": "", "of": "", "lot": "", "x": "",
    "ml": "", "gr": "", "g": "", "l": "", "cl": "", "kg": "", "mg": "", "m": "m", "s": "s", "t": "t",
    "et": "", "de": "", "du": "", "des": "", "la": "", "le": "", "les": "", "a": "", "au": "", "aux": "", "en": "", "pour": "", "avec": "", "sans": "sans", "the": "", "and": "", "with": "", "for": "", "d": "", "l": "",
    "grat": "", "gratuit": "", "offert": "", "offerte": "", "promo": "", "pack": "pack", "coffret": "coffret", "trousse": "trousse", "kit": "kit",
    "p/g": "peau grasse", "p/s": "peau seche", "pnm": "peau normale mixte", "pg": "peau grasse", "pm": "peau mixte", "ps": "peau sensible",
    "visage": "visage", "corps": "corps", "corp": "corps", "bebe": "bebe", "enfant": "enfant", "kids": "enfant",
    "cream": "creme", "fluid": "fluide", "serum": "serum", "sérum": "serum", "gel": "gel", "lait": "lait", "huile": "huile", "baume": "baume",
    "levres": "levres", "levre": "levres", "lips": "levres", "lip": "levres", "yeux": "yeux", "eye": "yeux", "eyes": "yeux",
    "mains": "mains", "main": "mains", "hand": "mains", "pieds": "pieds", "pied": "pieds", "foot": "pieds", "feet": "pieds",
    "cheveux": "cheveux", "hair": "cheveux", "ongles": "ongles", "nail": "ongles", "nails": "ongles",
    "brosse": "brosse", "dents": "dents", "dent": "dents", "dentaire": "dentaire", "bain": "bain", "bouche": "bouche",
    "fdt": "fond teint", "teinte": "teinte", "teint": "teinte", "tinted": "teinte", "invisible": "invisible",
}
PROMO = re.compile(r"\*\s*2|\bx\s*2\b|\blot\s*2\b|\blot\b|\bof\s*\d+%|\bnf\b|\+\s*\d+\s*grat|\boffert\w*\b|\bgratuit\b|\bpromo\b|\bduo\b|\bpack\s*de\b", re.I)
SIZE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(ml|gr|g|l|cl|kg|mg|m|cm|mm)\b")


def normalize(name):
    s = strip_accents(str(name)).lower()
    s = s.replace("'", " ").replace("’", " ").replace("_", " ").replace("&", " ")
    s = re.sub(r"(\d)\s*(ml|gr|g|l|cl|kg|mg|cm|mm)\b", r"\1\2", s)          # 250 ML -> 250ml
    s = re.sub(r"\b(spf|ip|fps)\s*(\d+)\s*\+?", r"spf\2", s)                 # SPF 50+ -> spf50
    s = re.sub(r"\b(anti|apres|sans|micro|ultra|multi|hyper)[\s-]+(?=\w)", r"\1", s)  # anti chute -> antichute
    s = PROMO.sub(" ", s)
    s = re.sub(r"[^a-z0-9/+]+", " ", s)
    toks = []
    for t in s.split():
        t = t.strip("/+")
        if not t:
            continue
        m = SIZE_RE.fullmatch(t)
        if m:
            unit = m.group(2)
            unit = {"gr": "g", "l": "l"}.get(unit, unit)
            val = m.group(1).replace(",", ".")
            if unit == "l" and float(val) < 10:      # 2L -> 2000ml
                val, unit = str(int(float(val) * 1000)), "ml"
            toks.append(f"{val}{unit}".replace(".0m", "m"))
            continue
        if t in ABBREV:
            r = ABBREV[t]
            if r:
                toks.extend(r.split())
            continue
        if re.fullmatch(r"\d{1,2}", t) and t not in {"89", "10", "15", "20", "30", "50", "40", "60", "90", "12", "24", "48", "72"}:
            continue
        toks.append(stem(t))
    return toks


def stem(t):
    """Light stem so spelling variants line up: hyaluronic/hyaluron, gellules/gelules, nourissant/nourrissant."""
    if re.fullmatch(r"\d.*", t):
        return t
    t = t.replace("ll", "l").replace("rr", "r").replace("ss", "s").replace("ph", "f").replace("y", "i")
    t = re.sub(r"(ique|ant|ante|ants|eur|euse|ique|ic|ing|es|s)$", "", t) if len(t) > 5 else t
    return t[:7]


def sizes(toks):
    return {t for t in toks if SIZE_RE.fullmatch(t)}


def detect_brand(name):
    n = strip_accents(name).lower().replace("'", " ").replace("’", " ")
    n = re.sub(r"[^a-z0-9 ]+", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    for k in ALIAS_KEYS:
        if n.startswith(k + " ") or n == k:
            return ALIASES[k], k
    # brand mentioned anywhere (e.g. "CREME VISAGE MULTIFONCTION CLARELIS")
    for k in ALIAS_KEYS:
        if len(k) >= 4 and re.search(r"\b" + re.escape(k) + r"\b", n):
            return ALIASES[k], k
    return None, None


def load_reference():
    ref = []
    for f in sorted(os.listdir(RAW)):
        slug = f[:-5]
        for p in json.load(open(os.path.join(RAW, f))):
            if not p["name"] or not p["image"]:
                continue
            toks = normalize(p["name"])
            ref.append({"brand": slug, "name": p["name"], "toks": toks, "set": set(toks), "sizes": sizes(toks),
                        "image": p["image"], "bullets": p["bullets"], "cats": p["cats"], "url": p["url"], "price": p["price"]})
    df = Counter()
    for r in ref:
        df.update(r["set"])
    N = len(ref)
    idf = {t: math.log((N + 1) / (c + 1)) + 1 for t, c in df.items()}
    return ref, idf


def score(inv_toks, r, idf):
    a = set(inv_toks)
    if not a or not r["set"]:
        return 0.0
    shared = a & r["set"]
    w = lambda ts: sum(idf.get(t, 1.0) for t in ts)
    recall = w(shared) / w(a)
    precision = w(shared) / w(r["set"])
    s = 0.65 * recall + 0.35 * precision
    sa, sb = sizes(a), r["sizes"]
    if sa and sb:
        s *= 1.08 if sa & sb else 0.55
    elif sa or sb:
        s *= 0.95
    # the most distinctive inventory word (e.g. "grignoteur", "toner") must be present
    words = [t for t in a if t not in sa]
    if words:
        key = max(words, key=lambda t: idf.get(t, 1.0))
        if key not in shared:
            s *= 0.7
    if len(shared - sa) < 2 and len(words) >= 2:
        s *= 0.75
    return s


def match_all(inv, ref, idf):
    by_brand = defaultdict(list)
    for i, r in enumerate(ref):
        by_brand[r["brand"]].append(i)
    results = []
    for item in inv:
        name = item["name"]
        brand, alias = detect_brand(name)
        toks = normalize(name)
        if alias:  # drop the brand words themselves from the comparison
            toks = [t for t in toks if t not in normalize(alias)]
        if alias and brand is None:      # brand known but not in the reference library: never guess
            cands = []
        else:
            cands = by_brand.get(brand) if brand else range(len(ref))
        best, best_s = None, 0.0
        for i in cands or []:
            s = score(toks, ref[i], idf)
            if s > best_s:
                best, best_s = ref[i], s
        thr = 0.56 if brand else 0.80
        results.append({"item": item, "brand": brand, "alias": alias, "toks": toks, "match": best if best_s >= thr else None, "score": round(best_s, 3), "best": best})
    return results


SMALL = {"de", "du", "des", "la", "le", "les", "et", "a", "au", "aux", "en", "pour", "avec", "sans", "sur", "d", "l"}


def pretty_pos_name(name, alias, brand_display):
    """Clean up a POS designation for display when nothing matched."""
    n = re.sub(r"\s+", " ", str(name)).strip()
    n = PROMO.sub(" ", n) if re.search(r"\bof\s*\d+%|\bnf\b|\+\s*\d+\s*grat", n, re.I) else n
    n = re.sub(r"\s+", " ", n).strip(" -*")
    words = []
    for w in n.split(" "):
        lw = w.lower()
        if re.fullmatch(r"\d+(?:[.,]\d+)?(ml|g|gr|l|cl|kg|mg|cm|mm)", lw):
            words.append(re.sub(r"gr$", "g", lw)); continue
        if re.fullmatch(r"(spf|ip)\s*\d+\+?", lw):
            words.append(w.upper().replace("IP", "SPF")); continue
        if lw in {"shamp", "shp", "sh"}:
            words.append("Shampooing"); continue
        if lw == "nett":
            words.append("Nettoyant"); continue
        if lw == "cr":
            words.append("Crème"); continue
        if lw in {"bt", "b", "bte"} or re.fullmatch(r"(b|bt|bte)/\d+", lw):
            words.append(("Boîte de " + lw.split("/")[1]) if "/" in lw else "Boîte"); continue
        if len(w) <= 3 and w.isupper() and not w.isdigit():
            words.append(w); continue
        if lw in SMALL and words:
            words.append(lw); continue
        words.append("-".join(p[:1].upper() + p[1:].lower() for p in w.split("-")))
    n = " ".join(words)
    if alias:
        nn = strip_accents(n).lower()
        if nn.startswith(alias + " ") or nn.startswith(alias.replace(" ", "-") + " "):
            n = n[len(alias):].strip(" -–:")
    return n


def fetch_image(url, slug):
    dest = os.path.join(IMG_DIR, slug + ".jpg")
    if os.path.exists(dest):
        return dest
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=40) as r:
            data = r.read()
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.paste(im, mask=im.split()[3])
        im = bg.convert("RGB")
        im.thumbnail((700, 700))
        im.save(dest, "JPEG", quality=86, optimize=True, progressive=True)
        return dest
    except Exception as e:
        print("  image failed", slug, e)
        return None


def main():
    inv = json.load(open(os.path.join(HERE, "ref", "inventaire.json")))
    inv = [i for i in inv if i["name"] and i["price"]]
    ref, idf = load_reference()
    res = match_all(inv, ref, idf)
    overrides = json.load(open(OVERRIDES)) if os.path.exists(OVERRIDES) else {}

    if "--report" in sys.argv:
        import random
        random.seed(int(sys.argv[sys.argv.index("--report") + 1]) if len(sys.argv) > sys.argv.index("--report") + 1 else 1)
        matched = [r for r in res if r["match"]]
        print(f"matched {len(matched)}/{len(res)}  (brand detected: {sum(1 for r in res if r['brand'])})")
        for r in random.sample(matched, 60):
            print(f"{r['score']:.2f} | {r['item']['name'][:55]:55s} => {r['match']['name'][:70]}")
        print("\n---- unmatched (best guess shown) ----")
        for r in random.sample([r for r in res if not r["match"]], 40):
            print(f"{r['score']:.2f} | {r['item']['name'][:55]:55s} ~> {(r['best'] or {}).get('name', '')[:60]}")
        return

    products, seen = [], set()
    for r in res:
        item, m = r["item"], r["match"]
        ean = item["code"]
        ov = overrides.get(ean, {})
        if ov.get("hide"):
            continue
        if ov.get("ref_url"):  # manual pin to a reference product
            m = next((x for x in ref if x["url"] == ov["ref_url"]), m)
        brand_slug = (m["brand"] if m else r["brand"]) or ov.get("brand_slug")
        brand = DISPLAY.get(brand_slug, brand_slug.replace("-", " ").title() if brand_slug else "")
        if not brand_slug and r["alias"]:
            brand = {"les secrets de loly": "Les Secrets de Loly", "j admire": "J'Admire", "ortho claq": "Ortho-Claq",
                     "sti light": "S.T.I Light", "gh": "GH", "momcozy": "Momcozy", "suavinex": "Suavinex"}.get(r["alias"], r["alias"].title())
        name = clean_name(m["name"], brand) if m else pretty_pos_name(item["name"], r["alias"], brand)
        name = ov.get("name", name)
        slug = slugify((brand + " " + name) if brand else name) or ("p-" + ean)
        if slug in seen:
            slug = slug + "-" + re.sub(r"\W", "", ean)[-4:]
        seen.add(slug)
        fake = {"name": m["name"] if m else item["name"], "cats": m["cats"] if m else []}
        cat, sub = classify(fake, brand_slug or "")
        cat, sub = ov.get("category", cat), ov.get("sub", sub)
        stock = item["stock"] or 0
        products.append({
            "id": slug, "ean": ean, "name": name, "brand": brand, "brand_slug": brand_slug or "",
            "category": cat, "sub": sub, "price": round(float(item["price"]), 3),
            "stock": stock, "instock": stock > 0,
            "image": f"images/products/{slug}.jpg" if m else "",
            "src_image": m["image"] if m else "",
            "bullets": m["bullets"] if m else [], "pos_name": item["name"], "match_score": r["score"],
        })
    print("products", len(products), "with image", sum(1 for p in products if p["src_image"]))
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda p: fetch_image(p["src_image"], p["id"]) if p["src_image"] else None, products))
    for p in products:
        if p["image"] and not os.path.exists(os.path.join(HERE, p["image"])):
            p["image"] = ""
        p.pop("src_image", None)
    json.dump(products, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(Counter(p["category"] for p in products))
    print("in stock:", sum(1 for p in products if p["instock"]), " with image:", sum(1 for p in products if p["image"]))


if __name__ == "__main__":
    main()
