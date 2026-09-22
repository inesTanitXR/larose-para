#!/usr/bin/env python3
"""Curate the La Rose catalog from the raw reference data in ref/catalog-raw/.

Selection is driven by what was actually seen on the shelves (photos of 2026-09-21):
per-brand include patterns + caps.  Output: data/products.json + images/products/*.jpg

Re-run after editing the rules below.  Prices are the reference site's regular price
(TND) and are indicative until the shop confirms them.
"""
import glob
import hashlib
import io
import json
import os
import re
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "ref", "catalog-raw")
IMG_DIR = os.path.join(HERE, "images", "products")
OUT = os.path.join(HERE, "data", "products.json")
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"

# ---- La Rose taxonomy -------------------------------------------------------------
CATEGORIES = {
    "visage": ("Visage", ["Nettoyants & démaquillants", "Hydratation", "Anti-âge", "Anti-imperfections",
                          "Anti-taches & éclat", "Sérums", "Yeux & lèvres", "Peaux sensibles", "Masques & gommages"]),
    "solaire": ("Solaire", ["Visage", "Corps", "Enfants", "Après-soleil"]),
    "cheveux": ("Cheveux", ["Shampooings", "Soins & masques", "Anti-chute", "Antipelliculaire",
                            "Cheveux bouclés", "Anti-poux", "Coloration"]),
    "corps": ("Corps & hygiène", ["Douche & bain", "Hydratation corps", "Déodorants", "Hygiène intime",
                                  "Mains & pieds", "Épilation & rasage"]),
    "bebe": ("Bébé & maman", ["Toilette & soins bébé", "Change & couches", "Biberons & tétines",
                              "Allaitement & tire-lait", "Éveil & accessoires", "Alimentation & santé bébé", "Maman"]),
    "complements": ("Compléments alimentaires", ["Vitamines & minéraux", "Cheveux & ongles", "Minceur",
                                                  "Stress & sommeil", "Immunité & énergie", "Enfants"]),
    "bucco": ("Bucco-dentaire", ["Dentifrices", "Brosses à dents", "Bains de bouche", "Interdentaire & prothèses"]),
    "medical": ("Matériel médical & orthopédie", ["Tensiomètres & mesure", "Glycémie", "Thermomètres",
                                                   "Orthèses & supports", "Sandales orthopédiques", "Premiers soins", "Confort & bien-être"]),
    "beaute": ("Beauté & accessoires", ["Manucure & pédicure", "Appareils beauté", "Bijoux hypoallergéniques",
                                        "Coffrets & cadeaux", "Maquillage & lèvres"]),
    "autres": ("Autres produits", ["Maison & divers"]),
}

