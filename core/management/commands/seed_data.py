"""
python manage.py seed_data            # insère tout
python manage.py seed_data --flush    # vide la DB avant d'insérer
"""
import random
import requests
from decimal import Decimal
from io import BytesIO
from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.text import slugify
from django.utils import timezone
from django.db import transaction
from datetime import timedelta


# ──────────────────────────────────────────────────────────────────────────────
#  Images : URLs Unsplash par mot-clé (redirections stables par signature)
#  Unsplash Source retourne une photo pertinente selon les mots-clés.
# ──────────────────────────────────────────────────────────────────────────────
IMGS = {
    # Matelas / Literie
    "matelas_1":   "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&h=800&fit=crop&auto=format&q=80",
    "matelas_2":   "https://images.unsplash.com/photo-1588345921523-c2dcdb7f1dcd?w=800&h=800&fit=crop&auto=format&q=80",
    "matelas_3":   "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=800&h=800&fit=crop&auto=format&q=80",
    "matelas_4":   "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=800&h=800&fit=crop&auto=format&q=80",
    "matelas_5":   "https://images.unsplash.com/photo-1615874959474-d609969a20ed?w=800&h=800&fit=crop&auto=format&q=80",
    # Oreillers / Draps
    "oreillers_1": "https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?w=800&h=800&fit=crop&auto=format&q=80",
    "oreillers_2": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=800&fit=crop&auto=format&q=80",
    "draps_1":     "https://images.unsplash.com/photo-1542665952-14513db15293?w=800&h=800&fit=crop&auto=format&q=80",
    "draps_2":     "https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?w=800&h=800&fit=crop&auto=format&q=80",
    # Canapés / Salon
    "canape_1":    "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800&h=800&fit=crop&auto=format&q=80",
    "canape_2":    "https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=800&h=800&fit=crop&auto=format&q=80",
    "canape_3":    "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800&h=800&fit=crop&auto=format&q=80",
    "fauteuil_1":  "https://images.unsplash.com/photo-1567538096630-e0c55bd6374c?w=800&h=800&fit=crop&auto=format&q=80",
    "fauteuil_2":  "https://images.unsplash.com/photo-1506439773649-6e0eb8cfb237?w=800&h=800&fit=crop&auto=format&q=80",
    "table_b":     "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=800&h=800&fit=crop&auto=format&q=80",
    # Chambre / Lit
    "lit_1":       "https://images.unsplash.com/photo-1540518614846-7eded433c457?w=800&h=800&fit=crop&auto=format&q=80",
    "lit_2":       "https://images.unsplash.com/photo-1505691938895-1758d7feb511?w=800&h=800&fit=crop&auto=format&q=80",
    "armoire_1":   "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=800&h=800&fit=crop&auto=format&q=80",
    "chevet_1":    "https://images.unsplash.com/photo-1565814636199-ae8133055c1c?w=800&h=800&fit=crop&auto=format&q=80",
    "commode_1":   "https://images.unsplash.com/photo-1580480055273-228ff5388ef8?w=800&h=800&fit=crop&auto=format&q=80",
    # Luminaires
    "lampe_1":     "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&h=800&fit=crop&auto=format&q=80",
    "lampe_2":     "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&h=800&fit=crop&auto=format&q=80",
    "lustre_1":    "https://images.unsplash.com/photo-1540932239986-30128078f3c5?w=800&h=800&fit=crop&auto=format&q=80",
    "applique_1":  "https://images.unsplash.com/photo-1540932239986-30128078f3c5?w=800&h=800&fit=crop&auto=format&q=80",
    # Décoration
    "deco_tapis":  "https://images.unsplash.com/photo-1600166898405-da9535204843?w=800&h=800&fit=crop&auto=format&q=80",
    "deco_miroir": "https://images.unsplash.com/photo-1618220179428-22790b461013?w=800&h=800&fit=crop&auto=format&q=80",
    "deco_tableau":"https://images.unsplash.com/photo-1578926288207-a90a5366759d?w=800&h=800&fit=crop&auto=format&q=80",
    "deco_vase":   "https://images.unsplash.com/photo-1612196808214-b8e1d6145a8c?w=800&h=800&fit=crop&auto=format&q=80",
    # Table à manger
    "table_m1":    "https://images.unsplash.com/photo-1449247709967-d4461a6a6103?w=800&h=800&fit=crop&auto=format&q=80",
    "table_m2":    "https://images.unsplash.com/photo-1533090161767-e6ffed986c88?w=800&h=800&fit=crop&auto=format&q=80",
    "chaise_m":    "https://images.unsplash.com/photo-1551298370-9d3d53740c72?w=800&h=800&fit=crop&auto=format&q=80",
    "buffet_1":    "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=800&h=800&fit=crop&auto=format&q=80",
    # Chaise luxe
    "chester":     "https://images.unsplash.com/photo-1567538096630-e0c55bd6374c?w=800&h=800&fit=crop&auto=format&q=80",
    "chaise_s":    "https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=800&h=800&fit=crop&auto=format&q=80",
    "pouf_1":      "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800&h=800&fit=crop&auto=format&q=80",
    # Électroménager
    "ventilo_1":   "https://images.unsplash.com/photo-1625014618427-fbc980b974f5?w=800&h=800&fit=crop&auto=format&q=80",
    "frigo_1":     "https://images.unsplash.com/photo-1584568694244-14fbdf83bd30?w=800&h=800&fit=crop&auto=format&q=80",
    "clim_1":      "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=800&h=800&fit=crop&auto=format&q=80",
    # Fashion / Confort
    "peignoir":    "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=800&fit=crop&auto=format&q=80",
    "pantoufle":   "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=800&h=800&fit=crop&auto=format&q=80",
    # Bagages / Valises
    "valise_1":    "https://images.unsplash.com/photo-1565026057447-bc90a3dceb87?w=800&h=800&fit=crop&auto=format&q=80",
    "valise_2":    "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?w=800&h=800&fit=crop&auto=format&q=80",
    "valise_set":  "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=800&h=800&fit=crop&auto=format&q=80",
    # Vaissellerie
    "vaisselle_1": "https://images.unsplash.com/photo-1610701596007-11502861dcfa?w=800&h=800&fit=crop&auto=format&q=80",
    "vaisselle_2": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800&h=800&fit=crop&auto=format&q=80",
    "verres":      "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&h=800&fit=crop&auto=format&q=80",
    # Pack DOOYA
    "pack_ch":     "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=800&h=800&fit=crop&auto=format&q=80",
    "pack_sal":    "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800&h=800&fit=crop&auto=format&q=80",
}


def img_url(key):
    return IMGS[key]


def download_image(url, name="image.jpg"):
    """Télécharge une image et retourne un InMemoryUploadedFile ou None."""
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "DooyaSeeder/1.0"})
        r.raise_for_status()
        content = r.content
        buf = BytesIO(content)
        return InMemoryUploadedFile(buf, "image", name, "image/jpeg", len(content), None)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
#  Données produits
# ──────────────────────────────────────────────────────────────────────────────
CATEGORIES = [
    {"name": "Literie",        "slug": "literie",        "icon": "bed",          "order": 1, "children": [
        {"name": "Matelas",          "slug": "matelas",          "icon": "mattress",    "order": 1},
        {"name": "Oreillers",        "slug": "oreillers",        "icon": "pillow",      "order": 2},
        {"name": "Draps & Parures",  "slug": "draps-parures",    "icon": "sheets",      "order": 3},
        {"name": "Couettes",         "slug": "couettes",         "icon": "duvet",       "order": 4},
    ]},
    {"name": "Ameublement",    "slug": "ameublement",    "icon": "furniture",    "order": 2, "children": [
        {"name": "Salon",            "slug": "salon",            "icon": "sofa",        "order": 1},
        {"name": "Chambre",          "slug": "chambre",          "icon": "bedroom",     "order": 2},
        {"name": "Bureau",           "slug": "bureau",           "icon": "desk",        "order": 3},
    ]},
    {"name": "Décoration",     "slug": "decoration",     "icon": "decor",        "order": 3},
    {"name": "Luminaires",     "slug": "luminaires",     "icon": "lamp",         "order": 4},
    {"name": "Electroménager", "slug": "electromenager", "icon": "appliance",    "order": 5},
    {"name": "Fashion",        "slug": "fashion",        "icon": "fashion",      "order": 6},
    {"name": "Table A Manger", "slug": "table-manger",   "icon": "dining",       "order": 7},
    {"name": "Bagages",        "slug": "bagages",        "icon": "luggage",      "order": 8},
    {"name": "Chaise de luxe", "slug": "chaise-luxe",    "icon": "chair",        "order": 9},
    {"name": "Vaissellerie",   "slug": "vaissellerie",   "icon": "dishes",       "order": 10},
    {"name": "Pack DOOYA",     "slug": "pack-dooya",     "icon": "pack",         "order": 11},
]

VENDORS = [
    {"first_name": "Kouamé",   "last_name": "Assi",     "username": "kouame_assi",    "email": "kouame@dooya-vendor.ci",   "store": "Literie Premium CI",    "store_slug": "literie-premium-ci"},
    {"first_name": "Adjoua",   "last_name": "Bamba",    "username": "adjoua_bamba",   "email": "adjoua@dooya-vendor.ci",   "store": "Meublerie Adjoua",       "store_slug": "meublerie-adjoua"},
    {"first_name": "Barthélémy","last_name": "Koffi",   "username": "bart_koffi",     "email": "bart@dooya-vendor.ci",     "store": "Déco & Lumière Abidjan", "store_slug": "deco-lumiere-abidjan"},
]

