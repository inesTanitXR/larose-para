#!/usr/bin/env python3
"""Générateur du site La Rose Parapharmacie.

    python3 build.py            # construit docs/
    python3 build.py --fast     # saute les fiches produit (aperçu rapide)

Contenu : config.py (coordonnées, livraison) + data/products.json (catalogue).
Sortie : docs/ — servi par GitHub Pages. Ne jamais éditer docs/ à la main.
"""
import html
import json
import os
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as C  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")
FAST = "--fast" in sys.argv

E = html.escape
import hashlib as _h
V = _h.md5((open(os.path.join(HERE,"assets-src","style.css"),"rb").read()+open(os.path.join(HERE,"assets-src","site.js"),"rb").read())).hexdigest()[:8]


def slugify(s):
    s = "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:80]


def money(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return f"{s} {C.CURRENCY}"


# ---------------------------------------------------------------- données
PRODUCTS = json.load(open(os.path.join(HERE, "data", "products.json")))
for p in PRODUCTS:
    p["url"] = f"produit/{p['id']}.html"
    p["cat_name"] = C.CATEGORY_META[p["category"]][0]
    p["sub_slug"] = slugify(p["sub"])

BY_CAT = defaultdict(list)
for p in PRODUCTS:
    BY_CAT[p["category"]].append(p)
for k in BY_CAT:
    BY_CAT[k].sort(key=lambda p: (not p["instock"], not p["image"], p["sub"], p["brand"], p["name"]))

SUBS = OrderedDict()
for cat in C.CATEGORY_ORDER:
    seen = OrderedDict()
    for p in BY_CAT.get(cat, []):
        seen.setdefault(p["sub"], 0)
        seen[p["sub"]] += 1
    SUBS[cat] = seen

BRANDS = defaultdict(list)
for p in PRODUCTS:
    if p["brand"]:
        BRANDS[p["brand"]].append(p)
BRAND_LIST = sorted(BRANDS, key=lambda b: (-len(BRANDS[b]), b))

# ---------------------------------------------------------------- icônes
ICON = {
    "truck": '<path d="M2 6h11v9H2zM13 9h4l3 3v3h-7z"/><circle cx="6" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
    "wallet": '<path d="M3 7a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><path d="M16 12h3"/>',
    "store": '<path d="M4 9v10h16V9"/><path d="M3 9l1.6-5h14.8L21 9a3 3 0 01-6 0 3 3 0 01-6 0 3 3 0 01-6 0z"/>',
    "chat": '<path d="M21 12a8 8 0 01-11.6 7.1L3 21l1.9-6A8 8 0 1121 12z"/>',
    "pin": '<path d="M12 21s7-6.3 7-11a7 7 0 10-14 0c0 4.7 7 11 7 11z"/><circle cx="12" cy="10" r="2.6"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/>',
    "phone": '<path d="M5 3h4l2 5-2.5 1.5a12 12 0 006 6L16 13l5 2v4a2 2 0 01-2.2 2A17 17 0 013 5.2 2 2 0 015 3z"/>',
    "check": '<path d="M4 12.5l5 5L20 6.5"/>',
    "shield": '<path d="M12 3l8 3v6c0 4.6-3.3 8.4-8 9-4.7-.6-8-4.4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "leaf": '<path d="M20 4C10 4 4 9 4 16c0 2 .6 3.4.6 3.4S8 12 20 4z"/><path d="M4 20c4-6 9-9 14-10"/>',
    "cart": '<circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/><path d="M2 3h3l2.6 12.4h11.2L21 7H6"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    "x": '<path d="M5 5l14 14M19 5L5 19"/>',
    "chev": '<path d="M1 1l5 5 5-5"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "box": '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
    "heart": '<path d="M12 20s-7-4.4-7-9.5A4.5 4.5 0 0112 8a4.5 4.5 0 017 2.5C19 15.6 12 20 12 20z"/>',
}


def ico(name, cls=""):
    return f'<svg viewBox="0 0 24 24"{f" class={cls}" if cls else ""} aria-hidden="true">{ICON[name]}</svg>'


WA_SVG = ('<svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 00-8.6 15L2 22l5.2-1.4A10 10 0 1012 2zm5.8 14.2c-.2.7-1.4 1.3-2 1.4-.5.1-1.1.1-1.8-.1-.4-.1-1-.3-1.7-.6-3-1.3-4.9-4.3-5-4.5-.2-.2-1.2-1.6-1.2-3s.7-2.1 1-2.4c.3-.3.6-.4.8-.4h.6c.2 0 .4 0 .6.5l.9 2.1c.1.2.1.4 0 .6l-.4.5-.3.3c-.1.1-.3.3-.1.6.1.3.6 1.1 1.4 1.8 1 .9 1.8 1.1 2 1.3.3.1.4.1.6-.1l.8-1c.2-.2.4-.2.6-.1l2 1c.3.1.4.2.5.3 0 .1 0 .6-.3 1.3z"/></svg>')
IG_SVG = '<svg viewBox="0 0 24 24"><path d="M12 2.2c3.2 0 3.6 0 4.9.1 1.2.1 1.8.2 2.2.4.6.2 1 .5 1.4.9.4.4.7.8.9 1.4.2.4.4 1 .4 2.2.1 1.3.1 1.7.1 4.8s0 3.5-.1 4.8c0 1.2-.2 1.8-.4 2.2-.2.6-.5 1-.9 1.4-.4.4-.8.7-1.4.9-.4.2-1 .4-2.2.4-1.3.1-1.7.1-4.9.1s-3.6 0-4.9-.1c-1.2 0-1.8-.2-2.2-.4-.6-.2-1-.5-1.4-.9-.4-.4-.7-.8-.9-1.4-.2-.4-.4-1-.4-2.2C2.2 15.5 2.2 15.1 2.2 12s0-3.5.1-4.8c0-1.2.2-1.8.4-2.2.2-.6.5-1 .9-1.4.4-.4.8-.7 1.4-.9.4-.2 1-.4 2.2-.4C8.5 2.2 8.9 2.2 12 2.2zm0 3.1A6.7 6.7 0 1018.7 12 6.7 6.7 0 0012 5.3zm0 11A4.3 4.3 0 1116.3 12 4.3 4.3 0 0112 16.3zM18.9 5a1.6 1.6 0 11-1.6-1.6A1.6 1.6 0 0118.9 5z"/></svg>'
FB_SVG_BTN = '<svg viewBox="0 0 24 24" style="fill:#fff"><path d="M12 2C6.5 2 2 6.1 2 11.3c0 2.9 1.4 5.5 3.7 7.2V22l3.4-1.9c.9.3 1.9.4 2.9.4 5.5 0 10-4.1 10-9.3S17.5 2 12 2zm1 12.5l-2.6-2.7-5 2.7 5.5-5.8 2.6 2.7 4.9-2.7-5.4 5.8z"/></svg>'
FB_SVG = '<svg viewBox="0 0 24 24"><path d="M22 12a10 10 0 10-11.6 9.9v-7H7.9V12h2.5V9.8c0-2.5 1.5-3.9 3.8-3.9 1.1 0 2.2.2 2.2.2v2.5h-1.3c-1.2 0-1.6.8-1.6 1.6V12h2.8l-.4 2.9h-2.4v7A10 10 0 0022 12z"/></svg>'


def wa_link(text=""):
    base = f"https://wa.me/{C.WHATSAPP}"
    if text:
        from urllib.parse import quote
        return base + "?text=" + quote(text)
    return base


# ---------------------------------------------------------------- gabarit
def nav_items(root):
    cats = "".join(
        f'<a href="{root}categorie/{c}.html">{E(C.CATEGORY_META[c][0])}<small>{len(BY_CAT.get(c, []))} produits</small></a>'
        for c in C.CATEGORY_ORDER if BY_CAT.get(c))
    return cats


def head(title, desc, root, extra="", og_image="images/site/hero.jpg", canonical=""):
    full = f"{title} | {C.SITE_NAME}" if title != C.SITE_NAME else f"{C.SITE_NAME} — {C.TAGLINE} à {C.CITY}"
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(full)}</title>
<meta name="description" content="{E(desc)}">
<meta property="og:title" content="{E(full)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:type" content="website">
<meta property="og:locale" content="fr_TN">
<meta property="og:image" content="{root}{og_image}">
<meta name="theme-color" content="#f2849d">
<link rel="icon" href="{root}images/site/favicon.png">
<link rel="apple-touch-icon" href="{root}images/site/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&family=Jost:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/style.css?v={V}">
<script>window.LR_ROOT="{root}";window.LR_CUR="{C.CURRENCY}";</script>
{extra}
</head>
<body>"""


def header(root, active=""):
    def on(k):
        return " class=on" if active == k else ""
    return f"""