# ---- what is on the shelves: brand -> (display name, include regex, cap) ----------
# Patterns are matched (case-insensitive, accents stripped) against the product name.
SEEN = {
    "cerave": ("CeraVe", r"moussant|hydratant|hydrating|lotion|creme|serum|retinol|vitamine c|peptide|huile lavante|blemish|sa |pieds|baume|smoothing", 26),
    "la-roche-posay": ("La Roche-Posay", r"effaclar|toleriane|lipikar|cicaplast|hyalu|mela ?b3|anthelios|retinol|eau micellaire|gel moussant|vitamine c|pure niacinamide|hydraphase|kerium|substiane|redermic|serozinc|nutritic", 44),
    "bioderma": ("Bioderma", r"sensibio|hydrabio|sebium|photoderm|atoderm|pigmentbio|cicabio|abcderm|node|crealine", 44),
    "avene": ("Avène", r"cleanance|hydrance|cicalfate|tolerance|hyaluron|fluide|solaire|spf|eau thermale|xeracalm|physiolift|a-oxitive|cold cream|antirougeurs|couvrance|trixera|sunsi|b-protect|mineral|apres-soleil", 44),
    "uriage": ("Uriage", r"bariesun|hyseac|eau thermale|depiderm|toledem|toleder|xemose|bebe|1ere|gyn|age lift|isolift|ds |keratosane|roseliane|eau micellaire|creme lavante|pruriced|cica|xemose|deo", 40),
    "svr": ("SVR", r"sebiaclear|topialyse|sensifine|cicavit|xerial|palpebral|ampoule|\[|physiopure|sun secure|spirial|densitium|clairial|hydraliane|rubialine|b3|c20|hyalu|niacinamide|azelaic|glyco|salicylic|retinol|lavante|eau micellaire", 46),
    "eucerin": ("Eucerin", r"hyaluron|anti-pigment|dermopure|sun|urea|ph5|atopi|dermatoclean|aquaphor|even|hyal", 30),
    "vichy": ("Vichy", r"dercos|mineral 89|normaderm|capital soleil|liftactiv|deo|purete thermale|neovadiol|aqualia", 32),
    "ducray": ("Ducray", r"anaphase|neoptide|keracnyl|melascreen|kelual|squanorm|elution|sabal|densiage|creastim|dexyane|ictyane|argeal|kertyol", 24),
    "a-derma": ("A-Derma", r"exomega|biology|epitheliale|dermalibour|phys-ac|protect|primalba|cutalgan|rheacalm", 14),
    "acm": ("ACM", r"novophane|depiwhite|sebionex|vitix|duolys|noviderm", 20),
    "isdin": ("ISDIN", r"fotoprotector|isdinceutics|acniben|fotoultra|flavo|hyaluronic|retinal|melatonik|ureadin|eryfotona|pediatrics|k-ox|vital", 30),
    "noreva": ("Noreva", r"iklen|exfoliac|bergasol|sebodiane|sensidiane|trio white|xerodiane|hexaphane|psoriane|aquareva", 20),
    "novexpert": ("Novexpert", r"", 22),
    "lierac": ("Lierac", r"", 16),
    "filorga": ("Filorga", r"time-filler|hydra|ncef|uv|skin|lift|oxygen|global|sleep|meso|coffret|age-purify|optim|nutri", 24),
    "sensilis": ("Sensilis", r"", 20),
    "babe": ("Babé", r"", 20),
    "dermaceutic": ("Dermaceutic", r"", 14),
    "gamarde-soins-bio-dermatologiques": ("Gamarde", r"", 12),
    "nuxe": ("Nuxe", r"prodigieu|huile|sun|reve de miel|creme fraiche|nuxuriance|merveillance|bio|baume", 34),
    "phyto": ("Phyto", r"phytocyane|phytokeratine|phytojoba|phytodetox|phytoapaisant|phytosquam|phytocolor|phytospecific|phyto ?boucle|douceur|reparation|nutrition|volume|phytoprogenium|phytolium|densifiant|phytodefrisant|subtil", 30),
    "luxeol": ("Luxéol", r"", 16),
    "bioxsine": ("Bioxsine", r"", 12),
    "byphasse": ("Byphasse", r"gel douche|lait|gommage|creme|deodorant|micellaire|shampooing|masque|huile|baume|sugar|hydratant|bain", 28),
    "roge-cavailles": ("Rogé Cavaillès", r"", 26),
    "cetaphil": ("Cetaphil", r"", 12),
    "daylong": ("Daylong", r"", 10),
    "ultrasun": ("Ultrasun", r"", 12),
    "gum": ("GUM", r"", 40),
    "elgydium": ("Elgydium", r"", 18),
    "klorex": ("Klorex", r"", 6),
    "parodontax": ("Parodontax", r"", 6),
    "kin": ("KIN", r"", 14),
    "fixodent": ("Fixodent", r"", 2),
    "protefix": ("Protefix", r"", 2),
    "doppelherz": ("Doppelherz", r"", 40),
    "gummybear": ("Gummybear", r"", 6),
    "mustela": ("Mustela", r"", 30),
    "chicco": ("Chicco", r"", 40),
    "nuk": ("NUK", r"", 40),
    "bibs": ("BIBS", r"", 16),
    "wee": ("Wee Baby", r"", 14),
    "avent": ("Philips Avent", r"", 7),
    "alphanova": ("Alphanova", r"", 20),
    "lilas": ("Lilas", r"", 18),
    "beurer": ("Beurer", r"tensiometre|thermometre|pese|balance|brosse|epilateur|oxymetre|coussin|masseur|inhalateur|lampe|humidificateur|glycemie|pedicure|manucure|chauffant|nettoyage|purificateur|lumiere|miroir|tire-lait|babyphone|thermo", 36),
    "orthomed": ("Orthomed", r"", 21),
    "orthofix": ("Orthofix", r"", 2),
    "titania": ("Titania", r"", 40),
    "curall": ("CurALL", r"", 26),
    "naturtint": ("Naturtint", r"", 24),
    "pharmaceris": ("Pharmaceris", r"", 20),
    "hyfac": ("Hyfac", r"", 14),
    "roncey": ("Roncey", r"", 24),
    "cytolnat": ("Cytolnat", r"", 20),
    "esthelle": ("Esth'elle", r"calino|creme|lait|savon|shampooing|liniment|eau|huile|gel|baume|serum|solaire|spf|derm|clary|dermixa|riva", 24),
    "muriac": ("Muriac", r"", 12),
    "dermacare": ("Dermacare", r"", 22),
    "novaclear": ("Novaclear", r"", 16),
    "alania": ("Alania", r"", 22),
    "eye-care": ("Eye Care Cosmetics", r"mascara|crayon|rosy|baume|levres|demaquillant|eye|yeux|fond de teint|correcteur|vernis", 14),
    "beesline": ("Beesline", r"", 24),
    "ecrinal": ("Ecrinal", r"", 14),
    "killpoux": ("Killpoux", r"", 4),
    "quies": ("Quies", r"", 4),
    "durex": ("Durex", r"", 8),
    "phyteal": ("Phytéal", r"", 30),
    "dermedic": ("Dermedic", r"", 18),
    "pure-skin": ("Pure Skin", r"", 8),
    "rivaderm": ("Rivaderm", r"", 16),
    "physiomer": ("Physiomer", r"", 8),
    "tommee-tippee": ("Tommee Tippee", r"", 12),
    "medel": ("Medel", r"", 4),
    "rossmax": ("Rossmax", r"", 12),
    "accu-chek": ("Accu-Chek", r"", 8),
    "westinghouse": ("Westinghouse", r"", 3),
    "techwood": ("Techwood", r"", 2),
    "veet": ("Veet", r"", 2),
    "pulmoll": ("Pulmoll", r"", 6),
    "maximum": ("Maximum", r"", 4),
    "materna": ("Materna", r"", 16),
    "nimo": ("Nimo", r"", 5),
    "innovaderm": ("Innovaderm", r"", 14),
    "martiderm": ("Martiderm", r"", 8),
    "sesderma": ("Sesderma", r"", 10),
    "rilastil": ("Rilastil", r"", 10),
    "medela": ("Medela", r"", 6),
    "mixa": ("Mixa", r"", 1),
}

EXCLUDE = r"homme|for men|men |rasage|apres-rasage|parfum|eau de toilette|autobronzant|maquillage|fond de teint|mascara|rouge a levres|eye ?liner|vernis|nail polish"
EXCLUDE_KEEP_BRANDS = {"eye-care", "titania", "roge-cavailles", "vichy", "byphasse"}  # brands whose men/makeup lines were seen


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def slugify(s):
    s = strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80]


def norm(s):
    return strip_accents(s).lower()


