from django.shortcuts import redirect
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin
from core.pagination import StandardPagination
from .models import AffiliateProfile, AffiliateLink, AffiliateClick, AffiliateConversion, AffiliatePayout
from .serializers import (
    AffiliateProfileSerializer, AffiliateLinkSerializer,
    AffiliateConversionSerializer, AffiliateStatsSerializer, AffiliatePayoutSerializer,
)


@extend_schema(tags=['affiliate'])
class AffiliateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = AffiliateProfile.objects.get(user=request.user)
            return Response(AffiliateProfileSerializer(profile).data)
        except AffiliateProfile.DoesNotExist:
            return Response({'detail': 'Aucun profil affilié.'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        if AffiliateProfile.objects.filter(user=request.user).exists():
            return Response({'detail': 'Vous avez déjà un profil affilié.'}, status=status.HTTP_400_BAD_REQUEST)
        profile = AffiliateProfile.objects.create(user=request.user)
        request.user.role = 'affiliate'
        request.user.save(update_fields=['role'])
        return Response(AffiliateProfileSerializer(profile).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['affiliate'])
class AffiliateLinkListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_profile(self, user):
        try:
            return AffiliateProfile.objects.get(user=user)
        except AffiliateProfile.DoesNotExist:
            return None

    def get(self, request):
        profile = self.get_profile(request.user)
        if not profile:
            return Response({'detail': 'Profil affilié requis.'}, status=status.HTTP_404_NOT_FOUND)
        links = profile.links.all().order_by('-created_at')
        serializer = AffiliateLinkSerializer(links, many=True)
        return Response(serializer.data)

    def post(self, request):
        profile = self.get_profile(request.user)
        if not profile:
            return Response({'detail': 'Profil affilié requis.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AffiliateLinkSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(affiliate=profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, link_id):
        profile = self.get_profile(request.user)
        if not profile:
            return Response({'detail': 'Profil affilié requis.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            link = AffiliateLink.objects.get(pk=link_id, affiliate=profile)
        except AffiliateLink.DoesNotExist:
            return Response({'detail': 'Lien introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['affiliate'])
class AffiliateLinkClickView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, code):
        try:
            link = AffiliateLink.objects.get(code=code)
        except AffiliateLink.DoesNotExist:
            return redirect('/')
        AffiliateClick.objects.create(
            link=link,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            user=request.user if request.user.is_authenticated else None,
        )
        AffiliateLink.objects.filter(pk=link.pk).update(click_count=link.click_count + 1)
        AffiliateProfile.objects.filter(pk=link.affiliate.pk).update(total_clicks=link.affiliate.total_clicks + 1)
        dest = link.custom_url or '/'
        if link.product:
            dest = f'/products/{link.product.slug}/'
        elif link.category:
            dest = f'/categories/{link.category.slug}/'
        elif link.store:
            dest = f'/stores/{link.store.slug}/'
        return redirect(dest)


@extend_schema(tags=['affiliate'])
class AffiliateStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = AffiliateProfile.objects.get(user=request.user)
        except AffiliateProfile.DoesNotExist:
            return Response({'detail': 'Profil affilié requis.'}, status=status.HTTP_404_NOT_FOUND)
        from django.db.models import Sum
        pending = AffiliateConversion.objects.filter(link__affiliate=profile, status='pending').aggregate(
            total=Sum('commission_amount')
        )['total'] or 0
        conversion_rate = (profile.total_conversions / profile.total_clicks * 100) if profile.total_clicks > 0 else 0
        data = {
            'total_clicks': profile.total_clicks,
            'total_conversions': profile.total_conversions,
            'total_earnings': profile.total_earnings,
            'conversion_rate': round(conversion_rate, 2),
            'pending_earnings': pending,
        }
        return Response(AffiliateStatsSerializer(data).data)


@extend_schema(tags=['affiliate'])
class AffiliateConversionListView(generics.ListAPIView):
    serializer_class = AffiliateConversionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        try:
            profile = AffiliateProfile.objects.get(user=self.request.user)
        except AffiliateProfile.DoesNotExist:
            return AffiliateConversion.objects.none()
        return AffiliateConversion.objects.filter(link__affiliate=profile).order_by('-created_at')


@extend_schema(tags=['affiliate'])
class AffiliatePayoutRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = AffiliateProfile.objects.get(user=request.user)
        except AffiliateProfile.DoesNotExist:
            return Response({'detail': 'Profil affilié requis.'}, status=status.HTTP_404_NOT_FOUND)
        if profile.total_earnings <= 0:
            return Response({'detail': 'Aucun revenu disponible.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = AffiliatePayoutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(affiliate=profile, amount=profile.total_earnings)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['affiliate'])
class AdminAffiliateListView(generics.ListAPIView):
    serializer_class = AffiliateProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination
    queryset = AffiliateProfile.objects.all().select_related('user').order_by('-created_at')


@extend_schema(tags=['affiliate'])
class AdminAffiliatePayoutView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        payouts = AffiliatePayout.objects.all().select_related('affiliate__user').order_by('-created_at')
        serializer = AffiliatePayoutSerializer(payouts, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        try:
            payout = AffiliatePayout.objects.get(pk=pk)
        except AffiliatePayout.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        action = request.data.get('action')
        if action == 'process':
            payout.status = 'processed'
            payout.reference = request.data.get('reference', '')
        elif action == 'reject':
            payout.status = 'rejected'
        else:
            return Response({'detail': 'Action invalide.'}, status=status.HTTP_400_BAD_REQUEST)
        payout.save()
        return Response(AffiliatePayoutSerializer(payout).data)
