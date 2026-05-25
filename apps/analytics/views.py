from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from datetime import timedelta, date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin, IsVendor
from .models import SalesStat
from .serializers import SalesStatSerializer


@extend_schema(tags=['analytics'])
class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        from django.contrib.auth import get_user_model
        from apps.orders.models import Order, OrderItem
        from apps.vendors.models import Store
        from apps.products.models import Product

        User = get_user_model()
        from django.utils.timezone import localdate, localtime
        from datetime import datetime, time as dt_time
        from django.utils.timezone import make_aware

        now = timezone.now()
        today = localdate()
        today_start = make_aware(datetime.combine(today, dt_time.min))
        today_end   = make_aware(datetime.combine(today, dt_time.max))
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        users_count = User.objects.count()
        vendors_count = User.objects.filter(role='vendor').count()
        orders_today = Order.objects.filter(created_at__range=(today_start, today_end)).count()
        revenue_today = Order.objects.filter(
            created_at__range=(today_start, today_end), payment_status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        revenue_month = Order.objects.filter(
            created_at__gte=month_start, payment_status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        top_products = list(
            OrderItem.objects.filter(order__payment_status='paid')
            .values('product__name', 'product__slug')
            .annotate(total_qty=Sum('quantity'), total_revenue=Sum('total_price'))
            .order_by('-total_revenue')[:5]
        )
        top_vendors = list(
            OrderItem.objects.filter(order__payment_status='paid')
            .values('store__name', 'store__slug')
            .annotate(total_revenue=Sum('total_price'), orders_count=Count('order', distinct=True))
            .order_by('-total_revenue')[:5]
        )
        recent_orders = list(
            Order.objects.order_by('-created_at')[:10].values(
                'order_number', 'status', 'payment_status', 'total_amount', 'created_at'
            )
        )

        return Response({
            'users_count': users_count,
            'vendors_count': vendors_count,
            'orders_today': orders_today,
            'revenue_today': revenue_today,
            'revenue_month': revenue_month,
            'top_products': top_products,
            'top_vendors': top_vendors,
            'recent_orders': recent_orders,
        })


@extend_schema(tags=['analytics'])
class AdminSalesChartView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        from apps.orders.models import Order
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        group_by = request.query_params.get('group_by', 'day')

        try:
            from datetime import datetime
            if date_from:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            else:
                date_from = (timezone.now() - timedelta(days=30)).date()
            if date_to:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            else:
                date_to = timezone.now().date()
        except ValueError:
            return Response({'detail': 'Format de date invalide. Utilisez YYYY-MM-DD.'}, status=400)

        orders = Order.objects.filter(
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
            payment_status='paid',
        )

        if group_by == 'month':
            from django.db.models.functions import TruncMonth
            data = orders.annotate(period=TruncMonth('created_at')).values('period').annotate(
                orders_count=Count('id'), revenue=Sum('total_amount')
            ).order_by('period')
        elif group_by == 'week':
            from django.db.models.functions import TruncWeek
            data = orders.annotate(period=TruncWeek('created_at')).values('period').annotate(
                orders_count=Count('id'), revenue=Sum('total_amount')
            ).order_by('period')
        else:
            from django.db.models.functions import TruncDate
            data = orders.annotate(period=TruncDate('created_at')).values('period').annotate(
                orders_count=Count('id'), revenue=Sum('total_amount')
            ).order_by('period')

        return Response(list(data))


@extend_schema(tags=['analytics'])
class AdminTopProductsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        from apps.orders.models import OrderItem
        limit = int(request.query_params.get('limit', 10))
        sort_by = request.query_params.get('sort_by', 'revenue')
        order_field = '-total_revenue' if sort_by == 'revenue' else '-total_qty'
        top = list(
            OrderItem.objects.filter(order__payment_status='paid')
            .values('product__id', 'product__name', 'product__slug')
            .annotate(total_qty=Sum('quantity'), total_revenue=Sum('total_price'))
            .order_by(order_field)[:limit]
        )
        return Response(top)


@extend_schema(tags=['analytics'])
class AdminTopVendorsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        from apps.orders.models import OrderItem
        limit = int(request.query_params.get('limit', 10))
        top = list(
            OrderItem.objects.filter(order__payment_status='paid')
            .values('store__id', 'store__name', 'store__slug')
            .annotate(total_revenue=Sum('total_price'), orders_count=Count('order', distinct=True))
            .order_by('-total_revenue')[:limit]
        )
        return Response(top)


@extend_schema(tags=['analytics'])
class AdminUserStatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        now = timezone.now()
        first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        total = User.objects.count()
        new_this_month = User.objects.filter(date_joined__gte=first_day).count()
        by_role = list(User.objects.values('role').annotate(count=Count('id')))
        return Response({
            'total': total,
            'new_this_month': new_this_month,
            'by_role': by_role,
        })


@extend_schema(tags=['analytics'])
class VendorAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        from apps.orders.models import OrderItem
        from apps.products.models import Product
        store = request.user.store
        now = timezone.now()
        date_from_str = request.query_params.get('date_from')
        date_to_str = request.query_params.get('date_to')
        try:
            from datetime import datetime
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else (now - timedelta(days=30)).date()
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else now.date()
        except ValueError:
            return Response({'detail': 'Format de date invalide.'}, status=400)

        items = OrderItem.objects.filter(
            store=store,
            order__created_at__date__gte=date_from,
            order__created_at__date__lte=date_to,
            order__payment_status='paid',
        )
        total_revenue = items.aggregate(total=Sum('total_price'))['total'] or 0
        total_orders = items.values('order').distinct().count()
        top_products = list(
            items.values('product__name', 'product__slug')
            .annotate(qty=Sum('quantity'), revenue=Sum('total_price'))
            .order_by('-revenue')[:5]
        )
        products_count = Product.objects.filter(store=store, is_active=True).count()
        return Response({
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'products_count': products_count,
            'top_products': top_products,
            'period': {'date_from': str(date_from), 'date_to': str(date_to)},
        })