# ---- category mapping ---------------------------------------------------------------
def classify(p, brand_slug):
    n = norm(p["name"])
    cats = set(p["cats"])
    C = lambda *ks: any(k in cats for k in ks)

    # name-only rules (mostly for POS lines that matched nothing)
    if re.search(r"boucle|bracelet|gourmette|collier|bague|chaine|pendentif|bijou|piercing|jonc|creole", n) and not re.search(r"cheveux|curl|boucles? (de )?cheveux|shampo|soin", n): return "beaute", "Bijoux hypoallergéniques"
    if re.search(r"claquette|sandale|mule|chausson|semelle|ortho-claq|sti light|tong", n): return "medical", "Sandales orthopédiques"
    if re.search(r"tisane|infusion|the vert|the minceur", n):
        return ("complements", "Minceur") if re.search(r"minceur|slim|detox", n) else ("complements", "Vitamines & minéraux")
    if re.search(r"gelule|gellule|comprime|capsule|sirop|ampoule buv|sachet|b/\d+|bt/?\d+|bt\d+|b\d+ |magnes|omega|vitamin|vit b|vit c|vit d|zinc|fer |ferro|collagen|kollagen|probio|spirulin|levure|ginseng|melaton|calcium|selenium|iode|folate|acide folique|glutath|carnitin|biotin|tyrosine", n) and not re.search(r"creme|serum|gel |shampo|masque|lotion|ecran|spf|deo|savon|dentifrice|brosse|huile", n):
        if re.search(r"cheveux|ongle|capil|hair|kollagen|collagen|beauty", n): return "complements", "Cheveux & ongles"
        if re.search(r"minceur|brule|slim|drain|carnitin|ventre", n): return "complements", "Minceur"
        if re.search(r"stress|sommeil|sleep|melaton|relax|nuit|calm", n): return "complements", "Stress & sommeil"
        if re.search(r"kids|enfant|junior|pediakid|bebe", n): return "complements", "Enfants"
        if re.search(r"immun|energ|vital|fatigue|fer |ferro|omega|ginseng|tonic|multivit|a-z|q10", n): return "complements", "Immunité & énergie"
        return "complements", "Vitamines & minéraux"
    if re.search(r"compresse|gant|seringue|aiguille|bandage|bande |sparadrap|pansement|coton hydrophile|alcool|betadine|serum physio|lancette|bandelette|thermometre|masque chirurg|steril", n):
        if re.search(r"lancette|bandelette|glyc", n): return "medical", "Glycémie"
        if "thermometre" in n: return "medical", "Thermomètres"
        return "medical", "Premiers soins"
    if re.search(r"fauteuil|deambulateur|canne|bequille|coussin|urinal|bassin|chaise|rehausse|matelas anti|escarre|bas de contention|collant contention|ceinture|corset|attelle|genouillere|chevillere|coudiere|epaule|immobilisation|poignet|lombaire|cervical|minerve|orthese|releveur|pouce|talonnette|hallux", n):
        if re.search(r"ceinture|corset|attelle|genouillere|chevillere|coudiere|epaule|immobilisation|poignet|lombaire|cervical|minerve|orthese|releveur|pouce|talonnette|hallux|contention", n): return "medical", "Orthèses & supports"
        return "medical", "Confort & bien-être"
    if re.search(r"tensiometre|oxymetre|pese|balance|glucometre|aerosol|inhalateur|nebulis|stethoscope|bouillotte", n):
        if re.search(r"tensio|oxym|pese|balance|stethoscope", n): return "medical", "Tensiomètres & mesure"
        if "glucom" in n: return "medical", "Glycémie"
        return "medical", "Confort & bien-être"
    if re.search(r"tapis d ?eveil|jouet|hochet|peluche|trotteur|walker|gym|piano|doudou|veilleuse|mobile musical|anneau de dentition|dentition|pot bebe|baignoire|transat|sac a langer|sac maternite|vanity|thermos bebe|toile ciree|matelas a langer|bavoir|body |pyjama|chaussette bebe|coffret naissance", n): return "bebe", "Éveil & accessoires"
    if re.search(r"biberon|tetine|sucette|goupillon|tasse|gourde|cuillere|assiette|bol bebe|doseur|sac de stockage|sac de conservation|grignoteur|attache sucette|chaine de sucette|pacifier|bottle|cup", n): return "bebe", "Biberons & tétines"
    if re.search(r"couche|lingette|coton bebe|liniment|creme de change|change |erytheme|carre coton|maxi carre", n) and not re.search(r"adult|pants", n): return "bebe", "Change & couches"
    if re.search(r"tire-lait|tire lait|coussinet|allaitement|mamelon|bout de sein|lait maternel|chauffe-biberon|chauffe biberon|sterilis|chauffe lingette", n): return "bebe", "Allaitement & tire-lait"
    if re.search(r"compote|farine|cereale|lait infantile|lait de croissance|petit pot|biscuit bebe|lait 1er age|lait 2eme age", n): return "bebe", "Alimentation & santé bébé"
    if re.search(r"desodorisant|desinfectant|parfum d ambiance|linge|assouplissant|lessive|vaisselle|brume parfumee|bougie|diffuseur|spray textile", n): return "autres", "Maison & divers"
    if re.search(r"preservatif|lubrifiant|intime|gyn", n): return "corps", "Hygiène intime"
    if re.search(r"dentifrice|brosse a dent|brosse dent|bain de bouche|fil dentaire|brossette|interdent|blanchiment dent|prothese dent|adhesif|fixodent|protefix|orthodont", n):
        if "dentifrice" in n: return "bucco", "Dentifrices"
        if re.search(r"brossette|fil dentaire|interdent|prothese|fixodent|protefix", n): return "bucco", "Interdentaire & prothèses"
        if "brosse" in n: return "bucco", "Brosses à dents"
        if "bouche" in n: return "bucco", "Bains de bouche"
        return "bucco", "Interdentaire & prothèses"
    if re.search(r"pastille|gorge|toux|sirop|nez|nasal|oreille|bouchon", n): return "medical", "Confort & bien-être"
    if re.search(r"pince|coupe.ongle|lime|ciseaux|rasoir|rape|pierre ponce|peigne|brosse a cheveux|brosse cheveux|barrette|elastique|chouchou|bandeau|bigoudi|pinceau|eponge|houppette|miroir|epingle|coupe-ongle", n) and not re.search(r"a dent", n): return "beaute", "Manucure & pédicure"
    if re.search(r"epilateur|tondeuse|lisseur|seche.cheveux|brosse visage|brosse nettoyante|hydropulseur|pedi|callus", n): return "beaute", "Appareils beauté"
    if re.search(r"coffret|trousse|vanity|pack|kit|routine", n) and not re.search(r"ombilical|premiers soins|reparation", n): return "beaute", "Coffrets & cadeaux"
    if re.search(r"poux|lente", n): return "cheveux", "Anti-poux"
    if re.search(r"mascara|crayon|eye ?liner|fond de teint|fdt|rouge a levres|gloss|blush|vernis|poudre|highlight|bb cream|cc cream|correcteur|anticerne", n): return "beaute", "Maquillage & lèvres"
    if re.search(r"colorat|couleur|teinture|henne", n) and re.search(r"cheveux|colorat|teinture|henne|naturtint", n): return "cheveux", "Coloration"
    if re.search(r"shampo|shamp|shp\b|apres.shamp|masque capil|masque cheveux|conditioner|conditionner|demelant|serum capil|lotion capil|huile capil|spray capil|cheveux|hair|curl|boucle|keratin|kerat|lissant|lissage|coiffant|mousse coiff|gel coiff|cire coiff|laque", n) and not re.search(r"corps et cheveux|cheveux et corps|visage|epilat|tondeuse|brosse", n):
        if re.search(r"curl|boucle|frise|crepu", n): return "cheveux", "Cheveux bouclés"
        if re.search(r"chute|densi|croissance|fortif|capilvit|cystiphane|bioxcin|luxeol|pousse|anti-chute", n) and not re.search(r"pellic", n): return "cheveux", "Anti-chute"
        if re.search(r"pellic|squam|dandruff|kelual|elution|kertyol|pso", n): return "cheveux", "Antipelliculaire"
        if re.search(r"shamp|shp", n): return "cheveux", "Shampooings"
        return "cheveux", "Soins & masques"
    if re.search(r"deo |deod|anti.transp|roll.on|roll_on", n): return "corps", "Déodorants"
    if re.search(r"gel douche|savon|douche|bain|lavant corps|huile lavante|creme lavante|syndet|pain dermato|gel lavant", n) and not re.search(r"visage|bebe|dent", n): return "corps", "Douche & bain"
    if re.search(r"creme main|creme pied|mains|pieds|hand|foot|talon|crevasse|ongle|cor |cors |durillon", n) and not re.search(r"visage|brosse", n): return "corps", "Mains & pieds"
    if re.search(r"lait corps|creme corps|baume corps|body|corps|vergeture|huile seche|huile prodigieuse|huile de massage|beurre de karite|karite|huile d amande|huile vegetale|huile essentielle|huile de coco|huile d argan|eau florale|hydrolat|eau d ortie|eau de rose", n) and not re.search(r"visage|solaire|spf", n): return "corps", "Hydratation corps"
    if re.search(r"epilat|depilat|cire|bande de cire|rasoir|apres.rasage|mousse a raser", n): return "corps", "Épilation & rasage"
    if re.search(r"spf|solaire|ecran|sun|bronz|apres.soleil|after sun|uv ", n):
        if re.search(r"apres.soleil|after sun", n): return "solaire", "Après-soleil"
        if re.search(r"enfant|kids|pediatric|bebe|baby|junior|family", n): return "solaire", "Enfants"
        if re.search(r"lait|spray|corps|body|brume|huile|lotion|stick", n) and not re.search(r"visage|face", n): return "solaire", "Corps"
        return "solaire", "Visage"
    # targeted fixes seen in review
    if re.search(r"rape electrique|pedi|callus|epilateur|brosse visage|brosse nettoyante|pore|face brush", n) and brand_slug in {"westinghouse", "techwood", "beurer"}: return "beaute", "Appareils beauté"
    if brand_slug == "pulmoll" or re.search(r"pastille|gorge", n): return "medical", "Confort & bien-être"
    if brand_slug == "materna" and re.search(r"farine|cereal|biscuit|lait |infantile|puree|compote|tisane", n): return "bebe", "Alimentation & santé bébé"
    if re.search(r"tire-lait|tire lait", n): return "bebe", "Allaitement & tire-lait"
    if re.search(r"creme mains|creme main|hand cream|mains ", n) and not re.search(r"visage", n): return "corps", "Mains & pieds"
    if brand_slug == "luxeol" and re.search(r"pousse|croissance|gelule|bt/|comprim|capsule", n): return "complements", "Cheveux & ongles"
    if brand_slug == "lilas" and re.search(r"adulte|pants|incontinence", n): return "medical", "Confort & bien-être"
    if re.search(r"relipidant|baume corps|lait corps|creme corps", n): return "corps", "Hydratation corps"
    if brand_slug == "curall" and re.search(r"gel|arnica|spray|desinfect", n): return "medical", "Premiers soins"

    # brand-level shortcuts
    if brand_slug in {"gum", "elgydium", "klorex", "parodontax", "kin", "fixodent", "protefix"} or C("soins-buccodentaires", "dentifrice", "brosse-a-dent", "bain-de-bouche", "brossette-interdentaire", "brosse-a-dent-electrique"):
        if C("brosse-a-dent", "brosse-a-dent-electrique") or re.search(r"brosse", n): return "bucco", "Brosses à dents"
        if C("bain-de-bouche") or re.search(r"bain de bouche", n): return "bucco", "Bains de bouche"
        if C("brossette-interdentaire") or re.search(r"brossette|fil dentaire|prothese|fixodent|protefix|adhesif", n): return "bucco", "Interdentaire & prothèses"
        return "bucco", "Dentifrices"
    if brand_slug in {"doppelherz", "gummybear"} or C("complements-alimentaires", "complements-cheveux-et-ongles", "immunite", "anti-fatigue", "forme-et-vitalite", "articulations", "trouble-de-sommeil", "magnesium", "omega-3", "zinc", "fertilite", "detox-et-draineurs", "transit-et-digestion", "cholesterol-et-cardiovasculaire", "concentration-et-memoire", "yeux-et-vision", "anti-oxydant", "complements-alimentaires-bebe-et-enfant"):
        if re.search(r"capilvit|cheveux|ongles|hair|kollagen|collagen|biotine", n): return "complements", "Cheveux & ongles"
        if re.search(r"minceur|brule|slim|draineur|ventre|figura", n): return "complements", "Minceur"
        if re.search(r"stress|sommeil|sleep|melaton|relax|nerv", n): return "complements", "Stress & sommeil"
        if re.search(r"kids|enfant|junior|kinder|bebe", n): return "complements", "Enfants"
        if re.search(r"immun|energ|vitalit|fatigue|fer |ferro|omega|q10|ginseng|a-z|multivit|tonic", n): return "complements", "Immunité & énergie"
        return "complements", "Vitamines & minéraux"
    if brand_slug in {"beurer", "orthomed", "orthofix", "curall", "rossmax", "accu-chek", "medel", "quies", "physiomer"} or C("materiel-medical", "appareils-de-mesure", "tensiometres", "thermometre", "glucometre", "bandelettes-glycemie", "oxymetre", "attelle-de-poignet", "genouillere", "compresse-et-sparadrap", "accessoire-medicale", "appareils-daerosol", "pese-personne", "appareils-de-massage", "hallux-valgus", "nez-et-oreilles", "aide-auditive"):
        if re.search(r"epilateur|brosse|pedicure|manucure|nettoyage visage|miroir|lumiere|face|beaute|beauty|seche-cheveux|lisseur", n): return "beaute", "Appareils beauté"
        if re.search(r"tire-lait|babyphone|chauffe|sterilis", n): return "bebe", "Allaitement & tire-lait"
        if re.search(r"glyc|glucom|bandelette|lancette|accu-chek|on call|gm550", n): return "medical", "Glycémie"
        if re.search(r"tensio|pression|blood", n): return "medical", "Tensiomètres & mesure"
        if re.search(r"thermo|fievre", n): return "medical", "Thermomètres"
        if re.search(r"attelle|genou|cheville|poignet|ceinture|lombaire|epaule|coude|orthese|chevillere|genouillere|support|corset|bas de contention|semelle|hallux|coussin|orthopedi", n): return "medical", "Orthèses & supports"
        if re.search(r"pansement|compresse|sparadrap|bandage|ampoule|cors|durillon|patch|gel pack|glace|bande", n): return "medical", "Premiers soins"
        if re.search(r"pese|balance|oxym", n): return "medical", "Tensiomètres & mesure"
        return "medical", "Confort & bien-être"
    if brand_slug == "titania":
        return "beaute", "Manucure & pédicure"
    if brand_slug in {"mustela", "chicco", "nuk", "bibs", "wee", "avent", "alphanova", "lilas", "tommee-tippee", "materna", "nimo", "medela"} or C("puericulture", "bebe-et-maman", "toilette-soins-bebe", "biberon", "sucette", "tetine", "gel-lavant-et-nettoyant-bebe", "change-de-bebe", "shampoing-bebe", "lingette-bebe", "couches-bebe", "anneaux-de-dentition", "tire-lait", "chauffe-biberon", "sterilisateurs", "trousseaux-et-cadeaux-bebe", "creme-de-change", "liniment", "maman", "soins-specifiques-bebe-et-enfant"):
        if brand_slug == "lilas" and re.search(r"serviette|nuit|jour|protege|hygien|adult|pants|maternite", n): return "corps", "Hygiène intime"
        if re.search(r"vergetures|grossesse|maman|nursing", n): return "bebe", "Maman"
        if re.search(r"tire-lait|allaitement|coussinet|mamelon|lait maternel|coquille|creme mamelon", n): return "bebe", "Allaitement & tire-lait"
        if re.search(r"biberon|tetine|sucette|tasse|gourde|goupillon|cuillere|assiette|bol|bavoir|chauffe-biberon|sterilis|bouteille|thermos|lolette|anneau|attache", n): return "bebe", "Biberons & tétines"
        if re.search(r"couche|change|lingette|coton|liniment|erytheme|fessier|talc", n): return "bebe", "Change & couches"
        if re.search(r"jouet|eveil|hochet|peluche|tapis|trotteur|jeu|doudou|mobile|veilleuse|thermometre|mouche|aspirateur|brosse|peigne|ciseaux|coupe-ongle|trousse|sac|thermo|humidif|babyphone|transat|porte-bebe|bain|baignoire|pot ", n): return "bebe", "Éveil & accessoires"
        return "bebe", "Toilette & soins bébé"
    if C("coloration") or brand_slug == "naturtint":
        if re.search(r"colorat|couleur|color|teint|henn|mousse coloran|racines|retouche", n): return "cheveux", "Coloration"
        if re.search(r"shampo", n): return "cheveux", "Shampooings"
        if re.search(r"cc creme|creme anti age|visage", n): return "visage", "Anti-âge"
        return "cheveux", "Soins & masques"
    if C("poux-lentes") or brand_slug == "killpoux" or re.search(r"poux|lentes", n): return "cheveux", "Anti-poux"
    if brand_slug in {"phyto", "luxeol", "bioxsine", "ecrinal"} or C("cheveux", "shampoing", "soins-anti-chute", "shampoing-anti-chute", "shampoing-anti-pelliculaire", "masque-nourrissant-pour-cheveux-secs", "apres-shampooing-soin-des-cheveux", "lotion-anti-chute", "serum-pour-cheveux", "keratine", "produits-coiffants", "shampoing-cheveux-secs", "shampoing-doux", "shampoing-cheveux-gras", "masque-hydratant-pour-cheveux", "huiles-pour-cheveux", "masques-pour-cheveux", "cheveux-homme", "shampoing-cheveux-colores", "shampoing-sans-sulfate", "apres-shampoing-anti-chute", "capillaire-solaire", "shampoing-cheveux-boucles", "masque-pour-cheveux-boucles-crepus-ou-frises", "proteine-capillaire"):
        if brand_slug == "ecrinal" and re.search(r"ongle|vernis|durciss|nail", n): return "beaute", "Manucure & pédicure"
        if re.search(r"boucle|curl|frise|crepu", n): return "cheveux", "Cheveux bouclés"
        if re.search(r"anti-?chute|chute|densi|anaphase|neoptide|phytocyane|capilvit|croissance|fortifiant|kerium ds|cystiphane|bioxsine|luxeol|lotion", n) and not re.search(r"pellic", n): return "cheveux", "Anti-chute"
        if re.search(r"pellic|dandruff|squam|kelual|elution|ds ", n): return "cheveux", "Antipelliculaire"
        if re.search(r"shampo|shampoo", n): return "cheveux", "Shampooings"
        return "cheveux", "Soins & masques"
    if C("creme-solaire", "cremes-solaires", "ecran-solaire-invisible", "ecran-tout-type-de-peaux", "ecran-solaire-peau-sensible", "spray-solaire", "lait-de-corps-solaire", "cremes-solaires-enfant", "soins-apres-soleil", "huile-solaire", "stick-levres-solaire", "solaires", "protection-solaire-corps", "ecran-solaire-teinte", "ecran-solaire-anti-taches", "ecran-solaire-peau-mixte-a-grasse", "ecran-solaire-anti-age", "ecran-solaire-peau-seche") or re.search(r"spf ?\d|solaire|sunscreen|sun |anthelios|bariesun|photoderm|capital soleil|fotoprotector|daylong|ultrasun|bergasol", n):
        if re.search(r"apres-soleil|after sun|apres soleil|reparateur apres", n): return "solaire", "Après-soleil"
        if re.search(r"enfant|kids|pediatric|bebe|baby|junior", n): return "solaire", "Enfants"
        if re.search(r"lait|spray|corps|body|brume|huile|gel solaire|lotion", n) and not re.search(r"visage|face", n): return "solaire", "Corps"
        return "solaire", "Visage"
    if brand_slug in {"durex", "maximum"} or re.search(r"intime|gyn|lubrifiant|preservatif|mycolin", n): return "corps", "Hygiène intime"
    if C("deodorants-et-anti-transpirants", "deodorant-homme") or re.search(r"deodorant|deo |anti-transpirant|roll-on|roll on", n): return "corps", "Déodorants"
    if C("epilation-et-depilation-et-decoloration") or brand_slug == "veet" or re.search(r"epilat|depilat|cire ", n): return "corps", "Épilation & rasage"
    if C("soins-des-mains", "soins-des-pieds", "hygiene-des-mains") or re.search(r"mains|pieds|hand cream|creme main|foot|talon|ongle", n): return "corps", "Mains & pieds"
    if C("douche-bain", "douche-et-bain-homme") or re.search(r"gel douche|savon|douche|bain |lavant corps|huile lavante|creme lavante|gel lavant|syndet|pain ", n): return "corps", "Douche & bain"
    if C("hydratation-et-nutrition-corps", "gommage-et-exfoliant-corps", "peaux-seches-2", "corps", "cremes-hydratantes-peaux-atopiques") or re.search(r"corps|body|lait hydratant|baume corporel|xerial|topialyse|lipikar|atoderm|xemose|urea|vergeture|gommage corps|huile seche|huile prodigieuse|ichtyane", n): return "corps", "Hydratation corps"
    # everything else: visage
    if C("coffrets-parapharmacie", "routine-pack") and re.search(r"coffret|trousse|kit|routine|pack", n): return "beaute", "Coffrets & cadeaux"
    if C("sticks-et-baumes-a-levres", "stick-a-levres", "rouges-a-levres", "mascara", "crayon-a-yeux-et-eye-liner", "vernis-a-ongles", "fond-de-teint", "correcteur-de-teint", "maquillage-2", "sourcils") or re.search(r"levres|lip|mascara|vernis|fond de teint|crayon", n):
        if re.search(r"contour des yeux|eye contour|yeux", n) and not re.search(r"mascara|crayon", n): return "visage", "Yeux & lèvres"
        return "beaute", "Maquillage & lèvres"
    if C("soin-des-yeux", "anti-cernes-et-anti-poches-yeux", "contour-des-yeux", "anti-age-yeux", "demaquillants-yeux") or re.search(r"yeux|eye|cernes|paupi", n): return "visage", "Yeux & lèvres"
    if C("demaquillants-nettoyants-visage-2", "nettoyant", "gel-nettoyant", "demaquillant", "eau-micellaire", "mousse-nettoyante", "lotion-tonique", "huile-nettoyante", "creme-nettoyante", "lait-demaquillant", "contons-demaquillants-tiges-lingettes", "eaux-thermales-2", "brume-visage") or re.search(r"nettoyant|micellaire|demaquill|moussant|mousse|gel lavant|lavante|eau thermale|tonique|brume", n): return "visage", "Nettoyants & démaquillants"
    if C("masques-visage-et-gommage-2", "masque-visage", "exfoliant") or re.search(r"masque|gommage|peeling|exfoli|scrub", n): return "visage", "Masques & gommages"
    if C("soins-anti-taches-et-depigmentants-2", "cremes-anti-taches", "serum-anti-taches", "eclat-du-teint-3", "cremes-eclaircissantes", "soins-eclaircissants-2", "gels-nettoyants-eclaircissants", "serum-eclaircissant", "correcteurs-de-taches", "serum-vitamine-c", "nettoyants-anti-taches") or re.search(r"tache|pigment|eclat|eclairciss|whiten|glow|vitamine c|vit c|depiwhite|iklen|melascreen|mela|radiance|luminos", n): return "visage", "Anti-taches & éclat"
    if C("soins-peau-grasse-ou-mixte-et-acne-2", "peau-a-tendance-acneique", "nettoyant-peau-acneique", "soin-localise") or re.search(r"acne|imperfection|sebium|effaclar|cleanance|hyseac|sebiaclear|keracnyl|exfoliac|normaderm|acniben|matifiant|purif|sebo|boutons|pores|zinc", n): return "visage", "Anti-imperfections"
    if C("soins-anti-rougeurs-et-peau-sensible-2", "soins-apaisants-2", "peau-sensible", "baume-reparateur", "soins-des-cicatrices-2") and re.search(r"apais|rougeur|sensib|reparat|cicatri|cica|tolerance|sensifine|sensibio|toleriane|rosal|rose|baume", n): return "visage", "Peaux sensibles"
    if C("serum", "serum-anti-age", "serum-hydratant", "serum-acide-hyaluronique", "serum-niacinamide", "serum-retinol", "serum-acide-glycolique", "huiles-et-serums", "soin-avec-actifs") or re.search(r"serum|ampoule|booster|concentr", n):
        if re.search(r"rides|anti-age|age|lift|retinol|collag|firm|ferme", n): return "visage", "Anti-âge"
        return "visage", "Sérums"
    if C("soins-anti-age-et-anti-rides-2", "cremes-anti-rides", "cremes-anti-age", "peau-mature") or re.search(r"rides|anti-age|anti-aging|lift|retinol|collagene|fermete|time-filler|hyaluron-filler|liftactiv|redermic|nuxuriance|age", n): return "visage", "Anti-âge"
    if C("creme-hydratante", "soins-hydratants-et-nourrissants-2", "cremes-hydratantes-peaux-seches", "cremes-hydratantes-peaux-sensibles", "cremes-hydratantes-toutes-peaux", "cremes-hydratantes-peaux-normales-a-mixtes") or re.search(r"hydrat|nourri|creme|gel-creme|fluide|emollient|moistur|visage|face|peau|skin|soin", n): return "visage", "Hydratation"
    if cats:
        return "visage", "Hydratation"
    return brand_default(brand_slug, n)