PRODUCTS = [
    # ── MATELAS ───────────────────────────────────────────────────────
    {
        "name": "Matelas Orthopédique Premium 160×200",
        "short_description": "Matelas à ressorts ensachés haute densité, housse en coton quilted.",
        "description": "<p>Notre matelas orthopédique premium offre un soutien exceptionnel pour votre dos. Fabriqué avec 1 500 ressorts ensachés indépendants, il s'adapte parfaitement à la morphologie de chaque dormeur. Housse en coton égyptien quilted, respirante et anti-acariens.</p><p><strong>Dimensions :</strong> 160 × 200 × 28 cm<br><strong>Matière :</strong> Ressorts ensachés + mousse mémoire<br><strong>Fermeté :</strong> Médium-ferme</p>",
        "category": "matelas", "store_idx": 0,
        "price": 189000, "compare_price": 245000,
        "discount_type": "percentage", "discount_value": 20,
        "stock": 25, "is_featured": True, "rating": 4.8, "reviews_count": 142,
        "images": ["matelas_1", "matelas_2"],
        "tags": ["matelas", "literie", "orthopédique", "premium"],
    },
    {
        "name": "Matelas Mémoire de Forme 140×190",
        "short_description": "Technologie visco-élastique pour un sommeil sur mesure.",
        "description": "<p>La mousse mémoire de forme de haute qualité épouse parfaitement les courbes de votre corps, éliminant les points de pression. Idéal pour les personnes souffrant de douleurs dorsales.</p><p><strong>Dimensions :</strong> 140 × 190 × 24 cm<br><strong>Mousse :</strong> 50 kg/m³ visco-élastique<br><strong>Fermeté :</strong> Médium-doux</p>",
        "category": "matelas", "store_idx": 0,
        "price": 145000, "compare_price": 178000,
        "discount_type": "percentage", "discount_value": 15,
        "stock": 18, "is_featured": False, "rating": 4.6, "reviews_count": 89,
        "images": ["matelas_3", "matelas_4"],
        "tags": ["matelas", "mémoire de forme"],
    },
    {
        "name": "Matelas Mousse HR 90×190 — Bonne Nuit",
        "short_description": "Matelas économique haute résilience, parfait pour chambres d'amis.",
        "description": "<p>Matelas en mousse haute résilience (HR 35) pour un confort quotidien durable. Idéal pour les chambres d'amis ou les petits budgets sans compromis sur la qualité.</p>",
        "category": "matelas", "store_idx": 0,
        "price": 65000, "compare_price": None,
        "discount_type": None, "discount_value": None,
        "stock": 40, "is_featured": False, "rating": 4.2, "reviews_count": 56,
        "images": ["matelas_5", "matelas_1"],
        "tags": ["matelas", "économique"],
    },
    {
        "name": "Matelas Bébé Hypoallergénique 60×120",
        "short_description": "Matelas ferme et sécurisé pour bébé, certifié OEKO-TEX.",
        "description": "<p>Matelas spécialement conçu pour les bébés de 0 à 3 ans. Fermeté optimale pour le développement du dos. Housse amovible et lavable en machine. Certifié OEKO-TEX Standard 100.</p>",
        "category": "matelas", "store_idx": 0,
        "price": 42000, "compare_price": 52000,
        "discount_type": "fixed", "discount_value": 10000,
        "stock": 30, "is_featured": False, "rating": 4.9, "reviews_count": 67,
        "images": ["matelas_2", "matelas_3"],
        "tags": ["matelas", "bébé", "hypoallergénique"],
    },
    # ── OREILLERS ─────────────────────────────────────────────────────
    {
        "name": "Oreiller Mémoire de Forme Ergonomique",
        "short_description": "Soutien cervical optimal, housse bambou ultra-douce.",
        "description": "<p>Oreiller ergonomique avec noyau en mousse à mémoire de forme qui soutient parfaitement la nuque. Housse en bambou 60% douce et respirante.</p>",
        "category": "oreillers", "store_idx": 0,
        "price": 18500, "compare_price": 24000,
        "discount_type": "percentage", "discount_value": 22,
        "stock": 60, "is_featured": True, "rating": 4.7, "reviews_count": 203,
        "images": ["oreillers_1", "oreillers_2"],
        "tags": ["oreiller", "mémoire de forme", "ergonomique"],
    },
    {
        "name": "Pack 2 Oreillers Anti-Acariens Premium",
        "short_description": "Traitement permanent anti-acariens, garnissage microfibre.",
        "description": "<p>Set de 2 oreillers traitement permanent anti-acariens. Garnissage en fibre creuse siliconée pour un confort moelleux. Housse 100% coton percale.</p>",
        "category": "oreillers", "store_idx": 0,
        "price": 22000, "compare_price": 28000,
        "discount_type": "fixed", "discount_value": 6000,
        "stock": 45, "is_featured": False, "rating": 4.5, "reviews_count": 118,
        "images": ["oreillers_2", "oreillers_1"],
        "tags": ["oreiller", "anti-acariens", "lot 2"],
    },
    # ── DRAPS & PARURES ────────────────────────────────────────────────
    {
        "name": "Parure de Lit Satin de Coton 160×200 — Blanc Ivoire",
        "short_description": "Drap housse + taies + drap plat en satin de coton 300 fils.",
        "description": "<p>Parure complète 4 pièces en satin de coton 300 fils. Finition satinée brillante pour un rendu luxueux. Comprend : 1 drap housse 160×200+30cm, 2 taies 50×70cm, 1 drap plat 240×290cm.</p>",
        "category": "draps-parures", "store_idx": 0,
        "price": 55000, "compare_price": 72000,
        "discount_type": "percentage", "discount_value": 23,
        "stock": 35, "is_featured": True, "rating": 4.8, "reviews_count": 167,
        "images": ["draps_1", "draps_2"],
        "tags": ["draps", "satin", "parure", "literie"],
    },
    {
        "name": "Housse de Couette Bambou 260×240",
        "short_description": "Tissu bambou ultra-respirant, fermeture boutons.",
        "description": "<p>Housse de couette en tissu bambou/coton (60/40). Extrêmement douce et thermorégulatrice, idéale pour le climat ivoirien. Fermeture boutons pression invisibles.</p>",
        "category": "draps-parures", "store_idx": 0,
        "price": 38500, "compare_price": None,
        "discount_type": None, "discount_value": None,
        "stock": 28, "is_featured": False, "rating": 4.6, "reviews_count": 92,
        "images": ["draps_2", "draps_1"],
        "tags": ["housse couette", "bambou", "draps"],
    },
    # ── CANAPÉS ───────────────────────────────────────────────────────
    {
        "name": "Canapé 3 Places Velours Gris Anthracite",
        "short_description": "Structure bois massif, pieds métal doré, tissu velours premium.",
        "description": "<p>Canapé 3 places élégant en velours gris anthracite. Structure en bois massif traité, pieds en métal doré brossé. Assises et dossiers en mousse haute densité pour un confort optimal.</p><p><strong>Dimensions :</strong> L 215 × P 88 × H 85 cm<br><strong>Tissu :</strong> Velours polyester 380 g/m²<br><strong>Poids max :</strong> 400 kg</p>",
        "category": "salon", "store_idx": 1,
        "price": 285000, "compare_price": 360000,
        "discount_type": "percentage", "discount_value": 20,
        "stock": 8, "is_featured": True, "rating": 4.9, "reviews_count": 78,
        "images": ["canape_1", "canape_2"],
        "tags": ["canapé", "salon", "velours", "3 places"],
    },
    {
        "name": "Canapé d'Angle Convertible Tissu Beige",
        "short_description": "Angle réversible, convertible lit 140cm, coffre de rangement.",
        "description": "<p>Canapé d'angle convertible idéal pour les petits espaces. Angle réversible (gauche ou droite). Se transforme en lit 140×190cm. Coffre de rangement intégré dans la méridienne.</p>",
        "category": "salon", "store_idx": 1,
        "price": 395000, "compare_price": 480000,
        "discount_type": "fixed", "discount_value": 85000,
        "stock": 5, "is_featured": True, "rating": 4.7, "reviews_count": 54,
        "images": ["canape_2", "canape_3"],
        "tags": ["canapé angle", "convertible", "salon"],
    },
    {
        "name": "Fauteuil Relax Cuir PU Noir — Signature",
        "short_description": "Position zéro-gravité, repose-pieds intégré, cuir PU premium.",
        "description": "<p>Fauteuil relax électrique avec 3 positions mémorisées. Repose-pieds rabattable. Revêtement en cuir PU premium, facile d'entretien. Parfait pour lire ou regarder la TV.</p>",
        "category": "salon", "store_idx": 1,
        "price": 175000, "compare_price": 220000,
        "discount_type": "percentage", "discount_value": 20,
        "stock": 12, "is_featured": False, "rating": 4.8, "reviews_count": 89,
        "images": ["fauteuil_1", "fauteuil_2"],
        "tags": ["fauteuil", "relax", "cuir", "salon"],
    },
    {
        "name": "Table Basse Verre Trempé + Marbre",
        "short_description": "Plateau verre trempé 8mm, base marbre véritable, pieds inox.",
        "description": "<p>Table basse design contemporain, plateau en verre trempé 8mm extra-blanc, base en marbre naturel de Carrare, pieds en inox brossé. Un meuble d'exception pour sublimer votre salon.</p>",
        "category": "salon", "store_idx": 1,
        "price": 98000, "compare_price": 125000,
        "discount_type": "percentage", "discount_value": 21,
        "stock": 15, "is_featured": False, "rating": 4.6, "reviews_count": 63,
        "images": ["table_b", "canape_1"],
        "tags": ["table basse", "verre", "salon"],
    },
    # ── CHAMBRE ───────────────────────────────────────────────────────
    {
        "name": "Lit Double Coffre 160×200 Tête de Lit Capitonnée",
        "short_description": "Coffre de rangement 200L, tête de lit capitonnée velours.",
        "description": "<p>Lit double avec coffre de rangement XXL (200 litres). Tête de lit capitonnée en velours bleu nuit avec boutons dorés. Structure en bois aggloméré HD. Livré sans matelas.</p>",
        "category": "chambre", "store_idx": 1,
        "price": 320000, "compare_price": 395000,
        "discount_type": "fixed", "discount_value": 75000,
        "stock": 6, "is_featured": True, "rating": 4.9, "reviews_count": 45,
        "images": ["lit_1", "lit_2"],
        "tags": ["lit", "chambre", "coffre", "160"],
    },
    {
        "name": "Armoire 3 Portes Miroir Coulissante — Bella",
        "short_description": "Miroir pleine hauteur, intérieur aménagé, fermeture silencieuse.",
        "description": "<p>Armoire contemporaine 3 portes dont 2 miroirs pleine hauteur. Intérieur aménagé avec penderie + 4 étagères + 2 tiroirs. Système coulissant ultra-silencieux. Bois blanc mat.</p><p><strong>Dimensions :</strong> L 180 × P 60 × H 220 cm</p>",
        "category": "chambre", "store_idx": 1,
        "price": 245000, "compare_price": 298000,
        "discount_type": "percentage", "discount_value": 17,
        "stock": 7, "is_featured": False, "rating": 4.7, "reviews_count": 38,
        "images": ["armoire_1", "lit_1"],
        "tags": ["armoire", "miroir", "chambre"],
    },
    {
        "name": "Table de Chevet Flottante LED — Glow",
        "short_description": "Rétroéclairage LED RGB, tiroir softclose, charge sans fil.",
        "description": "<p>Table de chevet murale avec rétroéclairage LED RGB à télécommande. Tiroir à fermeture douce. Plateau en chêne naturel. Emplacement recharge sans fil Qi intégré.</p>",
        "category": "chambre", "store_idx": 2,
        "price": 58000, "compare_price": 75000,
        "discount_type": "percentage", "discount_value": 22,
        "stock": 20, "is_featured": True, "rating": 4.8, "reviews_count": 112,
        "images": ["chevet_1", "lampe_2"],
        "tags": ["table de chevet", "LED", "chambre"],
    },
    # ── LUMINAIRES ────────────────────────────────────────────────────
    {
        "name": "Lampadaire Trépied Industriel Noir — Vintage",
        "short_description": "Style industriel, bras articulé, ampoule E27 incluse.",
        "description": "<p>Lampadaire sur trépied en métal noir mat style industriel. Bras articulable sur 180°. Abat-jour rotatif. Câble tressé vintage. Compatible ampoules E27 jusqu'à 60W. Ampoule Edison incluse.</p><p><strong>Hauteur :</strong> 165 cm (réglable 140-175 cm)</p>",
        "category": "luminaires", "store_idx": 2,
        "price": 78000, "compare_price": 95000,
        "discount_type": "fixed", "discount_value": 17000,
        "stock": 22, "is_featured": True, "rating": 4.7, "reviews_count": 134,
        "images": ["lampe_1", "lampe_2"],
        "tags": ["lampadaire", "luminaires", "industriel"],
    },
    {
        "name": "Lustre Cristal Bohème 5 Branches — Étoile",
        "short_description": "500 cristaux swarovski-style, lustre Ø60cm, E14×5.",
        "description": "<p>Lustre de prestige avec 500 cristaux taillés en facettes. Structure en métal doré. Diamètre 60 cm. Hauteur ajustable de 40 à 120 cm. Convient pour ampoules E14 × 5 (non incluses).</p>",
        "category": "luminaires", "store_idx": 2,
        "price": 125000, "compare_price": 168000,
        "discount_type": "percentage", "discount_value": 25,
        "stock": 10, "is_featured": True, "rating": 4.9, "reviews_count": 67,
        "images": ["lustre_1", "lampe_1"],
        "tags": ["lustre", "cristal", "luminaires", "luxe"],
    },
    {
        "name": "Lampe de Chevet Tactile LED Dimmable — Touch",
        "short_description": "3 niveaux de luminosité, port USB intégré, design marbre.",
        "description": "<p>Lampe de chevet tactile LED avec 3 niveaux de luminosité et 3 températures de couleur. Base effet marbre blanc. Port USB intégré pour charger votre téléphone. Ampoule LED 8W intégrée.</p>",
        "category": "luminaires", "store_idx": 2,
        "price": 32000, "compare_price": 42000,
        "discount_type": "fixed", "discount_value": 10000,
        "stock": 35, "is_featured": False, "rating": 4.6, "reviews_count": 198,
        "images": ["lampe_2", "chevet_1"],
        "tags": ["lampe chevet", "LED", "tactile", "luminaires"],
    },
    {
        "name": "Applique Murale Articulée Laiton — Archi",
        "short_description": "Bras articulé 360°, finition laiton brossé, câble apparent.",
        "description": "<p>Applique murale design avec bras articulé 360°. Finition laiton brossé naturel. Câble en tissu tressé avec interrupteur intégré. Parfaite pour la lecture au lit.</p>",
        "category": "luminaires", "store_idx": 2,
        "price": 45000, "compare_price": 58000,
        "discount_type": "percentage", "discount_value": 22,
        "stock": 18, "is_featured": False, "rating": 4.7, "reviews_count": 76,
        "images": ["applique_1", "lampe_1"],
        "tags": ["applique", "laiton", "luminaires"],
    },
    # ── DÉCORATION ────────────────────────────────────────────────────
    {
        "name": "Tapis Berbère Kilim Naturel 150×200",
        "short_description": "Laine pure, motifs géométriques, fabrication artisanale.",
        "description": "<p>Tapis kilim artisanal en pure laine. Motifs géométriques traditionnels berbères en tons naturels. Chaque pièce est unique. Entretien facile, lavable en machine à 30°C.</p>",
        "category": "decoration", "store_idx": 2,
        "price": 85000, "compare_price": 110000,
        "discount_type": "percentage", "discount_value": 22,
        "stock": 12, "is_featured": False, "rating": 4.8, "reviews_count": 95,
        "images": ["deco_tapis", "deco_miroir"],
        "tags": ["tapis", "kilim", "décoration", "artisanal"],
    },
    {
        "name": "Miroir Doré Baroque Ø80cm — Prestige",
        "short_description": "Cadre résine dorée, forme ronde, effet vieilli élégant.",
        "description": "<p>Grand miroir rond avec cadre en résine sculptée finition dorée vieillie. Diamètre 80 cm. Peut s'utiliser posé au sol ou accroché au mur. Poids : 8 kg. Attaches murales incluses.</p>",
        "category": "decoration", "store_idx": 2,
        "price": 45000, "compare_price": 58000,
        "discount_type": "fixed", "discount_value": 13000,
        "stock": 15, "is_featured": False, "rating": 4.7, "reviews_count": 87,
        "images": ["deco_miroir", "deco_vase"],
        "tags": ["miroir", "décoration", "doré"],
    },
    {
        "name": "Tableau Triptyque Abstrait Doré 3×40×120cm",
        "short_description": "Impression sur toile canvas, sous-cadre bois, dorures.",
        "description": "<p>Tableau triptyque 3 panneaux en impression haute résolution sur toile canvas tendue. Dorures à la feuille d'or 24K. Prêt à accrocher, crochets inclus. Format total : 120×120cm.</p>",
        "category": "decoration", "store_idx": 2,
        "price": 28000, "compare_price": 38000,
        "discount_type": "percentage", "discount_value": 26,
        "stock": 20, "is_featured": False, "rating": 4.5, "reviews_count": 143,
        "images": ["deco_tableau", "deco_miroir"],
        "tags": ["tableau", "abstrait", "décoration"],
    },
    {
        "name": "Set 3 Vases Céramique Artisanaux — Terra",
        "short_description": "Argile de Côte d'Ivoire, finition mate, hauteurs 18/25/32cm.",
        "description": "<p>Set de 3 vases en céramique artisanale fabriqués en Côte d'Ivoire. Argile naturelle, finition mate. Formes organiques uniques. Hauteurs : 18, 25 et 32 cm. Produit 100% local.</p>",
        "category": "decoration", "store_idx": 2,
        "price": 15000, "compare_price": 22000,
        "discount_type": "fixed", "discount_value": 7000,
        "stock": 25, "is_featured": True, "rating": 4.9, "reviews_count": 62,
        "images": ["deco_vase", "deco_tableau"],
        "tags": ["vase", "céramique", "artisanal", "local"],
    },
    # ── TABLE À MANGER ────────────────────────────────────────────────
    {
        "name": "Table à Manger Extensible Bois Hêtre 6 à 10 Personnes",
        "short_description": "Extension 60cm, bois massif hêtre, pieds acier laqué blanc.",
        "description": "<p>Table à manger extensible en bois massif hêtre. Se transforme de 6 à 10 couverts grâce au système d'extension papillon. Pieds en acier laqué blanc. L160-220 × P90 × H75 cm.</p>",
        "category": "table-manger", "store_idx": 1,
        "price": 245000, "compare_price": 305000,
        "discount_type": "percentage", "discount_value": 19,
        "stock": 9, "is_featured": True, "rating": 4.8, "reviews_count": 54,
        "images": ["table_m1", "table_m2"],
        "tags": ["table manger", "bois", "extensible"],
    },
    {
        "name": "Chaises Salle à Manger Velours Vert (Lot de 4)",
        "short_description": "Pieds bois chêne, assise velours, dossier capitonné.",
        "description": "<p>Set de 4 chaises design scandinave en velours vert sauge. Pieds en bois de chêne massif. Assise et dossier capitonnés. Faciles d'entretien. Capacité 120 kg par chaise.</p>",
        "category": "table-manger", "store_idx": 1,
        "price": 145000, "compare_price": 188000,
        "discount_type": "fixed", "discount_value": 43000,
        "stock": 14, "is_featured": False, "rating": 4.7, "reviews_count": 83,
        "images": ["chaise_m", "table_m1"],
        "tags": ["chaises", "table manger", "velours", "lot 4"],
    },
    {
        "name": "Buffet Vaisselier Blanc 3 Portes — Hampton",
        "short_description": "Rangements vitrés, portes cerclées doré, dimensions L150cm.",
        "description": "<p>Buffet vaisselier de style hamptons en MDF laqué blanc mat. 3 portes dont 2 à vitre feuilletée. Poignées cerclées laiton doré. Dimensions : L150 × P42 × H195 cm.</p>",
        "category": "table-manger", "store_idx": 1,
        "price": 285000, "compare_price": 345000,
        "discount_type": "percentage", "discount_value": 17,
        "stock": 5, "is_featured": False, "rating": 4.6, "reviews_count": 41,
        "images": ["buffet_1", "table_m2"],
        "tags": ["buffet", "vaisselier", "table manger"],
    },
    # ── CHAISE DE LUXE ─────────────────────────────────────────────────
    {
        "name": "Fauteuil Chester Cuir Véritable Cognac — Royal",
        "short_description": "Cuir pleine fleur, capitons boutons dorés, pieds chêne massif.",
        "description": "<p>Fauteuil Chester traditionnel de prestige en cuir pleine fleur cognac. Capitons à la main avec boutons dorés. Pieds tournés en chêne massif huilé. Rembourrage plumes/mousse HD.</p>",
        "category": "chaise-luxe", "store_idx": 1,
        "price": 345000, "compare_price": 425000,
        "discount_type": "percentage", "discount_value": 18,
        "stock": 6, "is_featured": True, "rating": 4.9, "reviews_count": 36,
        "images": ["chester", "fauteuil_1"],
        "tags": ["chester", "cuir", "fauteuil", "luxe"],
    },
    {
        "name": "Chaise Scandinave Molly Pieds Frêne Naturel",
        "short_description": "Assise coque plastique recyclé, pieds bois de frêne, empilable.",
        "description": "<p>Chaise design scandinave avec assise en polypropylène recyclé disponible en 6 coloris. Pieds en frêne naturel. Empilable jusqu'à 6 chaises. Idéale intérieur/extérieur.</p>",
        "category": "chaise-luxe", "store_idx": 1,
        "price": 48500, "compare_price": 62000,
        "discount_type": "fixed", "discount_value": 13500,
        "stock": 30, "is_featured": False, "rating": 4.6, "reviews_count": 115,
        "images": ["chaise_s", "chester"],
        "tags": ["chaise", "scandinave", "bois"],
    },
    {
        "name": "Pouf Ottoman Rond Velours Bordeaux — Lounge",
        "short_description": "Ø50cm, mousse 40kg/m³, pieds métal doré, repose-pieds ou assise.",
        "description": "<p>Pouf ottoman rond en velours bordeaux. Double usage : repose-pieds ou assise d'appoint (charge max 150 kg). Mousse haute densité 40 kg/m³. Pieds en métal doré. Ø50 × H35 cm.</p>",
        "category": "chaise-luxe", "store_idx": 2,
        "price": 38000, "compare_price": 48000,
        "discount_type": "percentage", "discount_value": 20,
        "stock": 22, "is_featured": False, "rating": 4.7, "reviews_count": 78,
        "images": ["pouf_1", "fauteuil_2"],
        "tags": ["pouf", "ottoman", "velours", "salon"],
    },
    # ── ÉLECTROMÉNAGER ────────────────────────────────────────────────
    {
        "name": "Climatiseur Split Inverter 1.5 CV — FreshAir Pro",
        "short_description": "Énergie A+++, silencieux 19dB, WiFi intégré, télécommande.",
        "description": "<p>Climatiseur split inverter dernière génération. Classe énergétique A+++. Niveau sonore 19 dB (ultra-silencieux). Contrôle WiFi via application smartphone. Auto-nettoyage. Gaz R32 écologique.</p>",
        "category": "electromenager", "store_idx": 2,
        "price": 285000, "compare_price": 350000,
        "discount_type": "percentage", "discount_value": 18,
        "stock": 8, "is_featured": True, "rating": 4.8, "reviews_count": 89,
        "images": ["clim_1", "ventilo_1"],
        "tags": ["climatiseur", "électroménager", "inverter"],
    },
    {
        "name": "Ventilateur de Plafond LED 5 Pales — Cyclone",
        "short_description": "5 pales réversibles, éclairage LED intégré, télécommande.",
        "description": "<p>Ventilateur de plafond 5 pales en bois naturel avec éclairage LED 32W intégré. Moteur DC silencieux 6 vitesses. 3 températures d'éclairage. Télécommande incluse. Ø132 cm.</p>",
        "category": "electromenager", "store_idx": 2,
        "price": 68000, "compare_price": 88000,
        "discount_type": "fixed", "discount_value": 20000,
        "stock": 15, "is_featured": False, "rating": 4.6, "reviews_count": 142,
        "images": ["ventilo_1", "lampe_1"],
        "tags": ["ventilateur", "plafond", "LED", "électroménager"],
    },
    # ── FASHION ──────────────────────────────────────────────────────
    {
        "name": "Peignoir de Bain Luxe Hotel 5 Etoiles - Blanc",
        "short_description": "Éponge 100% coton, 600g/m², broderie dorée, taille S-XXL.",
        "description": "<p>Peignoir de bain de qualité hôtelière en éponge 100% coton. Grammage 600 g/m². Broderie dorée personnalisable. Ceinture et 2 poches. Disponible de S à XXL.</p>",
        "category": "fashion", "store_idx": 0,
        "price": 35000, "compare_price": 45000,
        "discount_type": "percentage", "discount_value": 22,
        "stock": 40, "is_featured": False, "rating": 4.8, "reviews_count": 189,
        "images": ["peignoir", "draps_1"],
        "tags": ["peignoir", "bain", "coton", "fashion"],
    },
    {
        "name": "Pantoufles Mémoire de Forme — Cloud Walk",
        "short_description": "Semelle EVA anti-dérapante, garnissage mousse mémoire, unisexe.",
        "description": "<p>Pantoufles unisexe ultra-confortables avec semelle intérieure en mousse à mémoire de forme qui épouse votre pied. Semelle extérieure EVA anti-dérapante. Lavable en machine.</p>",
        "category": "fashion", "store_idx": 0,
        "price": 12000, "compare_price": 18000,
        "discount_type": "fixed", "discount_value": 6000,
        "stock": 80, "is_featured": False, "rating": 4.7, "reviews_count": 256,
        "images": ["pantoufle", "peignoir"],
        "tags": ["pantoufles", "confort", "fashion"],
    },
    # ── BAGAGES ────────────────────────────────────────────────────────
    {
        "name": "Valise Cabine Rigide 55cm — Voyageur Pro",
        "short_description": "Polycarbonate ultra-léger, 4 roues 360°, verrou TSA.",
        "description": "<p>Valise cabine en polycarbonate 100% léger (2,8 kg). 4 roues doubles pivotantes à 360°. Verrou à combinaison TSA homologué. Intérieur organisé avec sangles et poche zippée. Dimensions : 55×40×20cm.</p>",
        "category": "bagages", "store_idx": 2,
        "price": 65000, "compare_price": 85000,
        "discount_type": "percentage", "discount_value": 23,
        "stock": 25, "is_featured": False, "rating": 4.7, "reviews_count": 134,
        "images": ["valise_1", "valise_2"],
        "tags": ["valise", "cabine", "bagages", "voyage"],
    },
    {
        "name": "Set 3 Valises Polycarbonate — Family Travel",
        "short_description": "S+M+L, même coloris, roues silencieuses, cadenas TSA.",
        "description": "<p>Set complet de 3 valises en polycarbonate (S 55cm + M 65cm + L 75cm). 4 roues doubles silencieuses. Verrous TSA. Poignées télescopiques en aluminium. Disponible en 6 coloris.</p>",
        "category": "bagages", "store_idx": 2,
        "price": 175000, "compare_price": 240000,
        "discount_type": "fixed", "discount_value": 65000,
        "stock": 10, "is_featured": True, "rating": 4.8, "reviews_count": 76,
        "images": ["valise_set", "valise_1"],
        "tags": ["valise", "set", "famille", "bagages"],
    },
    # ── VAISSELLERIE ────────────────────────────────────────────────────
    {
        "name": "Service de Table Complet Porcelaine 24 Pièces — Versailles",
        "short_description": "6 assiettes plates, creuses, dessert + 6 bols, dorures.",
        "description": "<p>Service de table 24 pièces en porcelaine fine blanche avec filets dorés. Pour 6 personnes : assiettes plates + creuses + dessert + bols. Passe au lave-vaisselle et micro-ondes. Boîte cadeau incluse.</p>",
        "category": "vaissellerie", "store_idx": 1,
        "price": 88000, "compare_price": 115000,
        "discount_type": "percentage", "discount_value": 23,
        "stock": 18, "is_featured": False, "rating": 4.8, "reviews_count": 67,
        "images": ["vaisselle_1", "vaisselle_2"],
        "tags": ["vaisselle", "porcelaine", "service table"],
    },
    {
        "name": "Set 6 Verres à Pied Cristal Bohème — Élégance",
        "short_description": "Verre soufflé, 45cl, bord anti-éclats, coffret cadeau.",
        "description": "<p>Set de 6 verres à pied en cristal soufflé de Bohème. Capacité 45 cl. Taille 24 cm. Traitement bord renforcé anti-éclats. Lavable à la main. Coffret cadeau inclus.</p>",
        "category": "vaissellerie", "store_idx": 1,
        "price": 38000, "compare_price": 50000,
        "discount_type": "fixed", "discount_value": 12000,
        "stock": 30, "is_featured": False, "rating": 4.9, "reviews_count": 112,
        "images": ["verres", "vaisselle_1"],
        "tags": ["verres", "cristal", "vaissellerie"],
    },
    # ── PACK DOOYA ─────────────────────────────────────────────────────
    {
        "name": "Pack Chambre Premium — Dooya Signature",
        "short_description": "Matelas 160×200 + Oreiller×2 + Parure satin + Housse couette.",
        "description": "<p>Notre pack chambre le plus populaire réunit les essentiels pour une chambre 5 étoiles :</p><ul><li>1 Matelas orthopédique 160×200 (valeur 189 000 FCFA)</li><li>2 Oreillers mémoire de forme (valeur 37 000 FCFA)</li><li>1 Parure satin 160×200 (valeur 55 000 FCFA)</li><li>1 Housse de couette bambou 260×240 (valeur 38 500 FCFA)</li></ul><p><strong>Valeur totale : 319 500 FCFA — Vous économisez 95 500 FCFA !</strong></p>",
        "category": "pack-dooya", "store_idx": 0,
        "price": 224000, "compare_price": 319500,
        "discount_type": "percentage", "discount_value": 30,
        "stock": 15, "is_featured": True, "rating": 4.9, "reviews_count": 87,
        "images": ["pack_ch", "matelas_1", "oreillers_1"],
        "tags": ["pack", "chambre", "literie", "dooya", "offre"],
    },
    {
        "name": "Pack Salon Complet — Dooya Living",
        "short_description": "Canapé 3P + Table basse + Tapis + Lampadaire, tout assorti.",
        "description": "<p>Transformez votre salon avec notre pack coordonné :</p><ul><li>1 Canapé 3 places velours (valeur 285 000 FCFA)</li><li>1 Table basse verre/marbre (valeur 98 000 FCFA)</li><li>1 Tapis berbère 150×200 (valeur 85 000 FCFA)</li><li>1 Lampadaire industriel (valeur 78 000 FCFA)</li></ul><p><strong>Valeur totale : 546 000 FCFA — Vous économisez 146 000 FCFA !</strong></p>",
        "category": "pack-dooya", "store_idx": 1,
        "price": 400000, "compare_price": 546000,
        "discount_type": "fixed", "discount_value": 146000,
        "stock": 5, "is_featured": True, "rating": 4.8, "reviews_count": 31,
        "images": ["pack_sal", "canape_1", "deco_tapis"],
        "tags": ["pack", "salon", "living", "dooya", "offre"],
    },
]