<div class="topbar"><div class="wrap">
  <span>{ico('truck')} Livraison partout en Tunisie</span>
  <span>{ico('wallet')} Paiement à la livraison</span>
  <span>{ico('store')} Retrait en boutique à {E(C.CITY)}</span>
</div></div>
<header class="site"><div class="bar">
  <nav class="nav">
    <div class="drop"><button aria-haspopup="true">Nos rayons {ico('chev')}</button>
      <div class="dropmenu">{nav_items(root)}</div></div>
    <a href="{root}catalogue.html"{on('cat')}>Catalogue</a>
    <a href="{root}marques.html"{on('marques')}>Marques</a>
    <a href="{root}carte-rose.html"{on('rose')} style="color:var(--rose-ink)">✿ Carte Rose</a>
  </nav>
  <a class="logo" href="{root}index.html" aria-label="{E(C.SITE_NAME)} — accueil">
    <img src="{root}images/site/logo.png" alt="{E(C.SITE_NAME)}" width="438" height="147"></a>
  <div class="hactions">
    <a class="desk" href="{root}boutique.html" style="font-size:14.5px;margin-right:10px"{on('boutique')}>La boutique</a>
    <a class="desk" href="{root}commander.html" style="font-size:14.5px;margin-right:6px"{on('commander')}>Commander</a>
    <button class="icobtn" id="search-open" aria-label="Rechercher">{ico('search')}</button>
    <button class="icobtn" id="cart-open" aria-label="Panier">{ico('cart')}<span id="cart-count" hidden>0</span></button>
    <button class="icobtn" id="nav-toggle" aria-label="Menu"><svg viewBox="0 0 24 24"><path d="M3 6h18M3 12h18M3 18h18"/></svg></button>
  </div>
</div></header>

<div id="scrim"></div>
<nav id="mobnav" aria-label="Menu">
  <button class="icobtn x" data-close aria-label="Fermer">{ico('x')}</button>
  <h4>Nos rayons</h4>
  {''.join(f'<a href="{root}categorie/{c}.html">{E(C.CATEGORY_META[c][0])}</a>' for c in C.CATEGORY_ORDER if BY_CAT.get(c))}
  <h4>La parapharmacie</h4>
  <a href="{root}catalogue.html">Tout le catalogue</a>
  <a href="{root}marques.html">Marques</a>
  <a href="{root}carte-rose.html" style="color:var(--rose-ink)">✿ Carte Rose — fidélité</a>
  <a href="{root}boutique.html">La boutique</a>
  <a href="{root}commander.html">Comment commander</a>
  <a href="{root}contact.html">Contact</a>
  <a class="btn btn-wa" style="margin-top:22px" href="{wa_link('Bonjour La Rose, je souhaite des conseils.')}" target="_blank" rel="noopener">{WA_SVG} Écrire sur WhatsApp</a>
</nav>

<div id="searchbox" role="dialog" aria-label="Recherche">
  <button class="icobtn" data-close style="position:absolute;top:22px;right:22px">{ico('x')}</button>
  <div class="in"><form role="search">
    <input id="sq" type="search" placeholder="Rechercher un produit, une marque…" autocomplete="off" aria-label="Rechercher">
  </form><div id="sresults"></div></div>
</div>

<aside id="drawer" aria-label="Panier">
  <div class="dh"><h3>Votre panier</h3><button class="icobtn" data-close aria-label="Fermer">{ico('x')}</button></div>
  <div class="items"></div><div class="df"></div>
</aside>
<div id="toast">{ico('check')}<span></span></div>
"""


def footer(root):
    cats = "".join(f'<li><a href="{root}categorie/{c}.html">{E(C.CATEGORY_META[c][0])}</a></li>'
                   for c in C.CATEGORY_ORDER if BY_CAT.get(c))
    hours = "".join(f'<li>{E(d)} · {E(h)}</li>' for d, h in C.HOURS)
    return f"""
<a class="wafloat" href="{wa_link('Bonjour La Rose, je souhaite passer une commande.')}" target="_blank" rel="noopener" aria-label="WhatsApp">{WA_SVG}</a>
<footer class="site"><div class="wrap">
 <div class="fgrid">
  <div>
   <div class="flogo"><img src="{root}images/site/logo.png" alt="{E(C.SITE_NAME)}" width="438" height="147"></div>
   <p>{E(C.TAGLINE)}. Soins pour la peau, les cheveux, bébé et bien-être — sélectionnés et conseillés en boutique à {E(C.CITY)}.</p>
   <div class="socials">
     <a href="{C.INSTAGRAM}" target="_blank" rel="noopener" aria-label="Instagram">{IG_SVG}</a>
     <a href="{C.FACEBOOK}" target="_blank" rel="noopener" aria-label="Facebook">{FB_SVG}</a>
     <a href="{wa_link()}" target="_blank" rel="noopener" aria-label="WhatsApp">{WA_SVG}</a>
   </div>
  </div>
  <div><h4>Nos rayons</h4><ul>{cats}</ul></div>
  <div><h4>La parapharmacie</h4><ul>
    <li><a href="{root}boutique.html">La boutique</a></li>
    <li><a href="{root}marques.html">Nos marques</a></li>
    <li><a href="{root}carte-rose.html">Carte Rose (fidélité)</a></li>
    <li><a href="{root}commander.html">Comment commander</a></li>
    <li><a href="{root}livraison.html">Livraison & retrait</a></li>
    <li><a href="{root}contact.html">Contact</a></li>
  </ul></div>
  <div><h4>Nous trouver</h4><ul>
    <li><a href="{C.MAPS_URL}" target="_blank" rel="noopener">{E(C.ADDRESS)}, {E(C.CITY)}</a></li>
    <li><a href="tel:{C.PHONE_INTL}">{E(C.PHONE)}</a></li>
    {hours}
  </ul></div>
 </div>
 <div class="fbot">
   <span>© 2026 {E(C.SITE_NAME)} — {E(C.CITY)}, {E(C.COUNTRY)}</span>
   <span>Paiement à la livraison ou en boutique · aucun paiement en ligne</span>
 </div>
</div></footer>
<script src="{root}assets/site.js?v={V}" defer></script>
</body></html>"""


def page(path, title, desc, body, active="", root="", extra_head="", og=None):
    out = os.path.join(DOCS, path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    doc = head(title, desc, root, extra_head, og or "images/site/hero.jpg") + header(root, active) + body + footer(root)
    open(out, "w", encoding="utf-8").write(doc)


# ---------------------------------------------------------------- composants
def card(p, root=""):
    img = (f'<img src="{root}{p["image"]}" alt="{E(p["name"])}" loading="lazy" width="700" height="700">'
           if p["image"] else
           f'<div class="noimg"><span>{E(p["brand"] or C.SITE_SHORT)}<em>La Rose</em></span></div>')
    tag = ""
    if not p["instock"]:
        tag = '<span class="tag out">Sur commande</span>'
    payload = E(json.dumps({"id": p["id"], "n": p["name"], "b": p["brand"], "p": p["price"],
                            "img": p["image"], "u": p["url"]}, ensure_ascii=False), quote=True)
    return f"""<article class="card">
 <a class="cardlink" href="{root}{p['url']}" aria-label="{E(p['name'])}"></a>
 <div class="ph">{tag}{img}</div>
 <div class="body">
  <span class="brand">{E(p['brand'] or '&nbsp;')}</span>
  <h3 class="nm">{E(p['name'])}</h3>
  <div class="foot"><span class="price">{money(p['price'])}</span>
   <button class="add" data-add='{payload}' aria-label="Ajouter {E(p['name'])} au panier">{ico('plus')}</button></div>
 </div></article>"""


def cards(items, root=""):
    return "".join(card(p, root) for p in items)


TRUST = f"""<div class="trust"><div class="wrap">
 <div>{ico('truck')}<div><b>Livraison partout en Tunisie</b><small>Sous {C.DELIVERY_DAYS} · offerte dès {money(C.FREE_DELIVERY_FROM)}</small></div></div>
 <div>{ico('wallet')}<div><b>Paiement à la livraison</b><small>Vous réglez en espèces à la réception</small></div></div>
 <div>{ico('store')}<div><b>Retrait en boutique</b><small>Commandez ici, récupérez à {E(C.CITY)}</small></div></div>
 <div>{ico('chat')}<div><b>Conseil personnalisé</b><small>Une question ? Écrivez-nous sur WhatsApp</small></div></div>