BRAND_DEFAULT = {
    "bibs": ("bebe", "Biberons & tétines"), "nuk": ("bebe", "Biberons & tétines"),
    "suavinex": ("bebe", "Biberons & tétines"), "wee": ("bebe", "Biberons & tétines"),
    "canpol": ("bebe", "Éveil & accessoires"), "chicco": ("bebe", "Éveil & accessoires"),
    "dodie": ("bebe", "Biberons & tétines"), "avent": ("bebe", "Biberons & tétines"),
    "tommee-tippee": ("bebe", "Biberons & tétines"), "momcozy": ("bebe", "Allaitement & tire-lait"),
    "medela": ("bebe", "Allaitement & tire-lait"), "nimo": ("bebe", "Allaitement & tire-lait"),
    "biolane": ("bebe", "Toilette & soins bébé"), "mustela": ("bebe", "Toilette & soins bébé"),
    "alphanova": ("bebe", "Toilette & soins bébé"), "materna": ("bebe", "Toilette & soins bébé"),
    "pampers": ("bebe", "Change & couches"), "bebeto": ("bebe", "Biberons & tétines"),
    "doppelherz": ("complements", "Vitamines & minéraux"), "herbex": ("complements", "Vitamines & minéraux"),
    "therapia": ("complements", "Vitamines & minéraux"), "bioherbs": ("complements", "Vitamines & minéraux"),
    "pediakid": ("complements", "Enfants"), "gummybear": ("complements", "Vitamines & minéraux"),
    "luxeol": ("complements", "Cheveux & ongles"), "biorga": ("complements", "Cheveux & ongles"),
    "gum": ("bucco", "Brosses à dents"), "elgydium": ("bucco", "Dentifrices"), "kin": ("bucco", "Dentifrices"),
    "sensodyne": ("bucco", "Dentifrices"), "parodontax": ("bucco", "Dentifrices"), "klorex": ("bucco", "Dentifrices"),
    "oral-b": ("bucco", "Brosses à dents"), "listerine": ("bucco", "Bains de bouche"), "meridol": ("bucco", "Dentifrices"),
    "elmex": ("bucco", "Dentifrices"), "silca": ("bucco", "Brosses à dents"),
    "beurer": ("medical", "Tensiomètres & mesure"), "rossmax": ("medical", "Tensiomètres & mesure"),
    "medel": ("medical", "Tensiomètres & mesure"), "accu-chek": ("medical", "Glycémie"),
    "orthomed": ("medical", "Orthèses & supports"), "orthofix": ("medical", "Orthèses & supports"),
    "curall": ("medical", "Premiers soins"), "bandlux": ("medical", "Premiers soins"),
    "physiomer": ("medical", "Confort & bien-être"), "quies": ("medical", "Confort & bien-être"),
    "titania": ("beaute", "Manucure & pédicure"), "eye-care": ("beaute", "Maquillage & lèvres"),
    "eveline": ("beaute", "Manucure & pédicure"), "anycare": ("medical", "Confort & bien-être"),
    "septanil": ("autres", "Maison & divers"), "auracy": ("autres", "Maison & divers"),
    "durex": ("corps", "Hygiène intime"), "maximum": ("corps", "Hygiène intime"),
    "saforelle": ("corps", "Hygiène intime"), "lilas": ("corps", "Hygiène intime"),
    "roge-cavailles": ("corps", "Douche & bain"), "byphasse": ("corps", "Douche & bain"),
    "laino": ("corps", "Hydratation corps"), "bio-orient": ("corps", "Hydratation corps"),
    "beesline": ("corps", "Déodorants"), "veet": ("corps", "Épilation & rasage"),
    "naturtint": ("cheveux", "Coloration"), "phyto": ("cheveux", "Soins & masques"),
    "bioxsine": ("cheveux", "Anti-chute"), "ecrinal": ("beaute", "Manucure & pédicure"),
    "killpoux": ("cheveux", "Anti-poux"), "daylong": ("solaire", "Visage"), "ultrasun": ("solaire", "Visage"),
}


