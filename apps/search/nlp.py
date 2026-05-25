"""
Traitement NLP léger pour la recherche vocale et intelligente.

Pas de dépendance ML externe.
Pipeline :
  1. Normalisation (minuscules, accents, ponctuations)
  2. Extraction de mots-clés (stopwords FR + EN supprimés)
  3. Détection de filtres (prix, catégorie, couleur, taille…)
  4. Construction de la requête Django Q
"""
import re
import unicodedata


# ── Stopwords FR + EN ────────────────────────────────────────────────────────
STOPWORDS = {
    'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'au', 'aux',
    'et', 'ou', 'mais', 'donc', 'or', 'ni', 'car',
    'je', 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles',
    'mon', 'ton', 'son', 'ma', 'ta', 'sa', 'mes', 'tes', 'ses',
    'ce', 'cet', 'cette', 'ces', 'qui', 'que', 'quoi', 'dont', 'où',
    'je', 'veux', 'cherche', 'trouver', 'acheter', 'commander',
    'a', 'an', 'the', 'of', 'in', 'on', 'at', 'to', 'for', 'with',
    'and', 'or', 'but', 'is', 'are', 'was', 'were',
    'show', 'find', 'buy', 'search', 'i', 'want', 'need', 'looking',
}

# ── Patterns de filtres ──────────────────────────────────────────────────────
PRICE_UNDER = re.compile(r'(?:moins de|under|max)\s*(\d+)', re.I)
PRICE_OVER  = re.compile(r'(?:plus de|over|min)\s*(\d+)', re.I)
PRICE_RANGE = re.compile(r'(\d+)\s*(?:à|-)\s*(\d+)', re.I)

COLOR_MAP = {
    'rouge': 'rouge', 'red': 'rouge',
    'bleu': 'bleu', 'blue': 'bleu',
    'vert': 'vert', 'green': 'vert',
    'noir': 'noir', 'black': 'noir',
    'blanc': 'blanc', 'white': 'blanc',
    'jaune': 'jaune', 'yellow': 'jaune',
    'rose': 'rose', 'pink': 'rose',
    'gris': 'gris', 'grey': 'gris', 'gray': 'gris',
    'marron': 'marron', 'brown': 'marron',
    'orange': 'orange',
    'violet': 'violet', 'purple': 'violet',
}


def normalize(text: str) -> str:
    """Normalise le texte : minuscules, sans accents, sans ponctuation."""
    text = text.lower().strip()
    # Supprimer les accents
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    # Supprimer la ponctuation sauf espaces
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_keywords(text: str) -> list[str]:
    """Supprime les stopwords et retourne les mots-clés significatifs."""
    words = normalize(text).split()
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def extract_filters(text: str) -> dict:
    """
    Détecte les filtres implicites dans le texte :
    - prix max / min / fourchette
    - couleur
    """
    filters = {}

    m = PRICE_RANGE.search(text)
    if m:
        filters['price_min'] = int(m.group(1))
        filters['price_max'] = int(m.group(2))
    else:
        m = PRICE_UNDER.search(text)
        if m:
            filters['price_max'] = int(m.group(1))
        m = PRICE_OVER.search(text)
        if m:
            filters['price_min'] = int(m.group(1))

    norm = normalize(text)
    for word, color in COLOR_MAP.items():
        if word in norm.split():
            filters['color'] = color
            break

    return filters


def parse_query(text: str) -> dict:
    """
    Analyse complète d'une requête en langage naturel.
    Retourne : { keywords, filters, raw }
    """
    return {
        'raw': text,
        'keywords': extract_keywords(text),
        'filters': extract_filters(text),
    }


def build_product_queryset(parsed: dict):
    """
    Construit un queryset Django à partir du résultat de parse_query().
    """
    from django.db.models import Q
    from apps.products.models import Product

    keywords = parsed['keywords']
    filters = parsed['filters']

    qs = Product.objects.filter(is_active=True, status='published').select_related('store', 'category')

    if keywords:
        q = Q()
        for kw in keywords:
            q |= (
                Q(name__icontains=kw) |
                Q(description__icontains=kw) |
                Q(tags__name__icontains=kw) |
                Q(category__name__icontains=kw)
            )
        qs = qs.filter(q).distinct()

    if filters.get('price_max'):
        qs = qs.filter(price__lte=filters['price_max'])
    if filters.get('price_min'):
        qs = qs.filter(price__gte=filters['price_min'])
    if filters.get('color'):
        qs = qs.filter(
            Q(attributes__attribute__name__icontains='couleur') |
            Q(attributes__attribute__name__icontains='color'),
            attributes__value__value__icontains=filters['color'],
        ).distinct()

    return qs