</div></div>"""


# ---------------------------------------------------------------- pages
def build_home():
    feat = [p for p in PRODUCTS if p["instock"] and p["image"]]
    best = sorted(feat, key=lambda p: (p["category"] != "visage", -p["price"]))
    sel, seen_brand = [], Counter()
    for p in sorted(feat, key=lambda p: (-len(p.get("bullets") or []), p["name"])):
        if seen_brand[p["brand"]] < 1 and len(sel) < 12:
            sel.append(p); seen_brand[p["brand"]] += 1
    solaire = [p for p in BY_CAT.get("solaire", []) if p["image"] and p["instock"]][:10]
    bebe = [p for p in BY_CAT.get("bebe", []) if p["image"] and p["instock"]][:10]

    cat_cards = ""
    for i, c in enumerate(C.CATEGORY_ORDER[:8]):
        if not BY_CAT.get(c):
            continue
        name, desc, img = C.CATEGORY_META[c]
        cat_cards += f"""<a class="cat" href="categorie/{c}.html">
          <img src="images/site/{img}" alt="" loading="lazy">
          <div class="t"><b>{E(name)}</b><small>{E(desc)}</small></div></a>"""

    brands = "".join(f'<a href="marque/{slugify(b)}.html">{E(b)}</a>'
                     for b in C.FEATURED_BRANDS if b in BRANDS)

    body = f"""
<section class="hero" style="padding:0">
 <div class="in">
  <div class="txt">
   <span class="eyebrow">Parapharmacie à {E(C.CITY)}</span>
   <h1>Le soin qu'il vous faut,<br><em>conseillé comme en boutique.</em></h1>
   <p>Plus de {str(len(PRODUCTS)).replace(',', ' ')} références dermocosmétiques — visage, solaire, cheveux, bébé, compléments et matériel médical. Vous commandez, nous livrons, vous payez à la réception.</p>
   <div class="ctas">
     <a class="btn btn-rose" href="catalogue.html">{ico('cart')} Découvrir le catalogue</a>
     <a class="btn btn-line" href="{wa_link('Bonjour La Rose, je cherche un conseil produit.')}" target="_blank" rel="noopener">{WA_SVG} Demander conseil</a>
   </div>
  </div>
  <div class="art"><div class="petal"></div>
    <img src="images/site/hero.jpg" alt="Sélection de soins dermocosmétiques" width="1400" height="1000"></div>
 </div>
</section>
{TRUST.replace(',', ',')}

<section>
 <div class="wrap">
  <div class="sec-head row"><div>
    <span class="eyebrow">Nos rayons</span>
    <h2>Tout le soin, rayon par rayon</h2>
    <p>Les mêmes marques qu'en boutique : dermocosmétique de pharmacie, hygiène, puériculture et matériel médical.</p>
  </div><a class="btn btn-line btn-sm" href="catalogue.html">Voir tout le catalogue</a></div>
  <div class="cats">{cat_cards}</div>
 </div>
</section>

<section class="bg-cream">
 <div class="wrap">
  <div class="sec-head row"><div><span class="eyebrow">Sélection</span><h2>Nos essentiels du moment</h2></div>
    <a class="btn btn-line btn-sm" href="catalogue.html">Tout voir</a></div>
  <div class="grid">{cards(sel[:8])}</div>
 </div>
</section>

<section>
 <div class="wrap">
  <div class="sec-head row"><div><span class="eyebrow">Protection solaire</span><h2>Écrans SPF 50+</h2>
    <p>Fluides invisibles, teintés, minéraux — pour le visage, le corps et les enfants.</p></div>
    <a class="btn btn-line btn-sm" href="categorie/solaire.html">Voir le rayon</a></div>
  <div class="rail">{cards(solaire)}</div>
 </div>
</section>

<section class="bg-petal">
 <div class="wrap">
  <div class="sec-head center"><span class="eyebrow">Comment ça marche</span>
    <h2>Commander en trois étapes</h2>
    <p style="margin:10px auto 0">Aucun paiement en ligne : vous réglez en espèces à la livraison, ou en boutique au retrait.</p></div>
  <div class="steps">
   <div class="step"><h3>Vous composez votre panier</h3><p>Parcourez le catalogue, ajoutez vos produits. Une question sur un soin ? Écrivez-nous, on vous oriente.</p></div>
   <div class="step"><h3>Vous validez la commande</h3><p>Nom, téléphone, adresse — et c'est tout. Votre commande nous parvient immédiatement.</p></div>
   <div class="step"><h3>Vous payez à la réception</h3><p>Livraison partout en Tunisie sous {C.DELIVERY_DAYS}, paiement en espèces au livreur. Ou retrait gratuit à la parapharmacie.</p></div>
  </div>
 </div>
</section>

<section>
 <div class="wrap">
  <div class="sec-head row"><div><span class="eyebrow">Bébé & maman</span><h2>Pour les tout-petits</h2>
    <p>Toilette, change, biberons, allaitement — les marques de confiance des maternités.</p></div>
    <a class="btn btn-line btn-sm" href="categorie/bebe.html">Voir le rayon</a></div>
  <div class="rail">{cards(bebe)}</div>
 </div>
</section>


<section class="bg-petal">
 <div class="wrap"><div class="homerose">
  <div class="bloom"><div id="home-rose"></div></div>
  <div>
   <span class="eyebrow">Programme de fidélité</span>
   <h2>Votre rose s'ouvre<br>à chaque commande</h2>
   <ul>
    <li><span>✿</span><span><b>1 dinar = 1 pétale.</b> Tous les 250 pétales, un bon de {money(C.LOYALTY_BON)} sur votre prochaine commande.</span></li>
    <li><span>🎁</span><span><b>Cadeau de bienvenue</b> glissé dans votre première commande.</span></li>
    <li><span>🎂</span><span><b>Une surprise</b> le mois de votre anniversaire.</span></li>
    <li><span>💌</span><span><b>Parrainez une amie :</b> vous gagnez toutes les deux des pétales.</span></li>
   </ul>
   <a class="btn btn-rose" href="carte-rose.html">Découvrir la Carte Rose</a>
  </div>
 </div></div>
</section>
<script>document.addEventListener('DOMContentLoaded',function(){{document.getElementById('home-rose').innerHTML=window.LRroseSVG('hr');document.getElementById('hr').setAttribute('data-rose','');window.LRloyalRepaint();}});</script>
<section class="bg-cream">
 <div class="wrap">
  <div class="split">
   <div>
    <span class="eyebrow">La boutique</span>
    <h2>Venez nous voir à {E(C.CITY)}</h2>
    <p class="lead" style="margin:16px 0 22px">Notre parapharmacie est {E(C.ADDRESS.lower())}, à {E(C.CITY)}. On y trouve toute la dermocosmétique de pharmacie, un rayon bébé complet, le matériel médical — et surtout quelqu'un pour vous conseiller.</p>
    <div class="ctas" style="display:flex;gap:12px;flex-wrap:wrap">
      <a class="btn btn-ink" href="boutique.html">Découvrir la boutique</a>
      <a class="btn btn-line" href="{C.MAPS_URL}" target="_blank" rel="noopener">{ico('pin')} Itinéraire</a>
    </div>
   </div>
   <div class="gallery">
     <img src="images/site/store-sign.jpg" alt="Enseigne La Rose Parapharmacie" loading="lazy">
     <img src="images/site/store-arches.jpg" alt="Rayon bébé" loading="lazy">
     <img src="images/site/store-oval.jpg" alt="Rayon soins capillaires" loading="lazy">
   </div>
  </div>
 </div>
</section>

<section class="tight">
 <div class="wrap center">
  <span class="eyebrow">Nos marques</span>
  <h2 style="margin-bottom:26px">{len(BRAND_LIST)} marques disponibles</h2>
  <div class="brands">{brands}</div>
  <p style="margin-top:26px"><a class="btn btn-line btn-sm" href="marques.html">Voir toutes les marques</a></p>
 </div>