def brand_default(brand_slug, n):
    if brand_slug in BRAND_DEFAULT:
        return BRAND_DEFAULT[brand_slug]
    return "autres", "Maison & divers"


SMALL = {"de", "du", "des", "la", "le", "les", "et", "a", "à", "au", "aux", "en", "pour", "avec", "sans", "sur", "d", "l", "the", "of", "and", "for", "with"}
UNITS = re.compile(r"^(\d+(?:[.,]\d+)?)(ml|g|gr|kg|l|cl|mg|mm|cm)$", re.I)


def smart_title(n):
    out = []
    for i, w in enumerate(n.split(" ")):
        lw = w.lower()
        if UNITS.match(lw):
            m = UNITS.match(lw); out.append(m.group(1) + m.group(2).lower()); continue
        if re.match(r"^(spf|uv|ph|bb|cc|sos|xl|xs|dna|led|ha|c20|b3|b5|k2|d3|ip|pm|am)\d*\+?$", lw):
            out.append(w.upper()); continue
        if i and lw in SMALL:
            out.append(lw); continue
        out.append("-".join(part[:1].upper() + part[1:].lower() for part in w.split("-")))
    return " ".join(out)


def clean_name(name, brand_display):
    import html as _h
    n = _h.unescape(_h.unescape(name))
    n = n.replace("’", "'").replace("Esth'Elle", "Esth'elle").replace("ESTH'ELLE", "Esth'elle")
    n = re.sub(r"\s+", " ", n).strip()
    letters = [c for c in n if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        n = smart_title(n)
    # drop a leading brand mention so cards read "Brand / Product"
    b = strip_accents(brand_display).lower().replace("-", " ")
    for _ in range(2):
        nn = strip_accents(n).lower().replace("-", " ")
        if nn.startswith(b + " "):
            n = n[len(brand_display):].strip(" -–:")
        elif brand_display == "Rogé Cavaillès" and nn.startswith("roge cavailles"):
            n = n[len("roge cavailles"):].strip(" -–:")
        elif brand_display == "Eye Care Cosmetics" and nn.startswith("eye care "):
            n = n[len("eye care "):].strip(" -–:")
    n = re.sub(r"\s*-\s*$", "", n)
    n = n[:1].upper() + n[1:]
    return n


def fetch_image(url, slug):
    dest = os.path.join(IMG_DIR, slug + ".jpg")
    if os.path.exists(dest):
        return dest
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=40) as r:
            data = r.read()
        im = Image.open(io.BytesIO(data))
        im = im.convert("RGBA")
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
    products, seen_slugs = [], set()
    for brand_slug, (display, pattern, cap) in SEEN.items():
        path = os.path.join(RAW, brand_slug + ".json")
        if not os.path.exists(path):
            print("missing raw", brand_slug); continue
        raw = json.load(open(path))
        picked = []
        for p in raw:
            if not p["name"] or not p["image"] or not p["price"]:
                continue
            n = norm(p["name"])
            if pattern and not re.search(pattern, n):
                continue
            if brand_slug not in EXCLUDE_KEEP_BRANDS and re.search(EXCLUDE, n):
                continue
            if re.search(r"testeur|echantillon|lot de|x2|x3|duo pack|pack de|offre|promo", n):
                continue
            picked.append(p)
        # prefer in-stock, then the site's own order (popularity-ish)
        picked.sort(key=lambda p: (not p["instock"],))
        picked = picked[:cap]
        for p in picked:
            name = clean_name(p["name"], display)
            slug = slugify(display + " " + name)
            if slug in seen_slugs:
                slug += "-" + hashlib.md5(p["url"].encode()).hexdigest()[:4]
            seen_slugs.add(slug)
            cat, sub = classify(p, brand_slug)
            price = round(float(p["price"]), 3)
            # Tunisian pricing convention: x.900 / x.500 — round to nearest 0.1 dinar
            price = round(price * 10) / 10
            products.append({
                "id": slug,
                "name": name,
                "brand": display,
                "brand_slug": brand_slug,
                "category": cat,
                "sub": sub,
                "price": price,
                "image": f"images/products/{slug}.jpg",
                "src_image": p["image"],
                "bullets": p["bullets"],
                "instock": p["instock"],
            })
    print("selected", len(products))
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda p: fetch_image(p["src_image"], p["id"]), products))
    products = [p for p in products if os.path.exists(os.path.join(IMG_DIR, p["id"] + ".jpg"))]
    for p in products:
        p.pop("src_image", None)
    json.dump(products, open(OUT, "w"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(p["category"] for p in products))
    print(Counter((p["category"], p["sub"]) for p in products).most_common(60))
    print("written", OUT, len(products))


if __name__ == "__main__":
    main()