class Command(BaseCommand):
    help = "Insère les données de démonstration Dooya avec images réelles"

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Vide les tables avant d'insérer")
        parser.add_argument("--no-images", action="store_true", help="Ne télécharge pas les images (plus rapide)")

    def handle(self, *args, **options):
        from apps.users.models import User
        from apps.vendors.models import Store
        from apps.categories.models import Category, Attribute, AttributeValue
        from apps.products.models import Product, ProductImage, ProductVariant, Tag
        from apps.commissions.models import CommissionRule

        flush      = options["flush"]
        no_images  = options["no_images"]

        if flush:
            self.stdout.write(self.style.WARNING("[WARN] Flush demande -- suppression des donnees existantes..."))
            # Flush all seeded data in reverse dependency order
            try:
                from apps.live.models import LiveSession
                LiveSession.objects.all().delete()
            except Exception: pass
            try:
                from apps.chat.models import Conversation
                Conversation.objects.all().delete()
            except Exception: pass
            try:
                from apps.reports.models import Report
                Report.objects.all().delete()
            except Exception: pass
            try:
                from apps.quality.models import ProductReturn
                ProductReturn.objects.all().delete()
            except Exception: pass
            try:
                from apps.support.models import Dispute, SupportTicket, FAQ, FAQCategory
                Dispute.objects.all().delete()
                SupportTicket.objects.all().delete()
                FAQ.objects.all().delete()
                FAQCategory.objects.all().delete()
            except Exception: pass
            try:
                from apps.suppliers.models import Supplier
                Supplier.objects.all().delete()
            except Exception: pass
            try:
                from apps.deliveries.models import Delivery
                Delivery.objects.all().delete()
            except Exception: pass
            try:
                from apps.inventory.models import StockMovement, StockLocation, Warehouse
                StockMovement.objects.all().delete()
                StockLocation.objects.all().delete()
                Warehouse.objects.all().delete()
            except Exception: pass
            try:
                from apps.commissions.models import Commission, VendorPayout
                Commission.objects.all().delete()
                VendorPayout.objects.all().delete()
            except Exception: pass
            try:
                from apps.payments.models import Refund, Payment
                Refund.objects.all().delete()
                Payment.objects.all().delete()
            except Exception: pass
            try:
                from apps.wallets.models import WithdrawalRequest, Wallet
                WithdrawalRequest.objects.all().delete()
                Wallet.objects.all().delete()
            except Exception: pass
            try:
                from apps.affiliate.models import AffiliatePayout, AffiliateProfile
                AffiliatePayout.objects.all().delete()
                AffiliateProfile.objects.all().delete()
            except Exception: pass
            try:
                from apps.marketing.models import AbandonedCartReminder, Campaign
                AbandonedCartReminder.objects.all().delete()
                Campaign.objects.all().delete()
            except Exception: pass
            try:
                from apps.cms.models import BlogPost, BlogCategory, Coupon, Page
                BlogPost.objects.all().delete()
                BlogCategory.objects.all().delete()
                Coupon.objects.all().delete()
                Page.objects.all().delete()
            except Exception: pass
            try:
                from apps.reviews.models import ProductReview
                ProductReview.objects.all().delete()
            except Exception: pass
            try:
                from apps.orders.models import OrderItem, Order
                OrderItem.objects.all().delete()
                Order.objects.all().delete()
            except Exception: pass
            ProductImage.objects.all().delete()
            ProductVariant.objects.all().delete()
            Product.objects.all().delete()
            Store.objects.all().delete()
            Category.objects.all().delete()
            Tag.objects.all().delete()
            AttributeValue.objects.all().delete()
            Attribute.objects.all().delete()
            CommissionRule.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS("[OK] Tables videes"))

        with transaction.atomic():
            # ── 1. Superuser ───────────────────────────────────────────────
            admin, created = User.objects.get_or_create(
                email="admin@dooya.ci",
                defaults={
                    "username": "admin_dooya",
                    "first_name": "Admin",
                    "last_name": "Dooya",
                    "role": "admin",
                    "is_staff": True,
                    "is_superuser": True,
                    "is_email_verified": True,
                }
            )
            if created:
                admin.set_password("dooya2025!")
                admin.save()
                self.stdout.write(self.style.SUCCESS("[OK] Superuser  admin@dooya.ci  /  dooya2025!"))
            else:
                self.stdout.write("[-] Superuser existant (ignore)")

            # ── 2. Client de test ──────────────────────────────────────────
            client, created = User.objects.get_or_create(
                email="client@dooya.ci",
                defaults={
                    "username": "client_test",
                    "first_name": "Yao",
                    "last_name": "Kouassi",
                    "role": "customer",
                    "is_email_verified": True,
                }
            )
            if created:
                client.set_password("client2025!")
                client.save()
                self.stdout.write(self.style.SUCCESS("[OK] Client       client@dooya.ci  /  client2025!"))

            # ── 3. Vendeurs & Boutiques ────────────────────────────────────
            stores = []
            for v in VENDORS:
                vendor, vc = User.objects.get_or_create(
                    email=v["email"],
                    defaults={
                        "username": v["username"],
                        "first_name": v["first_name"],
                        "last_name": v["last_name"],
                        "role": "vendor",
                        "is_email_verified": True,
                    }
                )
                if vc:
                    vendor.set_password("vendor2025!")
                    vendor.save()

                store, sc = Store.objects.get_or_create(
                    slug=v["store_slug"],
                    defaults={
                        "user": vendor,
                        "name": v["store"],
                        "description": f"Boutique officielle {v['store']} sur Dooya",
                        "city": "Abidjan",
                        "country": "Côte d'Ivoire",
                        "status": "active",
                        "is_certified": True,
                        "is_featured": True,
                        "commission_rate": 0.10,
                    }
                )
                stores.append(store)
                marker = "[OK]" if sc else "[-]"
                self.stdout.write(f"{marker} Boutique : {store.name}")

            # ── 4. Catégories MPTT ─────────────────────────────────────────
            cat_map = {}

            def make_cat(data, parent=None):
                slug = data["slug"]
                cat, _ = Category.objects.get_or_create(
                    slug=slug,
                    defaults={
                        "name": data["name"],
                        "parent": parent,
                        "icon": data.get("icon", ""),
                        "order": data.get("order", 0),
                        "is_active": True,
                    }
                )
                cat_map[slug] = cat
                for child in data.get("children", []):
                    make_cat(child, parent=cat)

            for c in CATEGORIES:
                make_cat(c)

            Category.objects.rebuild()
            self.stdout.write(self.style.SUCCESS(f"[OK] {len(cat_map)} categories creees"))

            # ── 5. Tags ────────────────────────────────────────────────────
            tag_map = {}

            def get_or_create_tag(name):
                s = slugify(name)
                if s not in tag_map:
                    t, _ = Tag.objects.get_or_create(slug=s, defaults={"name": name})
                    tag_map[s] = t
                return tag_map[s]

            # ── 6. Produits ────────────────────────────────────────────────
            created_count  = 0
            image_ok_count = 0
            image_fail     = 0

            for idx, pdata in enumerate(PRODUCTS):
                cat     = cat_map.get(pdata["category"])
                store   = stores[pdata["store_idx"]]
                slug    = slugify(pdata["name"])[:300]
                sku     = f"DOY-{idx+1:04d}"

                # Éviter doublons
                if Product.objects.filter(slug=slug).exists():
                    self.stdout.write(f"[-] Produit existant : {pdata['name'][:50]}")
                    continue

                # Remise temporisée
                discount_start = None
                discount_end   = None
                if pdata.get("discount_type"):
                    discount_start = timezone.now() - timedelta(days=1)
                    discount_end   = timezone.now() + timedelta(days=90)

                product = Product.objects.create(
                    store=store,
                    category=cat,
                    name=pdata["name"],
                    slug=slug,
                    description=pdata.get("description", ""),
                    short_description=pdata.get("short_description", ""),
                    price=pdata["price"],
                    compare_price=pdata.get("compare_price"),
                    discount_type=pdata.get("discount_type"),
                    discount_value=pdata.get("discount_value"),
                    discount_start=discount_start,
                    discount_end=discount_end,
                    sku=sku,
                    stock=pdata["stock"],
                    is_active=True,
                    is_featured=pdata.get("is_featured", False),
                    rating=pdata.get("rating", 0),
                    reviews_count=pdata.get("reviews_count", 0),
                    views_count=pdata.get("reviews_count", 0) * 12,
                )

                # Tags
                for tag_name in pdata.get("tags", []):
                    product.tags.add(get_or_create_tag(tag_name))

                created_count += 1

                # Images
                if not no_images:
                    for order, img_key in enumerate(pdata.get("images", [])):
                        url  = img_url(img_key)
                        fname = f"{product.slug}_{order}.jpg"
                        self.stdout.write(f"  >> Telechargement {fname}...", ending="\r")
                        img_file = download_image(url, fname)
                        if img_file:
                            pi = ProductImage(
                                product=product,
                                is_primary=(order == 0),
                                order=order,
                                alt_text=product.name,
                            )
                            pi.image.save(fname, img_file, save=True)
                            image_ok_count += 1
                        else:
                            image_fail += 1
                            self.stdout.write(
                                self.style.WARNING(f"  [WARN] Image non telechargee : {img_key}")
                            )
                        # Max 2 images par produit pour la démo
                        if order >= 1:
                            break

                self.stdout.write(
                    self.style.SUCCESS(f"  [OK] [{idx+1:02d}/{len(PRODUCTS)}] {product.name[:55]}")
                )

            # ── 7. Attributs & Valeurs ─────────────────────────────────────
            ATTRIBUTES_DATA = [
                {"name": "Taille", "slug": "taille", "type": "select", "is_filterable": True, "values": [
                    "XS", "S", "M", "L", "XL", "XXL",
                    "90×190", "140×190", "160×200", "180×200",
                ]},
                {"name": "Couleur", "slug": "couleur", "type": "color", "is_filterable": True, "values": [
                    {"value": "Blanc",       "color_hex": "#FFFFFF"},
                    {"value": "Noir",        "color_hex": "#1A1A1A"},
                    {"value": "Gris",        "color_hex": "#808080"},
                    {"value": "Beige",       "color_hex": "#C9B99A"},
                    {"value": "Bleu nuit",   "color_hex": "#1C2B4A"},
                    {"value": "Vert sauge",  "color_hex": "#8DAA91"},
                    {"value": "Bordeaux",    "color_hex": "#7D1128"},
                    {"value": "Cognac",      "color_hex": "#9A4700"},
                ]},
                {"name": "Matière", "slug": "matiere", "type": "select", "is_filterable": True, "values": [
                    "Coton 100%", "Velours", "Cuir véritable", "Cuir PU",
                    "Bois massif", "Métal", "Verre trempé", "Polyester",
                ]},
                {"name": "Fermeté", "slug": "fermete", "type": "select", "is_filterable": True, "values": [
                    "Très ferme", "Ferme", "Médium-ferme", "Médium", "Médium-doux", "Doux",
                ]},
                {"name": "Dimensions", "slug": "dimensions", "type": "text", "is_filterable": False, "values": []},
            ]

            for adata in ATTRIBUTES_DATA:
                attr, _ = Attribute.objects.get_or_create(
                    slug=adata["slug"],
                    defaults={
                        "name": adata["name"],
                        "type": adata["type"],
                        "is_filterable": adata["is_filterable"],
                    }
                )
                for i, val in enumerate(adata["values"]):
                    if isinstance(val, dict):
                        AttributeValue.objects.get_or_create(
                            attribute=attr, value=val["value"],
                            defaults={"color_hex": val.get("color_hex", ""), "order": i}
                        )
                    else:
                        AttributeValue.objects.get_or_create(
                            attribute=attr, value=val,
                            defaults={"order": i}
                        )
            self.stdout.write(self.style.SUCCESS(f"[OK] {len(ATTRIBUTES_DATA)} attributs crees"))

            # ── 8. Variantes produits ──────────────────────────────────────
            VARIANTS_DATA = [
                # Matelas: variantes par taille
                {"product_slug": "matelas-orthopedique-premium-160x200",
                 "variants": [
                     {"name": "90×190 cm", "price": 139000, "stock": 20, "attributes": {"Taille": "90×190"}},
                     {"name": "140×190 cm", "price": 159000, "stock": 15, "attributes": {"Taille": "140×190"}},
                     {"name": "160×200 cm", "price": 189000, "stock": 25, "attributes": {"Taille": "160×200"}},
                     {"name": "180×200 cm", "price": 215000, "stock": 10, "attributes": {"Taille": "180×200"}},
                 ]},
                # Canapé: variantes par couleur
                {"product_slug": "canape-3-places-velours-gris-anthracite",
                 "variants": [
                     {"name": "Velours Gris Anthracite", "price": 285000, "stock": 8, "attributes": {"Couleur": "Gris", "Matière": "Velours"}},
                     {"name": "Velours Bleu Nuit", "price": 285000, "stock": 5, "attributes": {"Couleur": "Bleu nuit", "Matière": "Velours"}},
                     {"name": "Velours Bordeaux", "price": 295000, "stock": 4, "attributes": {"Couleur": "Bordeaux", "Matière": "Velours"}},
                 ]},
                # Chaise scandinave: variantes par couleur
                {"product_slug": "chaise-scandinave-molly-pieds-frene-naturel",
                 "variants": [
                     {"name": "Blanc — Frêne", "price": 48500, "stock": 30, "attributes": {"Couleur": "Blanc"}},
                     {"name": "Noir — Frêne", "price": 48500, "stock": 25, "attributes": {"Couleur": "Noir"}},
                     {"name": "Vert sauge — Frêne", "price": 51000, "stock": 15, "attributes": {"Couleur": "Vert sauge"}},
                 ]},
                # Peignoir: variantes par taille
                {"product_slug": "peignoir-de-bain-luxe-hotel-5-etoiles-blanc",
                 "variants": [
                     {"name": "Taille S", "price": 35000, "stock": 20, "attributes": {"Taille": "S"}},
                     {"name": "Taille M", "price": 35000, "stock": 30, "attributes": {"Taille": "M"}},
                     {"name": "Taille L", "price": 35000, "stock": 25, "attributes": {"Taille": "L"}},
                     {"name": "Taille XL", "price": 37000, "stock": 15, "attributes": {"Taille": "XL"}},
                     {"name": "Taille XXL", "price": 38000, "stock": 10, "attributes": {"Taille": "XXL"}},
                 ]},
                # Valise: variantes de couleur
                {"product_slug": "valise-cabine-rigide-55cm-voyageur-pro",
                 "variants": [
                     {"name": "Noir", "price": 65000, "stock": 15, "attributes": {"Couleur": "Noir"}},
                     {"name": "Blanc", "price": 65000, "stock": 12, "attributes": {"Couleur": "Blanc"}},
                     {"name": "Bleu nuit", "price": 68000, "stock": 8, "attributes": {"Couleur": "Bleu nuit"}},
                 ]},
            ]

            variant_count = 0
            for vdata in VARIANTS_DATA:
                product = Product.objects.filter(slug__startswith=vdata["product_slug"][:40]).first()
                if not product:
                    continue
                for i, v in enumerate(vdata["variants"]):
                    if not ProductVariant.objects.filter(product=product, name=v["name"]).exists():
                        ProductVariant.objects.create(
                            product=product,
                            name=v["name"],
                            sku=f"{product.sku}-V{i+1}",
                            price=v["price"],
                            stock=v["stock"],
                            attributes=v.get("attributes", {}),
                        )
                        variant_count += 1
            self.stdout.write(self.style.SUCCESS(f"[OK] {variant_count} variantes creees"))

            # ── 9. Règles de commission (taux global si aucune boutique) ──
            RULES = [
                {"rate": 0.10, "flat_fee": 0,    "min_order_amount": 0,      "note": "Taux standard 10%",       "is_active": True},
                {"rate": 0.08, "flat_fee": 0,    "min_order_amount": 100000, "note": "Premium vendeurs 8%",      "is_active": True},
                {"rate": 0.12, "flat_fee": 500,  "min_order_amount": 0,      "note": "Nouveaux vendeurs 12%",    "is_active": False},
            ]
            rule_count = 0
            for r in RULES:
                obj, created = CommissionRule.objects.get_or_create(
                    store=None, category=None, note=r["note"],
                    defaults={"rate": r["rate"], "flat_fee": r["flat_fee"],
                              "min_order_amount": r["min_order_amount"], "is_active": r["is_active"]}
                )
                if created:
                    rule_count += 1
            self.stdout.write(self.style.SUCCESS(f"[OK] {rule_count} regles de commission creees"))

            # ── 10. Commandes de démo ──────────────────────────────────────
            try:
                from apps.orders.models import Order, OrderItem
                from decimal import Decimal
                import random

                all_products = list(Product.objects.filter(is_active=True)[:20])
                customers = list(User.objects.filter(role='customer'))
                if not customers:
                    customers = [client]

                statuses = ['pending', 'processing', 'shipped', 'delivered', 'delivered', 'delivered']
                pay_statuses = ['pending', 'paid', 'paid', 'paid', 'paid', 'paid']

                order_count = 0
                for i in range(15):
                    if Order.objects.count() >= 20:
                        break
                    customer = random.choice(customers)
                    status = statuses[i % len(statuses)]
                    pay_status = pay_statuses[i % len(pay_statuses)]
                    total = Decimal('0')
                    items_data = random.sample(all_products, min(3, len(all_products)))
                    order_items = []
                    for p in items_data:
                        qty = random.randint(1, 3)
                        price = p.price
                        order_items.append((p, qty, price))
                        total += price * qty

                    order = Order.objects.create(
                        user=customer,
                        status=status,
                        payment_status=pay_status,
                        total_amount=total,
                        shipping_address={"city": "Abidjan", "address": "Plateau, Rue des Jardins", "country": "CI"},
                        created_at=timezone.now() - timedelta(days=random.randint(1, 60)),
                    )
                    for p, qty, price in order_items:
                        OrderItem.objects.create(
                            order=order,
                            product=p,
                            store=p.store,
                            product_name=p.name,
                            quantity=qty,
                            unit_price=price,
                            total_price=price * qty,
                        )
                    order_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {order_count} commandes creees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Commandes ignorees : {e}"))

            # ── 11. Avis produits ──────────────────────────────────────────
            try:
                from apps.reviews.models import ProductReview
                import random

                REVIEW_TEXTS = [
                    "Excellent produit, je suis très satisfait de la qualité.",
                    "Livraison rapide et emballage soigné. Conforme à la description.",
                    "Très bon rapport qualité/prix, je recommande vivement.",
                    "Produit de qualité supérieure. Ma famille adore !",
                    "Parfait pour notre intérieur. Montage facile et solide.",
                    "Dépasse mes attentes. Service client très réactif.",
                    "Design élégant et matériaux de qualité. Parfait.",
                    "Produit reçu rapidement, emballé parfaitement. Je recommande.",
                ]
                reviewers = list(User.objects.filter(role='customer'))
                if not reviewers:
                    reviewers = [client]
                featured_products = list(Product.objects.filter(is_featured=True)[:10])

                review_count = 0
                for product in featured_products:
                    for j in range(min(3, len(reviewers))):
                        reviewer = reviewers[j % len(reviewers)]
                        if not ProductReview.objects.filter(product=product, user=reviewer).exists():
                            ProductReview.objects.create(
                                product=product,
                                user=reviewer,
                                rating=random.choice([4, 4, 5, 5, 5]),
                                title="Super produit !",
                                body=random.choice(REVIEW_TEXTS),
                                is_approved=True,
                            )
                            review_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {review_count} avis crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Avis ignores : {e}"))

            # ── 12. Paiements ──────────────────────────────────────────────
            try:
                from apps.payments.models import Payment, Refund
                from apps.orders.models import Order
                METHODS = ['orange_money', 'mtn_money', 'wave', 'visa']
                GATEWAYS = ['cinetpay', 'paydunya', 'flutterwave']
                paid_orders = list(Order.objects.filter(payment_status='paid')[:10])
                pay_count = 0
                for order in paid_orders:
                    if not order.payments.exists():
                        Payment.objects.create(
                            order=order,
                            amount=order.total_amount,
                            method=random.choice(METHODS),
                            gateway=random.choice(GATEWAYS),
                            status='success',
                            paid_at=order.created_at + timedelta(minutes=random.randint(1, 30)),
                        )
                        pay_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {pay_count} paiements crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Paiements ignores : {e}"))

            # ── 13. Remboursements ─────────────────────────────────────────
            try:
                from apps.payments.models import Payment, Refund
                paid_payments = list(Payment.objects.filter(status='success')[:3])
                ref_count = 0
                REFUND_REASONS = [
                    "Produit reçu endommagé",
                    "Article non conforme à la description",
                    "Double facturation",
                ]
                for pay in paid_payments:
                    if not pay.refunds.exists():
                        Refund.objects.create(
                            payment=pay,
                            amount=pay.amount * Decimal('0.5'),
                            reason=random.choice(REFUND_REASONS),
                            status=random.choice(['pending', 'approved', 'processed']),
                        )
                        ref_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {ref_count} remboursements crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Remboursements ignores : {e}"))

            # ── 14. Paniers abandonnés ─────────────────────────────────────
            try:
                from apps.marketing.models import AbandonedCartReminder
                from apps.cart.models import Cart
                customers = list(User.objects.filter(role='customer'))
                ab_count = 0
                for u in customers[:4]:
                    cart, _ = Cart.objects.get_or_create(user=u)
                    if not AbandonedCartReminder.objects.filter(cart=cart, user=u).exists():
                        AbandonedCartReminder.objects.create(
                            cart=cart,
                            user=u,
                            status=random.choice(['pending', 'sent', 'converted']),
                            reminder_count=random.randint(1, 3),
                            cart_total=Decimal(random.randint(25000, 350000)),
                        )
                        ab_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {ab_count} paniers abandonnes crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Paniers abandonnes ignores : {e}"))

            # ── 15. Wallets + Retraits ─────────────────────────────────────
            try:
                from apps.wallets.models import Wallet, WithdrawalRequest
                w_count = 0
                for u in list(User.objects.filter(role__in=['vendor', 'customer'])[:6]):
                    wallet, created = Wallet.objects.get_or_create(user=u)
                    if created:
                        wallet.balance = Decimal(random.randint(50000, 500000))
                        wallet.save()
                        w_count += 1
                vendor_wallets = list(Wallet.objects.filter(user__role='vendor'))
                wd_count = 0
                METHODS_W = ['orange_money', 'mtn_money', 'wave', 'bank']
                for wallet in vendor_wallets[:3]:
                    if wallet.balance > 50000 and not wallet.withdrawal_requests.filter(status='pending').exists():
                        WithdrawalRequest.objects.create(
                            wallet=wallet,
                            amount=Decimal(random.randint(50000, 200000)),
                            method=random.choice(METHODS_W),
                            account_number=f'225{random.randint(10000000, 99999999)}',
                            account_name=wallet.user.get_full_name() or wallet.user.email,
                            status=random.choice(['pending', 'approved', 'processed']),
                        )
                        wd_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {w_count} wallets, {wd_count} retraits crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Wallets/Retraits ignores : {e}"))

            # ── 16. Affiliés ───────────────────────────────────────────────
            try:
                from apps.affiliate.models import AffiliateProfile, AffiliatePayout
                aff_count = 0
                payout_count = 0
                for u in list(User.objects.filter(role='customer')[:3]):
                    profile, created = AffiliateProfile.objects.get_or_create(
                        user=u,
                        defaults={
                            'commission_rate': Decimal('0.05'),
                            'total_earnings': Decimal(random.randint(5000, 80000)),
                            'total_clicks': random.randint(20, 500),
                            'total_conversions': random.randint(2, 30),
                            'is_active': True,
                        }
                    )
                    if created:
                        aff_count += 1
                        AffiliatePayout.objects.create(
                            affiliate=profile,
                            amount=profile.total_earnings * Decimal('0.6'),
                            method='orange_money',
                            account_number=f'225{random.randint(10000000, 99999999)}',
                            status=random.choice(['pending', 'processed']),
                        )
                        payout_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {aff_count} profils affilies, {payout_count} paiements affilies"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Affilies ignores : {e}"))

            # ── 17. Pages CMS ──────────────────────────────────────────────
            try:
                from apps.cms.models import Page
                PAGES = [
                    {"title": "À propos de Dooya", "slug": "a-propos",
                     "content": "<h1>À propos de Dooya</h1><p>Dooya est la première marketplace ivoirienne dédiée à l'ameublement, la décoration et l'équipement de la maison. Fondée en 2023, notre mission est de rendre accessible les plus belles pièces pour votre intérieur au meilleur prix.</p><p>Nous travaillons avec des vendeurs locaux certifiés pour vous garantir qualité et authenticité.</p>"},
                    {"title": "Conditions Générales de Vente", "slug": "conditions-generales-vente",
                     "content": "<h1>CGV</h1><p>En passant commande sur Dooya, vous acceptez les présentes conditions générales de vente. Les prix sont indiqués en FCFA TTC. La livraison est assurée sous 2 à 7 jours ouvrés selon votre localisation.</p>"},
                    {"title": "Politique de Confidentialité", "slug": "politique-confidentialite",
                     "content": "<h1>Politique de confidentialité</h1><p>Dooya s'engage à protéger vos données personnelles conformément aux lois en vigueur. Vos données ne seront jamais cédées à des tiers sans votre consentement explicite.</p>"},
                    {"title": "Politique de Retour", "slug": "politique-retour",
                     "content": "<h1>Politique de retour</h1><p>Vous disposez de 14 jours après réception pour retourner un article non conforme ou endommagé. Le remboursement est effectué sous 5 jours ouvrés sur votre moyen de paiement d'origine.</p>"},
                    {"title": "Comment Vendre sur Dooya", "slug": "vendre-sur-dooya",
                     "content": "<h1>Devenez vendeur Dooya</h1><p>Rejoignez notre réseau de vendeurs certifiés. Créez votre boutique gratuitement, listez vos produits et commencez à vendre à des milliers de clients en Côte d'Ivoire.</p>"},
                ]
                page_count = 0
                for p in PAGES:
                    _, created = Page.objects.get_or_create(slug=p['slug'], defaults={
                        'title': p['title'], 'content': p['content'], 'is_published': True
                    })
                    if created:
                        page_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {page_count} pages CMS creees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Pages CMS ignorees : {e}"))

            # ── 18. Blog ───────────────────────────────────────────────────
            try:
                from apps.cms.models import BlogCategory, BlogPost
                BLOG_CATS = [
                    {"name": "Décoration", "slug": "decoration-interieure"},
                    {"name": "Conseils Literie", "slug": "conseils-literie"},
                    {"name": "Tendances", "slug": "tendances-maison"},
                    {"name": "Guides d'achat", "slug": "guides-achat"},
                ]
                blog_cats = {}
                for bc in BLOG_CATS:
                    obj, _ = BlogCategory.objects.get_or_create(slug=bc['slug'], defaults={'name': bc['name']})
                    blog_cats[bc['slug']] = obj

                POSTS = [
                    {"title": "10 idées déco pour transformer votre salon en 2025",
                     "slug": "10-idees-deco-salon-2025",
                     "cat": "decoration-interieure",
                     "excerpt": "Découvrez les tendances décoration qui feront de votre salon un espace unique et chaleureux cette année.",
                     "content": "<p>La décoration intérieure évolue chaque année. En 2025, les tendances se tournent vers des matières naturelles, des teintes terreuses et un mélange de styles modernes et authentiques.</p><h2>1. Les couleurs terreuses</h2><p>Ocre, terracotta, vert sauge... Ces nuances réchauffent l'atmosphère et s'accordent avec les matériaux naturels.</p><h2>2. Le rotin et l'osier</h2><p>Le mobilier en rotin fait son grand retour, apportant légèreté et élégance naturelle.</p>"},
                    {"title": "Comment choisir son matelas selon son morphotype",
                     "slug": "choisir-matelas-morphotype",
                     "cat": "conseils-literie",
                     "excerpt": "Ferme, médium ou doux ? Notre guide complet pour choisir le matelas parfait selon votre poids et votre position de sommeil.",
                     "content": "<p>Le choix d'un matelas est une décision importante qui impacte directement la qualité de votre sommeil et votre santé dorsale.</p><h2>Pour les dormeurs légers (-60 kg)</h2><p>Privilégiez un matelas médium à doux qui épousera vos courbes sans vous faire 'couler'.</p><h2>Pour les dormeurs lourds (+90 kg)</h2><p>Un matelas ferme à très ferme assurera le soutien nécessaire sur le long terme.</p>"},
                    {"title": "5 façons d'illuminer votre intérieur avec les bons luminaires",
                     "slug": "5-facons-illuminer-interieur-luminaires",
                     "cat": "decoration-interieure",
                     "excerpt": "L'éclairage est souvent négligé dans la déco. Pourtant, il change tout ! Nos conseils pour bien choisir vos luminaires.",
                     "content": "<p>Un bon éclairage peut complètement transformer l'ambiance d'une pièce. Voici nos 5 conseils essentiels.</p>"},
                    {"title": "Tendances meubles 2025 : ce qui va révolutionner vos espaces",
                     "slug": "tendances-meubles-2025",
                     "cat": "tendances-maison",
                     "excerpt": "Minimalisme japonais, courbes organiques, matériaux durables... Le mobilier 2025 mise sur l'authenticité.",
                     "content": "<p>Le design mobilier 2025 est marqué par un retour à l'essentiel, avec des formes épurées et des matériaux nobles et durables.</p>"},
                    {"title": "Guide d'achat : canapé — tous les critères à vérifier",
                     "slug": "guide-achat-canape",
                     "cat": "guides-achat",
                     "excerpt": "Taille, tissu, structure... Notre checklist complète avant d'acheter votre prochain canapé.",
                     "content": "<p>Acheter un canapé est un investissement important. Voici les points essentiels à vérifier avant de passer commande.</p>"},
                ]
                post_count = 0
                for p in POSTS:
                    if not BlogPost.objects.filter(slug=p['slug']).exists():
                        BlogPost.objects.create(
                            title=p['title'], slug=p['slug'],
                            content=p['content'], excerpt=p['excerpt'],
                            category=blog_cats.get(p['cat']),
                            author=admin,
                            is_published=True,
                            published_at=timezone.now() - timedelta(days=random.randint(1, 90)),
                            views_count=random.randint(50, 2000),
                        )
                        post_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {post_count} articles blog crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Blog ignore : {e}"))

            # ── 19. Coupons ────────────────────────────────────────────────
            try:
                from apps.cms.models import Coupon
                COUPONS = [
                    {"code": "BIENVENUE10", "type": "percentage", "value": 10, "min_order_amount": 50000, "usage_limit": 100, "days": 90},
                    {"code": "DOOYA2025",   "type": "fixed",      "value": 15000, "min_order_amount": 100000, "usage_limit": 50, "days": 30},
                    {"code": "FLASH20",     "type": "percentage", "value": 20, "min_order_amount": 80000, "usage_limit": 30, "days": 7},
                    {"code": "LITERIE15",   "type": "percentage", "value": 15, "min_order_amount": 60000, "usage_limit": 200, "days": 60},
                    {"code": "SALON30K",    "type": "fixed",      "value": 30000, "min_order_amount": 200000, "usage_limit": 20, "days": 14},
                ]
                coup_count = 0
                for c in COUPONS:
                    _, created = Coupon.objects.get_or_create(code=c['code'], defaults={
                        'type': c['type'], 'value': Decimal(str(c['value'])),
                        'min_order_amount': Decimal(str(c['min_order_amount'])),
                        'usage_limit': c['usage_limit'],
                        'used_count': random.randint(0, c['usage_limit'] // 3),
                        'is_active': True,
                        'valid_from': timezone.now() - timedelta(days=1),
                        'valid_until': timezone.now() + timedelta(days=c['days']),
                    })
                    if created:
                        coup_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {coup_count} coupons crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Coupons ignores : {e}"))

            # ── 20. Campagnes email ────────────────────────────────────────
            try:
                from apps.marketing.models import Campaign
                CAMPAIGNS = [
                    {"name": "Bienvenue sur Dooya", "channel": "email", "status": "sent",
                     "subject": "Bienvenue ! Votre code promo -10%",
                     "content": "<p>Merci de nous rejoindre ! Profitez de 10% de réduction sur votre première commande avec le code BIENVENUE10.</p>",
                     "audience": "new", "total_recipients": 145, "sent_count": 142, "opened_count": 89, "clicked_count": 34},
                    {"name": "Soldes été 2025", "channel": "email", "status": "sent",
                     "subject": "Jusqu'à -30% sur la literie et l'ameublement",
                     "content": "<p>Les soldes d'été ont commencé ! Profitez de remises exceptionnelles sur notre sélection premium.</p>",
                     "audience": "customers", "total_recipients": 312, "sent_count": 308, "opened_count": 198, "clicked_count": 87},
                    {"name": "Relance clients inactifs", "channel": "email", "status": "sent",
                     "subject": "Vous nous manquez ! 15 000 FCFA vous attendent",
                     "content": "<p>Cela fait un moment qu'on ne vous a pas vu ! Revenez et profitez d'un bon d'achat de 15 000 FCFA.</p>",
                     "audience": "inactive", "total_recipients": 78, "sent_count": 75, "opened_count": 32, "clicked_count": 12},
                    {"name": "Nouveautés Salon Automne", "channel": "email", "status": "scheduled",
                     "subject": "Découvrez notre nouvelle collection salon",
                     "content": "<p>Notre collection automne est arrivée ! Canapés, tables basses et fauteuils de luxe vous attendent.</p>",
                     "audience": "all", "total_recipients": 0, "sent_count": 0, "opened_count": 0, "clicked_count": 0},
                ]
                camp_count = 0
                for c in CAMPAIGNS:
                    _, created = Campaign.objects.get_or_create(name=c['name'], defaults={
                        'channel': c['channel'], 'status': c['status'],
                        'subject': c['subject'], 'content': c['content'],
                        'audience': c['audience'],
                        'total_recipients': c['total_recipients'], 'sent_count': c['sent_count'],
                        'opened_count': c['opened_count'], 'clicked_count': c['clicked_count'],
                        'created_by': admin,
                        'sent_at': timezone.now() - timedelta(days=random.randint(1, 30)) if c['status'] == 'sent' else None,
                    })
                    if created:
                        camp_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {camp_count} campagnes creees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Campagnes ignorees : {e}"))

            # ── 21. Tickets support ────────────────────────────────────────
            try:
                from apps.support.models import SupportTicket, TicketMessage
                from apps.orders.models import Order
                customers = list(User.objects.filter(role='customer'))
                orders = list(Order.objects.all()[:8])
                TICKET_DATA = [
                    {"category": "delivery", "priority": "high", "subject": "Livraison non reçue après 10 jours", "status": "in_progress"},
                    {"category": "product",  "priority": "medium", "subject": "Matelas reçu avec défaut sur la housse", "status": "open"},
                    {"category": "payment",  "priority": "urgent", "subject": "Double débit sur mon compte Orange Money", "status": "open"},
                    {"category": "order",    "priority": "medium", "subject": "Je souhaite modifier ma commande en cours", "status": "waiting_customer"},
                    {"category": "account",  "priority": "low",    "subject": "Impossible de me connecter depuis 2 jours", "status": "resolved"},
                    {"category": "product",  "priority": "medium", "subject": "Le canapé reçu ne correspond pas aux photos", "status": "in_progress"},
                    {"category": "delivery", "priority": "low",    "subject": "Demande de délai de livraison estimé", "status": "closed"},
                    {"category": "other",    "priority": "low",    "subject": "Question sur la politique de retour", "status": "resolved"},
                ]
                tkt_count = 0
                for i, td in enumerate(TICKET_DATA):
                    if SupportTicket.objects.filter(subject=td['subject']).exists():
                        continue
                    user = customers[i % max(len(customers), 1)] if customers else client
                    order = orders[i % len(orders)] if orders else None
                    ticket = SupportTicket.objects.create(
                        user=user,
                        category=td['category'], priority=td['priority'],
                        subject=td['subject'], status=td['status'],
                        order=order if i % 2 == 0 else None,
                    )
                    TicketMessage.objects.create(
                        ticket=ticket, sender=user,
                        content=f"Bonjour, {td['subject'].lower()}. Merci de bien vouloir m'aider à résoudre ce problème rapidement."
                    )
                    if td['status'] in ('in_progress', 'resolved', 'closed'):
                        TicketMessage.objects.create(
                            ticket=ticket, sender=admin,
                            content="Bonjour, merci pour votre message. Notre équipe prend en charge votre demande. Nous vous recontactons dans les plus brefs délais."
                        )
                    tkt_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {tkt_count} tickets crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Tickets ignores : {e}"))

            # ── 22. FAQs ───────────────────────────────────────────────────
            try:
                from apps.support.models import FAQ, FAQCategory
                FAQ_CATS = [
                    {"name": "Commandes & Livraisons", "slug": "commandes-livraisons", "icon": "📦", "order": 1},
                    {"name": "Paiements", "slug": "paiements", "icon": "💳", "order": 2},
                    {"name": "Retours & Remboursements", "slug": "retours-remboursements", "icon": "🔄", "order": 3},
                    {"name": "Compte & Sécurité", "slug": "compte-securite", "icon": "🔒", "order": 4},
                    {"name": "Vendeurs", "slug": "vendeurs", "icon": "🏪", "order": 5},
                ]
                faq_cat_map = {}
                for fc in FAQ_CATS:
                    obj, _ = FAQCategory.objects.get_or_create(slug=fc['slug'], defaults={
                        'name': fc['name'], 'icon': fc['icon'], 'order': fc['order']
                    })
                    faq_cat_map[fc['slug']] = obj

                FAQS = [
                    {"cat": "commandes-livraisons", "q": "Quels sont les délais de livraison ?", "a": "Les délais de livraison varient selon votre localisation : 24-48h pour Abidjan, 3-5 jours pour les autres villes de Côte d'Ivoire."},
                    {"cat": "commandes-livraisons", "q": "Comment suivre ma commande ?", "a": "Rendez-vous dans 'Mon espace > Mes commandes' pour suivre en temps réel l'état de votre livraison avec le numéro de suivi fourni."},
                    {"cat": "commandes-livraisons", "q": "Puis-je modifier ma commande après validation ?", "a": "Il est possible de modifier une commande dans les 2 heures suivant sa validation, tant qu'elle n'est pas encore prise en charge par le vendeur."},
                    {"cat": "paiements", "q": "Quels moyens de paiement acceptez-vous ?", "a": "Nous acceptons Orange Money, MTN Mobile Money, Wave, ainsi que les cartes Visa et Mastercard via nos partenaires CinetPay et PayDunya."},
                    {"cat": "paiements", "q": "Mon paiement a échoué. Que faire ?", "a": "Vérifiez que votre solde est suffisant et que votre numéro est bien enregistré. Réessayez ou contactez notre support au +225 XX XX XX XX."},
                    {"cat": "retours-remboursements", "q": "Quelle est la politique de retour ?", "a": "Vous disposez de 14 jours après réception pour retourner tout article non conforme ou défectueux. Le retour est gratuit sur présentation du bon de retour."},
                    {"cat": "retours-remboursements", "q": "Quand vais-je être remboursé ?", "a": "Le remboursement est traité sous 3 à 5 jours ouvrés après réception et inspection du produit retourné."},
                    {"cat": "compte-securite", "q": "Comment changer mon mot de passe ?", "a": "Allez dans 'Mon compte > Sécurité > Changer le mot de passe'. Un email de confirmation vous sera envoyé."},
                    {"cat": "compte-securite", "q": "Mes données personnelles sont-elles sécurisées ?", "a": "Oui, toutes vos données sont chiffrées et stockées de manière sécurisée. Nous ne partageons jamais vos informations avec des tiers."},
                    {"cat": "vendeurs", "q": "Comment devenir vendeur sur Dooya ?", "a": "Créez un compte, accédez à l'espace vendeur, complétez votre profil boutique et soumettez vos documents. L'approbation prend généralement 48h."},
                    {"cat": "vendeurs", "q": "Quels sont les frais de commission ?", "a": "Dooya prélève une commission de 8 à 12% sur chaque vente selon la catégorie de produit et le statut du vendeur."},
                ]
                faq_count = 0
                for i, f in enumerate(FAQS):
                    if not FAQ.objects.filter(question=f['q']).exists():
                        FAQ.objects.create(
                            faq_category=faq_cat_map.get(f['cat']),
                            question=f['q'], answer=f['a'],
                            is_published=True, order=i,
                        )
                        faq_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {faq_count} FAQs creees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] FAQs ignorees : {e}"))

            # ── 23. Litiges ────────────────────────────────────────────────
            try:
                from apps.support.models import Dispute
                from apps.orders.models import Order
                customers = list(User.objects.filter(role='customer'))
                paid_orders = list(Order.objects.filter(payment_status='paid')[:5])
                DISPUTE_DATA = [
                    {"subject": "Produit non conforme — matelas reçu abîmé", "status": "open", "amount": 189000},
                    {"subject": "Canapé livré avec une déchirure non signalée", "status": "under_review", "amount": 285000},
                    {"subject": "Couleur du produit différente de l'annonce", "status": "resolved_buyer", "amount": 48500},
                ]
                disp_count = 0
                for i, dd in enumerate(DISPUTE_DATA):
                    if i >= len(paid_orders) or i >= len(stores):
                        break
                    if Dispute.objects.filter(subject=dd['subject']).exists():
                        continue
                    user = customers[i % max(len(customers), 1)] if customers else client
                    Dispute.objects.create(
                        order=paid_orders[i],
                        complainant=user,
                        defendant_store=stores[i % len(stores)],
                        subject=dd['subject'],
                        description=f"Description détaillée : {dd['subject']}. Le client demande un remboursement ou remplacement.",
                        status=dd['status'],
                        amount_claimed=Decimal(str(dd['amount'])),
                        amount_awarded=Decimal(str(dd['amount'])) if dd['status'] == 'resolved_buyer' else Decimal('0'),
                    )
                    disp_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {disp_count} litiges crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Litiges ignores : {e}"))

            # ── 24. Retours produits ───────────────────────────────────────
            try:
                from apps.quality.models import ProductReturn
                from apps.orders.models import Order, OrderItem
                customers = list(User.objects.filter(role='customer'))
                order_items = list(OrderItem.objects.select_related('product')[:5])
                RETURN_DATA = [
                    {"reason": "defective", "condition": "defective", "status": "pending"},
                    {"reason": "not_as_described", "condition": "good", "status": "received"},
                    {"reason": "damaged_delivery", "condition": "damaged", "status": "approved"},
                ]
                ret_count = 0
                for i, rd in enumerate(RETURN_DATA):
                    if i >= len(order_items):
                        break
                    oi = order_items[i]
                    user = customers[i % max(len(customers), 1)] if customers else client
                    ProductReturn.objects.create(
                        requested_by=user,
                        product=oi.product,
                        quantity=1,
                        order_item=oi,
                        reason=rd['reason'],
                        description=f"Retour demandé pour : {oi.product.name}. Motif : {rd['reason']}.",
                        condition=rd['condition'],
                        status=rd['status'],
                    )
                    ret_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {ret_count} retours produits crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Retours ignores : {e}"))

            # ── 25. Fournisseurs ───────────────────────────────────────────
            try:
                from apps.suppliers.models import Supplier
                SUPPLIERS = [
                    {"name": "MobilExpo CI",     "code": "MOBCI01", "contact_name": "Oumar Diallo",    "email": "contact@mobilexpo.ci", "phone": "+225 07 45 12 33 90", "city": "Abidjan", "country": "CI", "lead_time_days": 5},
                    {"name": "Literie Pro Dakar", "code": "LITPRO01","contact_name": "Aminata Fall",   "email": "infos@literiedakar.sn", "phone": "+221 77 832 45 10", "city": "Dakar",   "country": "SN", "lead_time_days": 14},
                    {"name": "Déco & Style Ghana","code": "DSGHA01", "contact_name": "Kwame Mensah",  "email": "kwame@decostyle.gh",   "phone": "+233 24 567 8901", "city": "Accra",   "country": "GH", "lead_time_days": 10},
                    {"name": "FurniAsia Trading", "code": "FUASIA01","contact_name": "Mei Lin",        "email": "meilin@furniasia.cn",  "phone": "+86 20 8765 4321", "city": "Guangzhou","country":"CN", "lead_time_days": 45},
                ]
                sup_count = 0
                all_prods = list(Product.objects.all()[:8])
                for s in SUPPLIERS:
                    sup, created = Supplier.objects.get_or_create(code=s['code'], defaults={
                        'name': s['name'], 'contact_name': s['contact_name'],
                        'email': s['email'], 'phone': s['phone'], 'city': s['city'], 'country': s['country'],
                        'lead_time_days': s['lead_time_days'],
                        'min_order_amount': Decimal(random.randint(100000, 500000)),
                        'is_active': True, 'is_approved': True,
                        'quality_rating': random.choice(['A', 'B', 'B']),
                        'on_time_delivery_rate': Decimal(str(random.randint(85, 98))),
                    })
                    if sup.phone != s['phone']:
                        sup.phone = s['phone']
                        sup.save(update_fields=['phone'])
                    if created:
                        sup_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {sup_count} fournisseurs crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Fournisseurs ignores : {e}"))

            # ── 26. Livraisons ─────────────────────────────────────────────
            try:
                from apps.deliveries.models import Delivery
                from apps.orders.models import Order
                all_orders = list(Order.objects.filter(status__in=['processing', 'shipped', 'delivered'])[:8])
                del_count = 0
                DEL_STATUSES = ['pending', 'assigned', 'picked_up', 'in_transit', 'delivered']
                for order in all_orders:
                    if not hasattr(order, 'delivery') or not Delivery.objects.filter(order=order).exists():
                        Delivery.objects.create(
                            order=order,
                            type='home_delivery',
                            status=DEL_STATUSES[all_orders.index(order) % len(DEL_STATUSES)],
                            estimated_delivery_date=(timezone.now() + timedelta(days=random.randint(1, 5))).date(),
                        )
                        del_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {del_count} livraisons creees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Livraisons ignorees : {e}"))

            # ── 27. Live Shopping ──────────────────────────────────────────
            try:
                from apps.live.models import LiveSession, LiveProduct
                live_count = 0
                lp_count = 0
                featured_products = list(Product.objects.filter(is_featured=True)[:6])
                LIVE_DATA = [
                    {"title": "Vente Flash Literie — Matelas -25%", "status": "ended",
                     "scheduled_at": timezone.now() - timedelta(days=7),
                     "started_at": timezone.now() - timedelta(days=7),
                     "ended_at": timezone.now() - timedelta(days=7) + timedelta(hours=2),
                     "viewer_count": 342, "peak_viewer_count": 512, "total_orders": 23, "total_revenue": 4347000},
                    {"title": "Nouvelle Collection Salon Automne 2025", "status": "ended",
                     "scheduled_at": timezone.now() - timedelta(days=3),
                     "started_at": timezone.now() - timedelta(days=3),
                     "ended_at": timezone.now() - timedelta(days=3) + timedelta(hours=1, minutes=30),
                     "viewer_count": 189, "peak_viewer_count": 245, "total_orders": 12, "total_revenue": 2856000},
                    {"title": "Showcase Pack Chambre Premium", "status": "scheduled",
                     "scheduled_at": timezone.now() + timedelta(days=2),
                     "started_at": None, "ended_at": None,
                     "viewer_count": 0, "peak_viewer_count": 0, "total_orders": 0, "total_revenue": 0},
                ]
                for i, ld in enumerate(LIVE_DATA):
                    store = stores[i % len(stores)]
                    host = store.user
                    session = LiveSession.objects.create(
                        title=ld['title'], store=store, host=host,
                        status=ld['status'],
                        scheduled_at=ld['scheduled_at'],
                        started_at=ld['started_at'], ended_at=ld['ended_at'],
                        viewer_count=ld['viewer_count'], peak_viewer_count=ld['peak_viewer_count'],
                        total_orders=ld['total_orders'], total_revenue=Decimal(str(ld['total_revenue'])),
                    )
                    live_count += 1
                    for j, prod in enumerate(featured_products[:2]):
                        try:
                            LiveProduct.objects.create(
                                session=session, product=prod,
                                live_price=prod.price * Decimal('0.85'),
                                discount_pct=Decimal('15'), position=j,
                                units_sold=random.randint(0, 10),
                            )
                            lp_count += 1
                        except Exception:
                            pass
                self.stdout.write(self.style.SUCCESS(f"[OK] {live_count} sessions live, {lp_count} produits live crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Live ignorees : {e}"))

            # ── 28. Messagerie ─────────────────────────────────────────────
            try:
                from apps.chat.models import Conversation, Message
                from apps.orders.models import Order
                customers = list(User.objects.filter(role='customer'))
                paid_orders = list(Order.objects.filter(payment_status='paid')[:4])
                conv_count = 0
                msg_count = 0
                CONV_DATA = [
                    ("customer_vendor", [
                        ("client", "Bonjour, est-ce que ce matelas est disponible en 140×190 ?"),
                        ("vendor", "Bonjour ! Oui, il est disponible en 140×190, 160×200 et 180×200."),
                        ("client", "Super ! Quels sont les délais de livraison pour Abidjan ?"),
                        ("vendor", "Livraison sous 48h pour Abidjan plateau. Livraison gratuite à partir de 150 000 FCFA."),
                    ]),
                    ("customer_vendor", [
                        ("client", "Bonjour, puis-je voir des photos supplémentaires du canapé gris ?"),
                        ("vendor", "Bien sûr ! Je vous envoie des photos depuis différents angles. Le coloris est magnifique en vrai."),
                        ("client", "Merci beaucoup ! Je passe commande."),
                    ]),
                    ("support", [
                        ("client", "Bonjour, ma commande n'est pas encore arrivée après 5 jours."),
                        ("vendor", "Bonjour, nous sommes désolés pour ce délai. Votre colis est en transit. Vous le recevrez demain."),
                    ]),
                ]
                for i, (conv_type, messages) in enumerate(CONV_DATA):
                    if not customers and not stores:
                        break
                    customer = customers[i % max(len(customers), 1)] if customers else client
                    vendor_user = stores[i % len(stores)].user if stores else admin
                    order = paid_orders[i % len(paid_orders)] if paid_orders else None
                    conv = Conversation.objects.create(
                        type=conv_type,
                        order=order if conv_type == 'support' else None,
                    )
                    conv.participants.add(customer, vendor_user)
                    conv_count += 1
                    for sender_key, content in messages:
                        sender = customer if sender_key == 'client' else vendor_user
                        Message.objects.create(
                            conversation=conv, sender=sender,
                            content=content, type='text',
                            is_read=True,
                        )
                        msg_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {conv_count} conversations, {msg_count} messages crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Messagerie ignoree : {e}"))

            # ── 29. Rapports ───────────────────────────────────────────────
            try:
                from apps.reports.models import Report
                from reportlab.lib.pagesizes import A4
                from reportlab.pdfgen import canvas as rl_canvas
                REPORTS = [
                    {"type": "sales",    "name": "Rapport ventes mai 2025",     "status": "ready",      "params": {"period": "2025-05"}},
                    {"type": "vendors",  "name": "Performance vendeurs Q2 2025","status": "ready",      "params": {"quarter": "Q2-2025"}},
                    {"type": "products", "name": "Analyse produits avril 2025", "status": "ready",      "params": {"period": "2025-04"}},
                    {"type": "payments", "name": "Réconciliation paiements mars","status": "processing","params": {"period": "2025-03"}},
                    {"type": "users",    "name": "Acquisition utilisateurs 2025","status": "pending",   "params": {"year": "2025"}},
                ]

                def _make_pdf(report_name):
                    buf = BytesIO()
                    c = rl_canvas.Canvas(buf, pagesize=A4)
                    w, h = A4
                    c.setFont("Helvetica-Bold", 16)
                    c.drawString(50, h - 80, "DOOYA — " + report_name)
                    c.setFont("Helvetica", 11)
                    c.drawString(50, h - 110, f"Généré le {timezone.now().strftime('%d/%m/%Y')}")
                    c.drawString(50, h - 140, "Ce rapport a été généré automatiquement par la plateforme Dooya.")
                    c.save()
                    buf.seek(0)
                    safe_name = slugify(report_name)[:40] + ".pdf"
                    return InMemoryUploadedFile(buf, 'file', safe_name, 'application/pdf', buf.getbuffer().nbytes, None)

                rpt_count = 0
                for r in REPORTS:
                    if not Report.objects.filter(name=r['name']).exists():
                        kwargs = dict(
                            type=r['type'], name=r['name'], status=r['status'],
                            parameters=r['params'], generated_by=admin,
                            completed_at=timezone.now() - timedelta(days=random.randint(1, 30)) if r['status'] == 'ready' else None,
                        )
                        if r['status'] == 'ready':
                            kwargs['file'] = _make_pdf(r['name'])
                        Report.objects.create(**kwargs)
                        rpt_count += 1
                    elif r['status'] == 'ready':
                        rpt = Report.objects.get(name=r['name'])
                        if not rpt.file:
                            rpt.file = _make_pdf(r['name'])
                            rpt.save(update_fields=['file'])
                self.stdout.write(self.style.SUCCESS(f"[OK] {rpt_count} rapports crees"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Rapports ignores : {e}"))

            # ── 30. Entrepôts & Stock ──────────────────────────────────────
            try:
                from apps.inventory.models import Warehouse, StockLocation, StockMovement
                WAREHOUSES = [
                    {"name": "Entrepôt Principal Abidjan", "code": "WH-ABJ-01", "city": "Abidjan", "is_default": True},
                    {"name": "Dépôt Yopougon",             "code": "WH-YOP-01", "city": "Yopougon"},
                    {"name": "Point relais Cocody",        "code": "WH-COC-01", "city": "Cocody"},
                ]
                wh_map = {}
                for w in WAREHOUSES:
                    wh, _ = Warehouse.objects.get_or_create(code=w['code'], defaults={
                        'name': w['name'], 'city': w['city'],
                        'country': 'CI', 'is_active': True,
                        'is_default': w.get('is_default', False),
                        'manager': admin,
                    })
                    wh_map[w['code']] = wh

                all_prods = list(Product.objects.all()[:15])
                sl_count = 0
                sm_count = 0
                main_wh = wh_map.get('WH-ABJ-01')
                if main_wh:
                    for prod in all_prods:
                        sl, created = StockLocation.objects.get_or_create(
                            warehouse=main_wh, product=prod, variant=None,
                            defaults={'quantity': prod.stock, 'reserved_quantity': random.randint(0, max(1, prod.stock // 5))}
                        )
                        if created:
                            sl_count += 1
                            StockMovement.objects.create(
                                warehouse=main_wh, product=prod,
                                movement_type='in',
                                reason='initial',
                                quantity=prod.stock,
                                stock_before=0,
                                stock_after=prod.stock,
                                reference=f'INIT-{prod.sku}',
                                notes='Stock initial seed',
                                performed_by=admin,
                            )
                            sm_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {len(WAREHOUSES)} entrepots, {sl_count} emplacements, {sm_count} mouvements"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Stock/Entrepots ignores : {e}"))

            # ── 31. Commissions & Paiements vendeurs ──────────────────────
            try:
                from apps.commissions.models import Commission, VendorPayout, CommissionRule
                from apps.orders.models import Order
                paid_orders = list(Order.objects.filter(payment_status='paid').prefetch_related('items__store'))
                default_rule = CommissionRule.objects.filter(store=None, category=None, is_active=True).first()
                comm_count = 0
                for order in paid_orders[:8]:
                    if Commission.objects.filter(order=order).exists():
                        continue
                    first_item = order.items.first()
                    if not first_item:
                        continue
                    store = first_item.store
                    rate = Decimal('0.10')
                    commission_amount = order.total_amount * rate
                    Commission.objects.create(
                        order=order, store=store, rule=default_rule,
                        order_amount=order.total_amount,
                        rate_applied=rate, flat_fee_applied=Decimal('0'),
                        commission_amount=commission_amount,
                        vendor_amount=order.total_amount - commission_amount,
                        status='confirmed',
                    )
                    comm_count += 1

                payout_count = 0
                for store in stores[:3]:
                    store_commissions = Commission.objects.filter(store=store, status='confirmed', payout__isnull=True)
                    if store_commissions.exists():
                        total_order_amount = sum(c.order_amount for c in store_commissions)
                        total_commission = sum(c.commission_amount for c in store_commissions)
                        total_payout = sum(c.vendor_amount for c in store_commissions)
                        payout = VendorPayout.objects.create(
                            store=store,
                            period_start=(timezone.now() - timedelta(days=30)).date(),
                            period_end=timezone.now().date(),
                            total_order_amount=total_order_amount,
                            total_commission=total_commission,
                            total_payout=total_payout,
                            status=random.choice(['pending', 'paid']),
                            method='mobile_money',
                            processed_by=admin,
                        )
                        store_commissions.update(payout=payout, status='paid')
                        payout_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {comm_count} commissions, {payout_count} paiements vendeurs"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Commissions/Payouts ignores : {e}"))

        # ── Résumé ─────────────────────────────────────────────────────────
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"[DONE] Seed termine !"))
        self.stdout.write(f"   Produits crees  : {created_count}")
        if not no_images:
            self.stdout.write(f"   Images OK       : {image_ok_count}")
            self.stdout.write(f"   Images echouees : {image_fail}")
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("\n[COMPTES DE TEST]"))
        self.stdout.write("   Admin   -> admin@dooya.ci    / dooya2025!")
        self.stdout.write("   Client  -> client@dooya.ci   / client2025!")
        self.stdout.write("   Vendeur -> kouame@dooya-vendor.ci / vendor2025!")
        self.stdout.write("")