</section>
"""
    page("index.html", C.SITE_NAME, C.DESCRIPTION, body, active="home")


def facet_html(cats, brands, subs, root):
    def group(title, name, items, limit=8):
        rows = ""
        for i, (val, label, n) in enumerate(items):
            hid = ' hidden' if i >= limit else ''
            rows += (f'<label{hid} data-x><input type="checkbox" name="{name}" value="{E(val, quote=True)}">'
                     f'<span>{E(label)}</span><span class="cnt">{n}</span></label>')
        more = f'<button class="more" data-more>Voir tout ({len(items)})</button>' if len(items) > limit else ''
        return f'<div class="fg"><h4>{title}</h4>{rows}{more}</div>'

    html_out = '<form class="facets" id="facets"><button class="icobtn" data-close style="position:absolute;top:14px;right:14px" aria-label="Fermer">' + ico('x') + '</button>'
    if cats:
        html_out += group("Rayon", "cat", cats, 12)
    if subs:
        html_out += group("Catégorie", "sub", subs, 8)
    html_out += group("Marque", "brand", brands, 10)
    html_out += ('<div class="fg"><h4>Prix</h4>'
                 '<label><input type="checkbox" name="price" value="0-25"><span>Moins de 25 DT</span></label>'
                 '<label><input type="checkbox" name="price" value="25-50"><span>25 – 50 DT</span></label>'
                 '<label><input type="checkbox" name="price" value="50-100"><span>50 – 100 DT</span></label>'
                 '<label><input type="checkbox" name="price" value="100-9999"><span>Plus de 100 DT</span></label></div>')
    html_out += ('<div class="fg"><h4>Disponibilité</h4>'
                 '<label><input type="checkbox" name="stock" value="1"><span>En stock uniquement</span></label></div>')
    html_out += '</form>'
    return html_out


SHOP_JS = """
<script>
document.addEventListener('DOMContentLoaded',function(){
  var R=window.LR_ROOT||'', PER=48, all=[], view=[], shown=0;
  var q=new URLSearchParams(location.search);
  var box=document.getElementById('plist'), bar=document.getElementById('pcount'),
      chips=document.getElementById('chips'), sortSel=document.getElementById('sort'),
      form=document.getElementById('facets'), more=document.getElementById('more-wrap');
  var BASE=window.LR_BASE||null;
  function money(n){return window.LRmoney(n);}
  function cardHTML(p){
    var img=p.i?'<img src="'+R+p.i+'" alt="'+window.LResc(p.n)+'" loading="lazy">':
      '<div class="noimg"><span>'+window.LResc(p.b||'La Rose')+'<em>La Rose</em></span></div>';
    var tag=p.k?'':'<span class="tag out">Sur commande</span>';
    var pay=window.LResc(JSON.stringify({id:p.id,n:p.n,b:p.b,p:p.p,img:p.i,u:p.u}));
    return '<article class="card"><a class="cardlink" href="'+R+p.u+'" aria-label="'+window.LResc(p.n)+'"></a>'+
      '<div class="ph">'+tag+img+'</div><div class="body"><span class="brand">'+window.LResc(p.b||'')+'</span>'+
      '<h3 class="nm">'+window.LResc(p.n)+'</h3><div class="foot"><span class="price">'+money(p.p)+'</span>'+
      '<button class="add" data-add=\\''+pay.replace(/'/g,"&#39;")+'\\' aria-label="Ajouter au panier"><svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg></button></div></div></article>';
  }
  function state(){
    var s={cat:[],sub:[],brand:[],price:[],stock:[]};
    if(form) form.querySelectorAll('input:checked').forEach(function(i){s[i.name].push(i.value);});
    s.q=(q.get('q')||'').trim();
    return s;
  }
  function apply(){
    var s=state(), nq=s.q?window.LRnorm(s.q).split(/\\s+/).filter(Boolean):[];
    view=all.filter(function(p){
      if(s.cat.length&&s.cat.indexOf(p.c)<0)return false;
      if(s.sub.length&&s.sub.indexOf(p.sb)<0)return false;
      if(s.brand.length&&s.brand.indexOf(p.b)<0)return false;
      if(s.stock.length&&!p.k)return false;
      if(s.price.length){
        var ok=s.price.some(function(r){var a=r.split('-');return p.p>=+a[0]&&p.p<+a[1];});
        if(!ok)return false;
      }
      if(nq.length){for(var i=0;i<nq.length;i++) if(p.s.indexOf(nq[i])<0) return false;}
      return true;
    });
    var by=sortSel?sortSel.value:'rec';
    view.sort(function(a,b){
      if(by==='asc')return a.p-b.p;
      if(by==='desc')return b.p-a.p;
      if(by==='az')return a.n.localeCompare(b.n,'fr');
      return (b.k-a.k)||((b.i?1:0)-(a.i?1:0))||a.n.localeCompare(b.n,'fr');
    });
    shown=0; box.innerHTML='';
    render();
    bar.textContent=view.length+(view.length>1?' produits':' produit');
    // chips
    var c='';
    ['cat','sub','brand','price'].forEach(function(k){
      s[k].forEach(function(v){
        var lbl=v; if(k==='cat'&&window.LR_CATNAMES)lbl=window.LR_CATNAMES[v]||v;
        if(k==='price')lbl=v.replace('-',' – ').replace(' – 9999','+ DT').replace(/$/,v.indexOf('9999')<0?' DT':'');
        c+='<span class="chip">'+window.LResc(lbl)+'<button data-un="'+k+'|'+window.LResc(v)+'" aria-label="Retirer"><svg viewBox="0 0 24 24"><path d="M5 5l14 14M19 5L5 19"/></svg></button></span>';
      });
    });
    if(s.q)c+='<span class="chip">« '+window.LResc(s.q)+' »<button data-unq aria-label="Retirer"><svg viewBox="0 0 24 24"><path d="M5 5l14 14M19 5L5 19"/></svg></button></span>';
    if(c)c+='<button class="chip" data-clear style="background:none;border-color:var(--line);color:var(--gray)">Tout effacer</button>';
    chips.innerHTML=c;
  }
  function render(){
    var slice=view.slice(shown,shown+PER);
    if(!view.length){box.innerHTML='<div class="empty"><h3>Aucun produit ne correspond</h3><p>Essayez d\\'élargir vos filtres, ou demandez-nous : nous commandons sur demande.</p></div>';more.innerHTML='';return;}
    box.insertAdjacentHTML('beforeend',slice.map(cardHTML).join(''));
    shown+=slice.length;
    more.innerHTML=shown<view.length?'<button class="btn btn-line" id="loadmore">Afficher plus ('+(view.length-shown)+' restants)</button>':'';
  }
  document.addEventListener('click',function(e){
    if(e.target.closest('#loadmore')){render();return;}
    var m=e.target.closest('[data-more]');
    if(m){m.parentNode.querySelectorAll('[data-x][hidden]').forEach(function(l){l.hidden=false;});m.remove();return;}
    var u=e.target.closest('[data-un]');
    if(u){var a=u.getAttribute('data-un').split('|');
      form.querySelectorAll('input[name="'+a[0]+'"]').forEach(function(i){if(i.value===a[1])i.checked=false;});
      apply();return;}
    if(e.target.closest('[data-unq]')){q.delete('q');history.replaceState({},'',location.pathname);apply();return;}
    if(e.target.closest('[data-clear]')){form.reset();q.delete('q');history.replaceState({},'',location.pathname);apply();return;}
  });
  if(form)form.addEventListener('change',apply);
  if(sortSel)sortSel.addEventListener('change',apply);
  window.LRindex(function(list){
    all=BASE?list.filter(BASE):list;
    var qq=q.get('q'); if(qq){var si=document.getElementById('sq');if(si)si.value=qq;}
    var pre=q.get('sub'); if(pre&&form){form.querySelectorAll('input[name=sub]').forEach(function(i){if(i.value===pre)i.checked=true;});}
    apply();
  });
});
</script>"""


def shop_page(path, title, desc, intro_html, root, base_js, cats, subs, brands, active="", crumb=""):
    facets = facet_html(cats, brands, subs, root)
    body = f"""
<div class="page-hero"><div class="wrap">{crumb}<h1>{E(title)}</h1><p>{desc}</p></div></div>
<div class="wrap"><div class="shop">
  {facets}
  <div>
    <div class="shopbar">
      <button class="btn btn-line btn-sm" id="filter-open">Filtrer</button>
      <span class="n" id="pcount">…</span>
      <select id="sort" aria-label="Trier">
        <option value="rec">Tri : pertinence</option>
        <option value="asc">Prix croissant</option>
        <option value="desc">Prix décroissant</option>
        <option value="az">Nom (A → Z)</option>
      </select>
    </div>
    <div class="chips" id="chips"></div>
    <div class="grid" id="plist"></div>
    <div id="more-wrap"></div>
  </div>
