from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .nlp import parse_query, build_product_queryset, extract_keywords
from .transcription import transcribe_audio


def _serialize_products(qs, request, limit=20):
    from apps.products.serializers import ProductListSerializer
    return ProductListSerializer(qs[:limit], many=True, context={'request': request}).data


class TextSearchView(APIView):
    """Recherche intelligente en langage naturel (texte)."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Recherche'],
        summary='Recherche intelligente NLP (texte)',
        parameters=[
            OpenApiParameter('q', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=True,
                             description='Requête en langage naturel'),
            OpenApiParameter('limit', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response({'detail': 'Paramètre q requis.'}, status=status.HTTP_400_BAD_REQUEST)

        limit = min(int(request.query_params.get('limit', 20)), 50)
        parsed = parse_query(q)

        if not parsed['keywords'] and not parsed['filters']:
            return Response({'results': [], 'keywords': [], 'filters': {}, 'query': q})

        qs = build_product_queryset(parsed).order_by('-views_count')
        results = _serialize_products(qs, request, limit)

        return Response({
            'query': q,
            'keywords': parsed['keywords'],
            'filters': parsed['filters'],
            'count': qs.count(),
            'results': results,
        })


class VoiceSearchView(APIView):
    """Recherche par voix — audio → transcription → NLP → résultats."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Recherche'],
        summary='Recherche vocale (upload audio)',
        description=(
            'Envoyer un fichier audio (WAV, WEBM, OGG, MP3, FLAC) en multipart/form-data '
            'avec le champ `audio`. Le service transcrit la voix, extrait les mots-clés '
            'et retourne les produits correspondants.\n\n'
            'Langues supportées : fr-FR, en-US, sw-KE, yo-NG, ha-NE…\n\n'
            'Nécessite GOOGLE_SPEECH_API_KEY ou USE_WHISPER=True dans les settings.'
        ),
    )
    def post(self, request):
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({'detail': 'Champ audio requis.'}, status=status.HTTP_400_BAD_REQUEST)

        language_code = request.data.get('language', 'fr-FR')
        limit = min(int(request.data.get('limit', 20)), 50)

        # Transcription
        transcript = transcribe_audio(audio_file, language_code=language_code)
        if transcript is None:
            return Response(
                {'detail': 'Transcription indisponible. Configurez GOOGLE_SPEECH_API_KEY ou USE_WHISPER.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        parsed = parse_query(transcript)
        qs = build_product_queryset(parsed).order_by('-views_count')
        results = _serialize_products(qs, request, limit)

        return Response({
            'transcript': transcript,
            'keywords': parsed['keywords'],
            'filters': parsed['filters'],
            'count': qs.count(),
            'results': results,
        })


class SearchSuggestionsView(APIView):
    """Auto-complétion pour la barre de recherche."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Recherche'],
        summary='Suggestions de recherche (auto-complétion)',
        parameters=[
            OpenApiParameter('q', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter('limit', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        from django.db.models import Q
        from apps.products.models import Product
        from apps.analytics.models import SearchQuery

        q = request.query_params.get('q', '').strip()
        if len(q) < 2:
            return Response({'suggestions': []})

        limit = min(int(request.query_params.get('limit', 8)), 15)

        # Suggestions produits
        product_names = (
            Product.objects.filter(
                is_active=True, status='published',
                name__icontains=q
            )
            .values_list('name', flat=True)
            .order_by('-views_count')[:limit]
        )

        # Requêtes populaires existantes
        popular_queries = (
            SearchQuery.objects.filter(query__icontains=q)
            .values_list('query', flat=True)
            .order_by('-count')[:limit]
            if hasattr(SearchQuery, 'count') else []
        )

        suggestions = list(dict.fromkeys(list(product_names) + list(popular_queries)))[:limit]
        return Response({'query': q, 'suggestions': suggestions})
