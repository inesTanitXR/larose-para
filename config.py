"""Shop details and site-wide settings.  Edit here, then run: python3 build.py

Anything marked [À CONFIRMER] is a guess and should be checked with the shop before launch.
"""

SITE_NAME = "La Rose Parapharmacie"
SITE_SHORT = "La Rose"
TAGLINE = "Parapharmacie & dermocosmétique"
BASELINE = "Votre bien-être, notre priorité"
DESCRIPTION = ("Parapharmacie à Nabeul : soins du visage, solaires, cheveux, bébé, compléments "
               "et matériel médical. Livraison partout en Tunisie, paiement à la livraison.")

PHONE = "23 979 204"
PHONE_INTL = "+21623979204"
WHATSAPP = "21623979204"
EMAIL = "inessaid88@gmail.com"      # destinataire principal des commandes (FormSubmit — activer le lien reçu au 1er envoi)
EMAIL_CC = "fatmazangar95@gmail.com"  # en copie de chaque commande
MESSENGER = "https://m.me/61587418413300"
ADDRESS = "Avenue Hédi Nouira"
CITY = "Nabeul"
COUNTRY = "Tunisie"
MAPS_URL = "https://maps.app.goo.gl/jkMJwcENoHrwGE3X8"
MAPS_EMBED = ("https://www.google.com/maps?q=36.4439489,10.7141365&hl=fr&z=16&output=embed")
LAT, LNG = 36.4439489, 10.7141365

INSTAGRAM = "https://www.instagram.com/la_rose_para/"
FACEBOOK = "https://www.facebook.com/profile.php?id=61587418413300"

# [À CONFIRMER] horaires
HOURS = [
    ("Lundi – Samedi", "09:00 – 20:00"),
    ("Dimanche", "09:00 – 14:00"),
]

# Livraison — [À CONFIRMER] tarifs et seuil
DELIVERY_FEE = 8.0                  # dinars, livraison à domicile
FREE_DELIVERY_FROM = 150.0          # livraison offerte à partir de ce montant
DELIVERY_DAYS = "24 à 72 h"

CURRENCY = "DT"

# Carte Rose (fidélité) : 1 DT = 1 pétale ; 250 pétales = bon de LOYALTY_BON dinars
LOYALTY_BON = 15.0
SAMPLES_FROM = 250.0
WORKER_URL = ""             # registre Carte Rose (voir worker/README.md) — vide = local seulement        # échantillons offerts à partir de ce montant de commande (livraison exclue)

GOVERNORATES = [
    "Ariana", "Béja", "Ben Arous", "Bizerte", "Gabès", "Gafsa", "Jendouba", "Kairouan",
    "Kasserine", "Kébili", "La Manouba", "Le Kef", "Mahdia", "Médenine", "Monastir",
    "Nabeul", "Sfax", "Sidi Bouzid", "Siliana", "Sousse", "Tataouine", "Tozeur",
    "Tunis", "Zaghouan",
]

# Ordre d'affichage des rayons
CATEGORY_ORDER = ["visage", "solaire", "cheveux", "corps", "bebe", "complements",
                  "bucco", "medical", "beaute", "autres"]

CATEGORY_META = {
    "visage":      ("Visage", "Nettoyants, sérums, hydratation, anti-âge et soins ciblés.", "cat-visage.jpg"),
    "solaire":     ("Solaire", "Écrans SPF 50+, teintés, invisibles, pour toute la famille.", "cat-solaire.jpg"),
    "cheveux":     ("Cheveux", "Shampooings, anti-chute, antipelliculaire, boucles et coloration.", "cat-cheveux.jpg"),
    "corps":       ("Corps & hygiène", "Douche, hydratation, déodorants, hygiène intime, mains et pieds.", "cat-corps.jpg"),
    "bebe":        ("Bébé & maman", "Toilette, change, biberons, allaitement et éveil.", "cat-bebe.jpg"),
    "complements": ("Compléments", "Vitamines, cheveux & ongles, sommeil, immunité, minceur.", "cat-complements.jpg"),
    "bucco":       ("Bucco-dentaire", "Dentifrices, brosses, bains de bouche et interdentaire.", "cat-bucco.jpg"),
    "medical":     ("Matériel médical", "Tensiomètres, glycémie, orthèses, premiers soins.", "cat-medical.jpg"),
    "beaute":      ("Beauté & accessoires", "Manucure, appareils, bijoux hypoallergéniques, coffrets.", "cat-accessoires.jpg"),
    "autres":      ("Autres produits", "Le reste du rayon : maison, divers et nouveautés.", "cat-corps.jpg"),
}

# Marques mises en avant sur l'accueil
FEATURED_BRANDS = ["La Roche-Posay", "Avène", "Bioderma", "CeraVe", "Uriage", "SVR", "ISDIN",
                   "Vichy", "Eucerin", "Nuxe", "Filorga", "Ducray", "Mustela", "NUK", "Phyto",
                   "Novexpert", "Sensilis", "Noreva", "ACM", "Lierac"]