</div></div>
<script>window.LR_BASE={base_js};window.LR_CATNAMES={json.dumps({k: v[0] for k, v in C.CATEGORY_META.items()}, ensure_ascii=False)};</script>
{SHOP_JS}"""
    page(path, title, re.sub("<[^>]+>", "", desc), body, active=active, root=root)


def build_catalogue():
    cats = [(c, C.CATEGORY_META[c][0], len(BY_CAT[c])) for c in C.CATEGORY_ORDER if BY_CAT.get(c)]
    subs = [(s, s, n) for c in C.CATEGORY_ORDER for s, n in SUBS.get(c, {}).items()]
    subs.sort(key=lambda x: -x[2])
    brands = [(b, b, len(BRANDS[b])) for b in BRAND_LIST]
    shop_page("catalogue.html", "Tout le catalogue",
              f"{len(PRODUCTS)} références disponibles à la parapharmacie — filtrez par rayon, marque ou budget.",
              "", "", "null", cats, subs, brands, active="cat",
              crumb='<div class="crumb"><a href="index.html">Accueil</a><span>›</span>Catalogue</div>')


def build_categories():
    for c in C.CATEGORY_ORDER:
        items = BY_CAT.get(c)
        if not items:
            continue
        name, desc, _ = C.CATEGORY_META[c]
        subs = [(s, s, n) for s, n in SUBS[c].items()]
        bc = Counter(p["brand"] for p in items if p["brand"])
        brands = [(b, b, n) for b, n in bc.most_common()]
        shop_page(f"categorie/{c}.html", name, f"{desc} {len(items)} références.",
                  "", "../", f'function(p){{return p.c==="{c}";}}',
                  [], subs, brands,
                  crumb=f'<div class="crumb"><a href="../index.html">Accueil</a><span>›</span><a href="../catalogue.html">Catalogue</a><span>›</span>{E(name)}</div>')


def build_brands():
    rows = ""
    letters = defaultdict(list)
    for b in sorted(BRANDS, key=lambda x: slugify(x)):
        letters[slugify(b)[0].upper()].append(b)
    for L in sorted(letters):
        items = "".join(f'<a href="marque/{slugify(b)}.html">{E(b)} <span class="muted" style="font-size:12px">({len(BRANDS[b])})</span></a>'
                        for b in letters[L])
        rows += f'<div style="margin-bottom:34px"><h3 style="color:var(--rose);margin-bottom:14px">{L}</h3><div class="brands" style="justify-content:flex-start">{items}</div></div>'
    body = f"""
<div class="page-hero"><div class="wrap">
 <div class="crumb"><a href="index.html">Accueil</a><span>›</span>Marques</div>
 <h1>Nos marques</h1><p>{len(BRAND_LIST)} marques en rayon — dermocosmétique de pharmacie, puériculture, compléments et matériel médical.</p></div></div>
<section><div class="wrap">{rows}</div></section>"""
    page("marques.html", "Nos marques", f"Les {len(BRAND_LIST)} marques disponibles à La Rose Parapharmacie, Nabeul.",
         body, active="marques")

    for b, items in BRANDS.items():
        if len(items) < 1:
            continue
        cats = Counter(p["category"] for p in items)
        cl = [(c, C.CATEGORY_META[c][0], n) for c, n in cats.most_common()]
        subs = [(s, s, n) for s, n in Counter(p["sub"] for p in items).most_common()]
        shop_page(f"marque/{slugify(b)}.html", b,
                  f"{len(items)} références {E(b)} disponibles à la parapharmacie.",
                  "", "../", f'function(p){{return p.b==={json.dumps(b, ensure_ascii=False)};}}',
                  cl, subs, [], active="marques",
                  crumb=f'<div class="crumb"><a href="../index.html">Accueil</a><span>›</span><a href="../marques.html">Marques</a><span>›</span>{E(b)}</div>')


def build_products():
    root = "../"
    for p in PRODUCTS:
        img = (f'<img src="{root}{p["image"]}" alt="{E(p["name"])}" width="700" height="700">'
               if p["image"] else
               f'<div class="noimg"><span>{E(p["brand"] or C.SITE_SHORT)}<em>{E(p["name"][:38])}</em></span></div>')
        bullets = ""
        if p.get("bullets"):
            lis = "".join(f"<li>{E(b)}</li>" for b in p["bullets"][:10])
            bullets = f'<div class="bullets"><h4>En bref</h4><ul>{lis}</ul></div>'
        stock = ('<span class="stock">En stock — expédié sous 24 h</span>' if p["instock"]
                 else '<span class="stock out">Sur commande — nous consulter</span>')
        payload = E(json.dumps({"id": p["id"], "n": p["name"], "b": p["brand"], "p": p["price"],
                                "img": p["image"], "u": p["url"]}, ensure_ascii=False), quote=True)
        rel = [x for x in BY_CAT[p["category"]] if x["sub"] == p["sub"] and x["id"] != p["id"] and x["image"]][:5]
        if len(rel) < 5:
            rel += [x for x in BY_CAT[p["category"]] if x["id"] != p["id"] and x["image"] and x not in rel][:5 - len(rel)]
        wa = wa_link(f"Bonjour La Rose, je souhaite commander : {p['name']}" + (f" ({p['brand']})" if p["brand"] else ""))
        brandline = (f'<a class="brandline" href="{root}marque/{slugify(p["brand"])}.html">{E(p["brand"])}</a>'
                     if p["brand"] else "")
        ld = {"@context": "https://schema.org", "@type": "Product", "name": p["name"],
              "brand": p["brand"] or C.SITE_NAME, "sku": p.get("ean", p["id"]),
              "offers": {"@type": "Offer", "price": f"{p['price']:.3f}", "priceCurrency": "TND",
                         "availability": "https://schema.org/InStock" if p["instock"] else "https://schema.org/PreOrder"}}
        if p["image"]:
            ld["image"] = p["image"]
        body = f"""
<div class="wrap"><div class="crumb" style="padding-top:22px">
 <a href="{root}index.html">Accueil</a><span>›</span>
 <a href="{root}categorie/{p['category']}.html">{E(p['cat_name'])}</a><span>›</span>
 <a href="{root}categorie/{p['category']}.html?sub={E(p['sub'], quote=True)}">{E(p['sub'])}</a></div>
<div class="pdp">
 <div class="gal">{img}</div>
 <div>
  {brandline}
  <h1>{E(p['name'])}</h1>
  <div class="pricebig">{money(p['price'])}</div>
  {stock}
  <div class="qtyrow">
   <div class="qty"><button data-q="-" aria-label="Moins">−</button>
     <input id="qty" type="number" value="1" min="1" aria-label="Quantité">
     <button data-q="+" aria-label="Plus">+</button></div>
   <button class="btn btn-rose" data-add='{payload}' data-usa-qty style="flex:1;min-width:190px">{ico('cart')} Ajouter au panier</button>
  </div>
  <a class="btn btn-wa btn-block" href="{wa}" target="_blank" rel="noopener">{WA_SVG} Commander sur WhatsApp</a>
  {bullets}
  <div class="reassure">
   <div>{ico('truck')}<span>Livraison partout en Tunisie sous {C.DELIVERY_DAYS} — offerte à partir de {money(C.FREE_DELIVERY_FROM)}.</span></div>
   <div>{ico('wallet')}<span>Paiement en espèces à la livraison. Aucun paiement en ligne.</span></div>
   <div>{ico('store')}<span>Retrait gratuit à la parapharmacie, {E(C.ADDRESS)}, {E(C.CITY)}.</span></div>
  </div>
  <div class="meta">
   <div><dt>Marque</dt><dd>{E(p['brand'] or '—')}</dd></div>
   <div><dt>Rayon</dt><dd>{E(p['cat_name'])} · {E(p['sub'])}</dd></div>
   {'<div><dt>Référence</dt><dd>' + E(str(p.get('ean', ''))) + '</dd></div>' if p.get('ean') else ''}
  </div>
 </div>
</div></div>
{'<section class="bg-cream"><div class="wrap"><div class="sec-head"><h2 style="font-size:28px">Dans le même rayon</h2></div><div class="grid">' + cards(rel, root) + '</div></div></section>' if rel else ''}
"""
        extra = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
        page(p["url"], p["name"], f"{p['name']} — {p['brand']}. {money(p['price'])}. Disponible à La Rose Parapharmacie, {C.CITY}. Livraison en Tunisie, paiement à la livraison.",
             body, root=root, extra_head=extra, og=p["image"] or "images/site/hero.jpg")


def build_cart():
    govs = "".join(f'<option>{E(g)}</option>' for g in C.GOVERNORATES)
    body = f"""
<div class="page-hero"><div class="wrap">
 <div class="crumb"><a href="index.html">Accueil</a><span>›</span>Panier</div>
 <h1>Finaliser ma commande</h1>
 <p>Paiement à la livraison ou en boutique — aucune carte bancaire n'est demandée.</p></div></div>

<section><div class="wrap">
 <div id="confirm" style="display:none" class="wrap-narrow center">
   <div style="width:76px;height:76px;border-radius:50%;background:#e6f6ec;display:grid;place-items:center;margin:0 auto 22px">
     <svg viewBox="0 0 24 24" style="width:36px;height:36px;stroke:#2e9e5b;fill:none;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round"><path d="M4 12.5l5 5L20 6.5"/></svg></div>
   <span class="eyebrow">Commande confirmée</span>
   <h2>Merci <span id="c-name"></span> !</h2>
   <p class="lead" style="margin:14px auto 6px">Votre commande <strong id="c-num"></strong> est enregistrée.</p>
   <p class="muted" id="c-next"></p>
   <div class="infocard" style="text-align:left;margin:30px auto;max-width:560px"><h3 style="font-size:18px">Récapitulatif</h3><div id="c-sum"></div></div>
   <p class="muted" style="font-size:13.5px">Une question sur votre commande ? <a href="{wa_link("Bonjour, j'ai une question sur ma commande ")}" target="_blank" rel="noopener" style="color:var(--rose-ink);text-decoration:underline">WhatsApp</a> · <a href="tel:{C.PHONE_INTL}" style="color:var(--rose-ink);text-decoration:underline">{E(C.PHONE)}</a></p>
   <p style="margin-top:26px"><a class="btn btn-rose" href="catalogue.html">Continuer mes achats</a> <a class="btn btn-line" style="margin-left:8px" href="carte-rose.html">Voir ma Carte Rose</a></p>
 </div>

 <div id="cart-page" style="display:grid;grid-template-columns:1.25fr .75fr;gap:48px;align-items:start">
  <div>
   <h3 style="margin-bottom:8px">Vos produits</h3>
   <div id="cart-lines"></div>
   <div id="cart-empty" style="display:none" class="emptycart">
     {ico('cart')}<p style="margin:14px 0 18px">Votre panier est vide pour le moment.</p>
     <a class="btn btn-rose" href="catalogue.html">Parcourir le catalogue</a>
   </div>

   <form id="order" style="margin-top:44px" novalidate>
    <h3 style="margin-bottom:18px">Livraison</h3>
    <label class="opt on"><input type="radio" name="mode" value="livraison" checked>
      <span><b>Livraison à domicile</b>
      <small>Partout en Tunisie sous {C.DELIVERY_DAYS}. Frais {money(C.DELIVERY_FEE)}, offerts dès {money(C.FREE_DELIVERY_FROM)} d'achat. Paiement en espèces à la réception.</small></span></label>
    <label class="opt"><input type="radio" name="mode" value="retrait">
      <span><b>Retrait en boutique — gratuit</b>
      <small>{E(C.ADDRESS)}, {E(C.CITY)}. Nous vous prévenons dès que votre commande est prête. Paiement sur place.</small></span></label>

    <h3 style="margin:34px 0 18px">Vos coordonnées</h3>
    <div class="row2">
      <div class="field"><label for="nom">Nom et prénom <span class="req">*</span></label>
        <input id="nom" name="nom" required autocomplete="name"><div class="msg">Merci d'indiquer votre nom.</div></div>
      <div class="field"><label for="tel">Téléphone <span class="req">*</span></label>
        <input id="tel" name="tel" type="tel" required autocomplete="tel" placeholder="ex. 20 123 456">
        <div class="msg">Un numéro à 8 chiffres est nécessaire.</div></div>
    </div>
    <div id="addr">
      <div class="row2">
        <div class="field"><label for="gov">Gouvernorat <span class="req">*</span></label>
          <select id="gov" name="gouvernorat"><option value="">Choisir…</option>{govs}</select>
          <div class="msg">Choisissez votre gouvernorat.</div></div>
        <div class="field"><label for="ville">Ville / délégation <span class="req">*</span></label>
          <input id="ville" name="ville"><div class="msg">Indiquez votre ville.</div></div>
      </div>
      <div class="field"><label for="adresse">Adresse complète <span class="req">*</span></label>
        <input id="adresse" name="adresse" placeholder="Rue, immeuble, étage, points de repère">
        <div class="msg">L'adresse permet au livreur de vous trouver.</div></div>
    </div>

    <div class="loyalbox">
      <div class="mini" id="cart-rose"></div>
      <div style="flex:1">
        <b>Carte Rose</b> · <span data-rose-petals>0</span> pétales — cette commande vous en rapporte <b id="gain">0</b>.
        <label id="redeem-row" style="display:none"><input type="checkbox" id="redeem"> Utiliser 250 pétales : <b>−{money(C.LOYALTY_BON)}</b> sur cette commande</label>
        <div class="row2" style="margin-top:10px;gap:10px">
          <div class="field" style="margin:0"><input id="prenom" name="prenom" placeholder="Prénom (pour votre carte)"></div>
          <div class="field" style="margin:0"><input id="parrain" name="parrain" placeholder="Code parrainage ROSE-xxxx" style="text-transform:uppercase"></div>
        </div>
      </div>
    </div>

    <div class="field"><label for="notes">Instructions (facultatif)</label>
      <textarea id="notes" name="notes" placeholder="Horaires de livraison, précisions sur l'adresse…"></textarea></div>

    <button class="btn btn-rose btn-block" id="confirm-btn" type="submit" style="padding:16px;font-size:16px">Confirmer ma commande</button>
    <p class="note muted" style="text-align:center;font-size:13px;margin-top:12px">{ico('shield')} Paiement à la réception · Vos données servent uniquement à traiter votre commande.</p>
    <p id="send-err" style="display:none;color:#b3261e;font-size:14px;margin-top:14px;text-align:center">Nous n'avons pas pu enregistrer la commande. Réessayez, ou envoyez-la nous directement sur <a id="err-wa" href="#" target="_blank" rel="noopener" style="text-decoration:underline">WhatsApp</a>.</p>
   </form>
  </div>

  <aside class="infocard" style="position:sticky;top:100px">
    <h3>Récapitulatif</h3>
    <div id="sum"></div>
    <div class="note" style="border-top:1px solid var(--line);margin-top:18px;padding-top:16px;font-size:13.4px;color:var(--gray);line-height:1.7">
      {ico('wallet')} Paiement en espèces à la réception<br>
      {ico('truck')} Livraison {money(C.DELIVERY_FEE)} — offerte dès {money(C.FREE_DELIVERY_FROM)}<br>
      {ico('store')} Retrait gratuit en boutique
    </div>
    <p class="muted" style="font-size:13px;margin-top:16px">Une question avant de commander ? <a href="{wa_link("Bonjour La Rose, j'ai une question.")}" target="_blank" rel="noopener" style="color:var(--rose-ink);text-decoration:underline">Écrivez-nous</a>.</p>
  </aside>
 </div>
</div></section>
<script src="assets/checkout.js?v={V}" defer></script>"""
    page("panier.html", "Finaliser ma commande", "Validez votre commande : livraison avec paiement à la livraison partout en Tunisie, ou retrait en boutique à Nabeul.", body)


def build_static():
    hours = "".join(f'<div class="line">{ico("clock")}<div><b>{E(d)}</b><span>{E(h)}</span></div></div>' for d, h in C.HOURS)

    # --- boutique
    body = f"""
<div class="page-hero"><div class="wrap">
 <div class="crumb"><a href="index.html">Accueil</a><span>›</span>La boutique</div>
 <h1>La boutique</h1><p>{E(C.ADDRESS)}, {E(C.CITY)} — la dermocosmétique de pharmacie, le rayon bébé, les compléments et le matériel médical, avec le conseil en plus.</p></div></div>

<section><div class="wrap"><div class="split">
 <div>
  <span class="eyebrow">Notre maison</span>
  <h2>Une parapharmacie pensée comme un soin</h2>
  <p class="lead" style="margin-top:16px">La Rose est née d'une idée simple : que chacun trouve le bon produit, expliqué, sans se perdre dans les rayons. Vous y trouverez les marques prescrites en dermatologie — La Roche-Posay, Avène, Bioderma, CeraVe, SVR, Uriage, ISDIN — mais aussi tout ce qui accompagne le quotidien : bébé, hygiène, compléments, orthopédie.</p>
  <p class="lead" style="margin-top:14px">Ce site reprend le même rayonnage. Vous commandez en ligne, nous préparons, et vous payez à la réception.</p>
  <p style="margin-top:26px"><a class="btn btn-rose" href="catalogue.html">Voir le catalogue</a></p>
 </div>
 <div class="gallery">
   <img class="tall" src="images/site/store-oval.jpg" alt="Présentoir soins capillaires" loading="lazy">
   <img src="images/site/store-arches.jpg" alt="Rayon bébé" loading="lazy">
   <img src="images/site/store-shelves.jpg" alt="Rayon soins visage" loading="lazy">
 </div>
</div></div></section>

<section class="bg-cream"><div class="wrap"><div class="split rev">
 <div class="infocard">
  <h3>Nous trouver</h3>
  <div class="line">{ico('pin')}<div><b>{E(C.ADDRESS)}</b><span>{E(C.CITY)}, {E(C.COUNTRY)}</span></div></div>
  <div class="line">{ico('phone')}<div><b><a href="tel:{C.PHONE_INTL}">{E(C.PHONE)}</a></b><span>Appel ou WhatsApp</span></div></div>
  {hours}
  <div style="display:flex;gap:10px;margin-top:20px;flex-wrap:wrap">
    <a class="btn btn-ink btn-sm" href="{C.MAPS_URL}" target="_blank" rel="noopener">Itinéraire</a>
    <a class="btn btn-wa btn-sm" href="{wa_link('Bonjour La Rose !')}" target="_blank" rel="noopener">WhatsApp</a>
  </div>
 </div>
 <div class="mapwrap"><iframe src="{C.MAPS_EMBED}" loading="lazy" title="Carte — {E(C.SITE_NAME)}" referrerpolicy="no-referrer-when-downgrade"></iframe></div>
</div></div></section>

<section><div class="wrap">
 <div class="sec-head center"><span class="eyebrow">En rayon</span><h2>Ce que vous trouverez chez nous</h2></div>
 <div class="cats">{''.join(f'<a class="cat" href="categorie/{c}.html"><img src="images/site/{C.CATEGORY_META[c][2]}" alt="" loading="lazy"><div class="t"><b>{E(C.CATEGORY_META[c][0])}</b><small>{len(BY_CAT[c])} références</small></div></a>' for c in C.CATEGORY_ORDER[:8] if BY_CAT.get(c))}</div>
</div></section>"""
    page("boutique.html", "La boutique", f"La Rose Parapharmacie — {C.ADDRESS}, {C.CITY}. Horaires, itinéraire et rayons.", body, active="boutique")

    # --- commander
    body = f"""
<div class="page-hero"><div class="wrap">
 <div class="crumb"><a href="index.html">Accueil</a><span>›</span>Commander</div>
 <h1>Comment commander</h1><p>Simple et sans paiement en ligne : vous commandez, nous confirmons, vous payez à la réception.</p></div></div>

<section><div class="wrap">
 <div class="steps">
  <div class="step"><h3>1 · Composez votre panier</h3><p>Ajoutez vos produits depuis le catalogue. Vous pouvez aussi nous envoyer votre liste directement sur WhatsApp — une photo d'ordonnance ou de produit suffit.</p></div>
  <div class="step"><h3>2 · Validez vos coordonnées</h3><p>Nom, téléphone, adresse — c'est tout. Votre commande nous parvient immédiatement et nous vous contactons pour organiser la livraison.</p></div>
  <div class="step"><h3>3 · Payez à la réception</h3><p>En espèces au livreur à votre porte, ou en boutique si vous choisissez le retrait.</p></div>
 </div>
</div></section>

<section class="bg-cream"><div class="wrap-narrow">
 <div class="sec-head center"><span class="eyebrow">Questions fréquentes</span><h2>Bon à savoir</h2></div>
 <div class="faq">
  <details open><summary>Faut-il payer en ligne&nbsp;?</summary><p>Non, jamais. Aucune carte bancaire n'est demandée sur ce site. Vous réglez en espèces au moment de la livraison, ou en boutique lors du retrait.</p></details>
  <details><summary>Quels sont les délais et les frais de livraison&nbsp;?</summary><p>Nous livrons partout en Tunisie sous {C.DELIVERY_DAYS} via nos partenaires de livraison. Les frais sont de {money(C.DELIVERY_FEE)} et sont offerts à partir de {money(C.FREE_DELIVERY_FROM)} d'achat.</p></details>
  <details><summary>Puis-je récupérer ma commande en boutique&nbsp;?</summary><p>Oui, et c'est gratuit. Choisissez « retrait en boutique » au moment de valider : nous préparons votre commande et vous prévenons dès qu'elle est prête, {E(C.ADDRESS)}, {E(C.CITY)}.</p></details>
  <details><summary>Un produit affiché est-il toujours disponible&nbsp;?</summary><p>Le catalogue suit notre stock, mais il évolue vite. Les produits marqués « sur commande » sont commandés pour vous et arrivent généralement en quelques jours.</p></details>
  <details><summary>Je ne trouve pas mon produit.</summary><p>Écrivez-nous sur WhatsApp au {E(C.PHONE)} avec le nom ou une photo : si nous ne l'avons pas en rayon, nous pouvons souvent le commander pour vous.</p></details>
  <details><summary>Vendez-vous des médicaments&nbsp;?</summary><p>Non. La Rose est une parapharmacie : nous proposons des produits de soin, d'hygiène, de puériculture, des compléments alimentaires et du matériel médical, sans médicaments sur ordonnance.</p></details>
  <details><summary>Puis-je avoir un conseil avant d'acheter&nbsp;?</summary><p>Bien sûr — c'est même le cœur du métier. Décrivez-nous votre peau, votre besoin ou votre routine sur WhatsApp, et nous vous orientons vers ce qui convient, sans forcément le produit le plus cher.</p></details>
 </div>
 <div class="center" style="margin-top:40px">
   <a class="btn btn-rose" href="catalogue.html">Commencer mes achats</a>
   <a class="btn btn-wa" style="margin-left:8px" href="{wa_link('Bonjour La Rose, je souhaite commander.')}" target="_blank" rel="noopener">{WA_SVG} Commander sur WhatsApp</a>
 </div>
</div></section>"""
    page("commander.html", "Comment commander", "Commandez en ligne chez La Rose Parapharmacie : livraison avec paiement à la livraison partout en Tunisie, ou retrait en boutique à Nabeul.", body, active="commander")

    # --- livraison
    body = f"""
<div class="page-hero"><div class="wrap">
 <div class="crumb"><a href="index.html">Accueil</a><span>›</span>Livraison & retrait</div>
 <h1>Livraison & retrait</h1><p>Partout en Tunisie, avec paiement à la réception.</p></div></div>
<section><div class="wrap-narrow prose">
 <h2>Livraison à domicile</h2>
 <p>Nous expédions dans les 24 gouvernorats via nos partenaires de livraison. Le délai habituel est de {C.DELIVERY_DAYS} après confirmation de votre commande par téléphone.</p>
 <ul>
  <li>Frais de livraison : <strong>{money(C.DELIVERY_FEE)}</strong></li>
  <li>Livraison <strong>offerte</strong> à partir de {money(C.FREE_DELIVERY_FROM)} d'achat</li>
  <li>Paiement <strong>en espèces au livreur</strong>, à la réception du colis</li>
 </ul>
 <h2>Retrait en boutique</h2>
 <p>Gratuit. Choisissez « retrait en boutique » au moment de valider votre commande : nous la préparons et vous prévenons dès qu'elle est prête. Vous réglez sur place, {E(C.ADDRESS)}, {E(C.CITY)}.</p>
 <h2>Suivi de commande</h2>
 <p>Dès réception de votre commande, nous vous contactons par téléphone ou WhatsApp pour convenir de la livraison ou du retrait. Vous ne payez qu'à la réception.</p>
 <h2>Échange et retour</h2>
 <p>Pour des raisons d'hygiène, les produits ouverts ou descellés ne sont ni repris ni échangés. Si un article arrive abîmé ou ne correspond pas à votre commande, prévenez-nous dans les 48 h au {E(C.PHONE)} : nous le remplaçons.</p>
 <p class="muted" style="font-size:13.5px;margin-top:30px">Les tarifs et délais indiqués sont ceux en vigueur ; ils peuvent varier selon la destination et la période.</p>
</div></section>"""
    page("livraison.html", "Livraison & retrait", "Livraison partout en Tunisie sous 24-72 h, paiement à la livraison, retrait gratuit en boutique à Nabeul.", body)

    # --- contact
    body = f"""
<div class="page-hero"><div class="wrap">
 <div class="crumb"><a href="index.html">Accueil</a><span>›</span>Contact</div>
 <h1>Nous écrire</h1><p>Une question sur un produit, une routine, une commande&nbsp;? Le plus simple est WhatsApp — nous répondons dans la journée.</p></div></div>
<section><div class="wrap"><div class="split">
 <div>
  <div class="infocard">
   <h3>Coordonnées</h3>
   <div class="line">{ico('phone')}<div><b><a href="tel:{C.PHONE_INTL}">{E(C.PHONE)}</a></b><span>Téléphone & WhatsApp</span></div></div>
   <div class="line">{ico('pin')}<div><b>{E(C.ADDRESS)}</b><span>{E(C.CITY)}, {E(C.COUNTRY)}</span></div></div>
   {hours}
  </div>
  <div style="display:flex;gap:10px;margin-top:20px;flex-wrap:wrap">
   <a class="btn btn-wa" href="{wa_link('Bonjour La Rose !')}" target="_blank" rel="noopener">{WA_SVG} WhatsApp</a>
   <a class="btn btn-line" href="{C.INSTAGRAM}" target="_blank" rel="noopener">Instagram</a>
   <a class="btn btn-line" href="{C.FACEBOOK}" target="_blank" rel="noopener">Facebook</a>
  </div>
 </div>
 <div class="mapwrap" style="height:440px"><iframe src="{C.MAPS_EMBED}" loading="lazy" title="Carte"></iframe></div>
</div></div></section>"""
    page("contact.html", "Contact", f"Contacter La Rose Parapharmacie à {C.CITY} : téléphone, WhatsApp, adresse et horaires.", body, active="contact")

    # --- 404
    body = f"""<section style="padding:110px 0"><div class="wrap center">
 <span class="eyebrow">Erreur 404</span>
 <h1>Cette page a changé de rayon</h1>
 <p class="lead" style="margin:16px auto 30px">La page que vous cherchez n'existe pas ou a été déplacée.</p>
 <a class="btn btn-rose" href="index.html">Retour à l'accueil</a>
 <a class="btn btn-line" style="margin-left:8px" href="catalogue.html">Voir le catalogue</a>
</div></section>"""
    page("404.html", "Page introuvable", "Page introuvable.", body)


def build_loyalty():
    rewards = [
        ("🌱", "Bouton", "Votre carte est créée dès votre première commande — avec un cadeau de bienvenue glissé dans le colis."),
        ("✿", "250 pétales", f"Un bon de {money(C.LOYALTY_BON)} à utiliser sur la commande suivante, en ligne ou en boutique."),
        ("🎂", "Anniversaire", "Le mois de votre anniversaire, une surprise vous attend dans votre commande ou en boutique."),
        ("💌", "Parrainage", "Votre amie commande avec votre code ROSE-xxxx : elle gagne 50 pétales, vous aussi."),
    ]
    rw = "".join(f'<div class="rw"><div class="ic">{i}</div><b>{E(t)}</b><small>{E(d)}</small></div>' for i, t, d in rewards)
    body = f"""
<div class="page-hero"><div class="wrap">
 <div class="crumb"><a href="index.html">Accueil</a><span>›</span>Carte Rose</div>
 <h1>La Carte Rose</h1>
 <p>Notre programme de fidélité, aussi simple qu'une rose qui s'ouvre : <strong>1 dinar dépensé = 1 pétale</strong>. À 250 pétales, votre rose est épanouie et vous offre un bon de {money(C.LOYALTY_BON)}.</p></div></div>

<section><div class="wrap">
 <div class="rosecard">
  <div class="bloom" id="page-rose"></div>
  <div>
   <span class="stage" data-rose-stage>Bouton de rose</span>
   <h3>Bonjour <span data-rose-name>et bienvenue</span> ✿</h3>
   <div class="big"><span data-rose-petals>0</span><small>pétales</small></div>
   <div class="pbar"><i data-rose-bar style="width:0%"></i></div>
   <div class="next">Encore <b data-rose-next>250</b> pétales avant votre prochain bon de {money(C.LOYALTY_BON)} · <b data-rose-bons>0</b> bon(s) disponible(s) · <b data-rose-orders>0</b> commande(s)</div>
   <div class="code">Mon code parrainage : <span data-rose-code>—</span> <button type="button" id="copycode">copier</button></div>
   <p class="muted" style="font-size:12.5px;margin-top:12px">Votre carte se remplit automatiquement à chaque commande passée depuis cet appareil. Le solde de référence est celui de la parapharmacie — il vous suffit de donner votre numéro de téléphone en boutique.</p>
  </div>
 </div>
</div></section>

<section class="bg-cream"><div class="wrap">
 <div class="sec-head center"><span class="eyebrow">Ce que votre rose vous offre</span><h2>Quatre bonnes raisons de revenir</h2></div>
 <div class="rewards">{rw}</div>
</div></section>

<section><div class="wrap-narrow">
 <div class="sec-head center"><span class="eyebrow">Comment ça marche</span><h2>Simple comme une rose</h2></div>
 <div class="faq">
  <details open><summary>Comment gagner des pétales ?</summary><p>Chaque commande passée sur le site ou en boutique rapporte 1 pétale par dinar (livraison exclue). Donnez simplement votre numéro de téléphone : c'est votre identifiant Carte Rose.</p></details>
  <details><summary>Comment utiliser mon bon de {money(C.LOYALTY_BON)} ?</summary><p>Dès 250 pétales, cochez « Utiliser mes pétales » au moment de commander, ou dites-le en boutique. Le bon est déduit du total, et votre rose repart pour un nouveau cycle.</p></details>
  <details><summary>Et le parrainage ?</summary><p>Votre code est ROSE suivi des 4 derniers chiffres de votre téléphone. Une amie l'indique à sa première commande : elle reçoit 50 pétales de bienvenue, et vous aussi.</p></details>
  <details><summary>J'ai changé de téléphone, mes pétales sont perdus ?</summary><p>Non : votre solde est conservé à la parapharmacie sous votre numéro. Écrivez-nous sur WhatsApp et nous vous le communiquons.</p></details>
 </div>
 <div class="center" style="margin-top:36px"><a class="btn btn-rose" href="catalogue.html">Faire éclore ma rose</a></div>
</div></section>
<script>
document.addEventListener('DOMContentLoaded',function(){{
  document.getElementById('page-rose').innerHTML=window.LRroseSVG('pr');document.getElementById('pr').setAttribute('data-rose','');
  window.LRloyalRepaint();
  document.getElementById('copycode').addEventListener('click',function(){{
    var c=window.LRloyal.code(window.LRloyal.get().tel); if(!c){{alert('Votre code apparaît après votre première commande.');return;}}
    if(navigator.clipboard)navigator.clipboard.writeText(c);this.textContent='copié ✓';
  }});
}});
</script>"""
    page("carte-rose.html", "Carte Rose — fidélité", f"Programme de fidélité La Rose Parapharmacie : 1 dinar = 1 pétale, un bon de {money(C.LOYALTY_BON)} tous les 250 pétales, cadeau de bienvenue, anniversaire et parrainage.", body, active="rose")


def build_data():
    os.makedirs(os.path.join(DOCS, "data"), exist_ok=True)
    idx = []
    for p in PRODUCTS:
        s = f"{p['name']} {p['brand']} {p['sub']} {p['cat_name']}"
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()
        idx.append({"id": p["id"], "n": p["name"], "b": p["brand"], "p": p["price"], "i": p["image"],
                    "u": p["url"], "c": p["category"], "sb": p["sub"], "k": 1 if p["instock"] else 0,
                    "s": re.sub(r"\s+", " ", s)})
    json.dump(idx, open(os.path.join(DOCS, "data", "search.json"), "w"), ensure_ascii=False, separators=(",", ":"))

    urls = ["index.html", "catalogue.html", "marques.html", "boutique.html", "commander.html", "carte-rose.html",
            "livraison.html", "contact.html", "panier.html"]
    urls += [f"categorie/{c}.html" for c in C.CATEGORY_ORDER if BY_CAT.get(c)]
    urls += [f"marque/{slugify(b)}.html" for b in BRANDS]
    urls += [p["url"] for p in PRODUCTS]
    base = "https://larosepara.tn/"
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"<url><loc>{base}{u}</loc></url>" for u in urls]
    sm.append("</urlset>")
    open(os.path.join(DOCS, "sitemap.xml"), "w").write("\n".join(sm))
    open(os.path.join(DOCS, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n")


def copy_assets():
    os.makedirs(os.path.join(DOCS, "assets"), exist_ok=True)
    for f in ("style.css", "site.js"):
        shutil.copy2(os.path.join(HERE, "assets-src", f), os.path.join(DOCS, "assets", f))
    cfg = json.dumps({"fee": C.DELIVERY_FEE, "free": C.FREE_DELIVERY_FROM, "wa": C.WHATSAPP, "mail": C.EMAIL,
                      "cc": C.EMAIL_CC, "days": C.DELIVERY_DAYS, "city": C.CITY, "addr": C.ADDRESS}, ensure_ascii=False)
    js = open(os.path.join(HERE, "assets-src", "checkout.js"), encoding="utf-8").read().replace("__CFG__", cfg)
    open(os.path.join(DOCS, "assets", "checkout.js"), "w", encoding="utf-8").write(js)
    for sub in ("site", "products"):
        src = os.path.join(HERE, "images", sub)
        dst = os.path.join(DOCS, "images", sub)
        if not os.path.isdir(src):
            continue
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(src):
            s, d = os.path.join(src, f), os.path.join(dst, f)
            if not os.path.exists(d) or os.path.getmtime(s) > os.path.getmtime(d):
                shutil.copy2(s, d)


def main():
    if os.path.isdir(DOCS):
        for f in os.listdir(DOCS):
            p = os.path.join(DOCS, f)
            if f in ("images", "CNAME"):
                continue
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    os.makedirs(DOCS, exist_ok=True)
    copy_assets()
    build_home()
    build_catalogue()
    build_categories()
    build_brands()
    build_cart()
    build_static()
    build_loyalty()
    build_data()
    if not FAST:
        build_products()
    n = sum(len(fs) for _, _, fs in os.walk(DOCS))
    print(f"✓ docs/ — {len(PRODUCTS)} produits, {len(BRAND_LIST)} marques, {n} fichiers")


if __name__ == "__main__":
    main()
