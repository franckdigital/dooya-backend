from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin
from core.pagination import StandardPagination
from .models import Payment, Refund, InstallmentPlan, Installment
from .serializers import PaymentSerializer, PaymentInitiateSerializer, RefundSerializer, InstallmentPlanSerializer
from .gateways import get_gateway
import logging

logger = logging.getLogger(__name__)


@extend_schema(tags=['payments'])
class PaymentInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentInitiateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        order = serializer.validated_data['order']
        method = serializer.validated_data['method']
        gateway_name = serializer.validated_data['gateway']

        if method == 'wallet':
            from apps.wallets.models import Wallet
            try:
                wallet = Wallet.objects.get(user=request.user)
            except Wallet.DoesNotExist:
                return Response({'detail': 'Portefeuille introuvable.'}, status=status.HTTP_400_BAD_REQUEST)
            if wallet.balance < order.total_amount:
                return Response({'detail': 'Solde insuffisant dans le portefeuille.'}, status=status.HTTP_400_BAD_REQUEST)
            payment = Payment.objects.create(
                order=order,
                amount=order.total_amount,
                method=method,
                gateway='internal',
            )
            wallet.debit(order.total_amount, f'Paiement commande #{order.order_number}', payment.reference)
            payment.status = 'success'
            payment.paid_at = timezone.now()
            payment.save(update_fields=['status', 'paid_at'])
            order.payment_status = 'paid'
            order.status = 'confirmed'
            order.save(update_fields=['payment_status', 'status'])
            return Response({'status': 'success', 'payment': PaymentSerializer(payment).data})

        payment = Payment.objects.create(
            order=order,
            amount=order.total_amount,
            method=method,
            gateway=gateway_name,
        )
        try:
            gateway = get_gateway(gateway_name)
            result = gateway.initiate_payment(payment)
            payment.transaction_id = result.get('transaction_id')
            payment.save(update_fields=['transaction_id'])
            return Response({'payment_url': result['payment_url'], 'reference': payment.reference})
        except Exception as e:
            payment.status = 'failed'
            payment.save(update_fields=['status'])
            logger.error(f"Payment initiation error: {e}")
            return Response({'detail': 'Erreur lors de l\'initiation du paiement.'}, status=status.HTTP_502_BAD_GATEWAY)


@extend_schema(tags=['payments'])
class PaymentCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        reference = request.query_params.get('reference') or request.query_params.get('transaction_id')
        if not reference:
            return Response({'detail': 'Référence manquante.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payment = Payment.objects.get(reference=reference)
        except Payment.DoesNotExist:
            return Response({'detail': 'Paiement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if payment.status == 'success':
            return Response(PaymentSerializer(payment).data)
        try:
            gateway = get_gateway(payment.gateway)
            result = gateway.verify_payment(payment.transaction_id or reference)
            if result['status'] == 'success':
                payment.status = 'success'
                payment.paid_at = timezone.now()
                payment.save(update_fields=['status', 'paid_at'])
                payment.order.payment_status = 'paid'
                payment.order.status = 'confirmed'
                payment.order.save(update_fields=['payment_status', 'status'])
            else:
                payment.status = 'failed'
                payment.save(update_fields=['status'])
        except Exception as e:
            logger.error(f"Payment callback error: {e}")
        return Response(PaymentSerializer(payment).data)


@extend_schema(tags=['payments'])
class PaymentWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, gateway_name):
        try:
            gateway = get_gateway(gateway_name)
            gateway.process_webhook(request.data)
        except Exception as e:
            logger.error(f"Webhook {gateway_name} error: {e}")
        return Response({'status': 'received'})


@extend_schema(tags=['payments'])
class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, reference):
        try:
            payment = Payment.objects.get(reference=reference, order__user=request.user)
        except Payment.DoesNotExist:
            return Response({'detail': 'Paiement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PaymentSerializer(payment).data)


@extend_schema(tags=['payments'])
class RefundRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_ref = request.data.get('payment_reference')
        try:
            payment = Payment.objects.get(reference=payment_ref, order__user=request.user, status='success')
        except Payment.DoesNotExist:
            return Response({'detail': 'Paiement introuvable ou non éligible.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RefundSerializer(data={
            'payment': payment.pk,
            'amount': request.data.get('amount', payment.amount),
            'reason': request.data.get('reason', ''),
        })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


MIN_INSTALLMENT_AMOUNT = 100000  # FCFA


def _contract_text(plan=None, order=None, user=None):
    """Return the installment contract text."""
    from datetime import date, timedelta
    today = date.today().strftime('%d/%m/%Y')
    expires = (date.today() + timedelta(days=30)).strftime('%d/%m/%Y')
    total = plan.total_amount if plan else (order.total_amount if order else '—')
    order_num = plan.order.order_number if plan else (order.order_number if order else '—')
    client_name = (user or (plan.order.user if plan else None))
    client = client_name.get_full_name() if client_name else '—'
    return f"""CONTRAT DE RÉSERVATION ET PAIEMENT ÉCHELONNÉ
Plateforme : DOOYA Marketplace
Date : {today}

ENTRE :
DOOYA SARL, société exploitant la plateforme Dooya.ci, ci-après dénommée « DOOYA »,
ET : {client}, ci-après dénommé « le Client »,

IL A ÉTÉ CONVENU CE QUI SUIT :

Article 1 – Objet
Le présent contrat définit les conditions de paiement échelonné pour la commande n° {order_num}, d'un montant total de {total} FCFA.

Article 2 – Modalités de paiement
Le Client s'engage à régler la totalité du montant dans un délai maximum de 30 jours à compter de la signature du présent contrat, soit au plus tard le {expires}.
Chaque versement doit être effectué via Mobile Money (Orange Money, MTN Money ou Wave) et justifié par l'upload d'une preuve de paiement sur la plateforme.

Article 3 – Livraison
L'article commandé sera mis en retrait dans un point relais DOOYA. Aucune livraison à domicile n'est accordée dans le cadre du paiement échelonné.

Article 4 – Non-remboursement
En cas de désistement du Client après signature du présent contrat, aucun remboursement ne sera effectué. Les montants déjà versés restent acquis à DOOYA à titre d'indemnité de réservation.

Article 5 – Clause de déchéance
Passé le délai de 30 jours sans règlement complet, l'article commandé devient automatiquement la propriété de DOOYA, sans qu'il soit besoin d'une mise en demeure préalable.

Article 6 – Prolongation
DOOYA se réserve le droit d'accorder, à sa seule discrétion, une prolongation de 15 jours supplémentaires. Cette prolongation entraîne une pénalité de 10 % du prix de l'article, payable immédiatement.

Article 7 – Certification
Le présent contrat est établi conformément aux dispositions du droit ivoirien des obligations. Il est certifié par huissier de justice et a valeur d'engagement contractuel opposable aux deux parties.

En cliquant sur « J'accepte le contrat », le Client reconnaît avoir lu, compris et accepté l'intégralité des clauses ci-dessus.

DOOYA Marketplace — Abidjan, Côte d'Ivoire
"""


@extend_schema(tags=['payments'])
class InstallmentContractView(APIView):
    """Return the contract text for installment plans."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.orders.models import Order
        order_id = request.query_params.get('order_id')
        order = None
        if order_id:
            try:
                order = Order.objects.get(pk=order_id, user=request.user)
            except Order.DoesNotExist:
                pass
        text = _contract_text(order=order, user=request.user)
        return Response({'contract': text})


@extend_schema(tags=['payments'])
class InstallmentPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = InstallmentPlan.objects.filter(
            order__user=request.user
        ).select_related('order', 'relay_point').prefetch_related('installments').order_by('-created_at')
        serializer = InstallmentPlanSerializer(plans, many=True)
        return Response(serializer.data)

    def post(self, request):
        from apps.orders.models import Order
        from apps.deliveries.models import RelayPoint
        from datetime import timedelta, date
        order_id = request.data.get('order_id')
        relay_point_id = request.data.get('relay_point_id')
        try:
            order = Order.objects.get(pk=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'detail': 'Commande introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if float(order.total_amount) < MIN_INSTALLMENT_AMOUNT:
            return Response(
                {'detail': f'Le paiement échelonné est disponible uniquement pour les articles à partir de {MIN_INSTALLMENT_AMOUNT:,} FCFA.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if InstallmentPlan.objects.filter(order=order).exclude(status='forfeited').exists():
            return Response({'detail': 'Un plan de paiement existe déjà pour cette commande.'}, status=status.HTTP_400_BAD_REQUEST)
        relay_point = None
        if relay_point_id:
            try:
                relay_point = RelayPoint.objects.get(pk=relay_point_id, is_active=True)
            except RelayPoint.DoesNotExist:
                return Response({'detail': 'Point relais introuvable.'}, status=status.HTTP_400_BAD_REQUEST)
        installments_count = int(request.data.get('installments_count', 3))
        frequency = request.data.get('frequency', 'monthly')
        down_payment = round(float(order.total_amount) * 0.3, 2)
        remaining = round(float(order.total_amount) - down_payment, 2)
        plan = InstallmentPlan.objects.create(
            order=order,
            relay_point=relay_point,
            total_amount=order.total_amount,
            down_payment=down_payment,
            remaining_amount=remaining,
            installments_count=installments_count,
            frequency=frequency,
            due_date=date.today() + timedelta(days=30),
            status='pending',
        )
        amount_per = round(remaining / installments_count, 2)
        for i in range(installments_count):
            if frequency == 'monthly':
                d = date.today()
                month = d.month + i + 1
                year = d.year + (month - 1) // 12
                month = (month - 1) % 12 + 1
                try:
                    due = d.replace(year=year, month=month)
                except ValueError:
                    import calendar
                    due = d.replace(year=year, month=month, day=calendar.monthrange(year, month)[1])
            else:
                due = date.today() + timedelta(weeks=i + 1)
            Installment.objects.create(plan=plan, amount=amount_per, due_date=due)
        serializer = InstallmentPlanSerializer(plan)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['payments'])
class InstallmentSignContractView(APIView):
    """Client signs the contract for a plan."""
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id):
        try:
            plan = InstallmentPlan.objects.get(pk=plan_id, order__user=request.user)
        except InstallmentPlan.DoesNotExist:
            return Response({'detail': 'Plan introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if plan.contract_signed:
            return Response({'detail': 'Contrat déjà signé.'}, status=status.HTTP_400_BAD_REQUEST)
        plan.contract_signed = True
        plan.contract_signed_at = timezone.now()
        plan.status = 'active'
        plan.save(update_fields=['contract_signed', 'contract_signed_at', 'status'])
        return Response(InstallmentPlanSerializer(plan).data)


@extend_schema(tags=['payments'])
class InstallmentPayView(APIView):
    """Client uploads payment proof for an installment."""
    permission_classes = [IsAuthenticated]

    def post(self, request, installment_id):
        try:
            installment = Installment.objects.select_related('plan__order').get(
                pk=installment_id, plan__order__user=request.user,
            )
        except Installment.DoesNotExist:
            return Response({'detail': 'Versement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if installment.status in ('verified', 'paid'):
            return Response({'detail': 'Ce versement est déjà vérifié.'}, status=status.HTTP_400_BAD_REQUEST)
        plan = installment.plan
        if not plan.contract_signed:
            return Response({'detail': 'Le contrat doit être signé avant de soumettre un paiement.'}, status=status.HTTP_400_BAD_REQUEST)
        proof = request.FILES.get('proof_image')
        if not proof:
            return Response({'detail': 'Veuillez joindre une preuve de paiement.'}, status=status.HTTP_400_BAD_REQUEST)
        installment.proof_image = proof
        installment.payment_method = request.data.get('payment_method', '')
        installment.reference = request.data.get('reference', '')
        installment.status = 'uploaded'
        installment.save(update_fields=['proof_image', 'payment_method', 'reference', 'status'])
        return Response(InstallmentSerializer(installment).data)


# ── Admin installment views ──────────────────────────────────────────────────

@extend_schema(tags=['payments'])
class AdminInstallmentPlanListView(generics.ListAPIView):
    serializer_class = InstallmentPlanSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = InstallmentPlan.objects.select_related(
            'order', 'order__user', 'relay_point'
        ).prefetch_related('installments').order_by('-created_at')
        s = self.request.query_params.get('status')
        if s:
            qs = qs.filter(status=s)
        return qs


@extend_schema(tags=['payments'])
class AdminInstallmentPlanDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_plan(self, pk):
        try:
            return InstallmentPlan.objects.select_related(
                'order', 'order__user', 'relay_point'
            ).prefetch_related('installments').get(pk=pk)
        except InstallmentPlan.DoesNotExist:
            return None

    def get(self, request, pk):
        plan = self._get_plan(pk)
        if not plan:
            return Response({'detail': 'Plan introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(InstallmentPlanSerializer(plan).data)

    def post(self, request, pk):
        """Admin actions: verify, reject, extend, forfeit."""
        plan = self._get_plan(pk)
        if not plan:
            return Response({'detail': 'Plan introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        action = request.data.get('action')
        if action == 'forfeit':
            plan.status = 'forfeited'
            plan.save(update_fields=['status'])
        elif action == 'extend':
            if plan.extension_granted:
                return Response({'detail': 'Prolongation déjà accordée.'}, status=status.HTTP_400_BAD_REQUEST)
            from datetime import timedelta
            import decimal
            plan.extension_granted = True
            plan.extended_due_date = plan.due_date + timedelta(days=15)
            plan.penalty_amount = decimal.Decimal(plan.total_amount) * decimal.Decimal('0.10')
            plan.status = 'extended'
            plan.save(update_fields=['extension_granted', 'extended_due_date', 'penalty_amount', 'status'])
        elif action == 'deliver':
            if plan.stock_deducted:
                return Response({'detail': 'Stock déjà déduit pour ce plan.'}, status=status.HTTP_400_BAD_REQUEST)
            if plan.status not in ('active', 'completed', 'extended'):
                return Response({'detail': 'Le plan doit être actif ou complété pour confirmer la livraison.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                from apps.inventory.services import record_movement
                order = plan.order
                for item in order.items.select_related('product', 'variant').all():
                    record_movement(
                        product=item.product,
                        quantity=-item.quantity,
                        reason='sale',
                        movement_type='out',
                        variant=item.variant if hasattr(item, 'variant') and item.variant_id else None,
                        order=order,
                        notes=f'Livraison paiement échelonné — plan #{plan.id}',
                        performed_by=request.user,
                    )
                plan.stock_deducted = True
                plan.stock_deducted_at = timezone.now()
                plan.status = 'completed'
                plan.save(update_fields=['stock_deducted', 'stock_deducted_at', 'status'])
                order.status = 'delivered'
                order.save(update_fields=['status'])
            except Exception as e:
                return Response({'detail': f'Erreur lors de la déduction du stock : {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({'detail': 'Action invalide (forfeit | extend | deliver).'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(InstallmentPlanSerializer(plan).data)


@extend_schema(tags=['payments'])
class AdminInstallmentVerifyView(APIView):
    """Admin verifies or rejects an uploaded payment proof."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, installment_id):
        try:
            installment = Installment.objects.select_related('plan').get(pk=installment_id)
        except Installment.DoesNotExist:
            return Response({'detail': 'Versement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        action = request.data.get('action')
        if action == 'verify':
            installment.status = 'verified'
            installment.verified_by = request.user
            installment.verified_at = timezone.now()
            installment.paid_at = timezone.now()
            installment.save(update_fields=['status', 'verified_by', 'verified_at', 'paid_at'])
            plan = installment.plan
            if not plan.installments.exclude(status__in=['verified', 'paid']).exists():
                plan.status = 'completed'
                plan.save(update_fields=['status'])
        elif action == 'reject':
            installment.status = 'rejected'
            installment.rejection_reason = request.data.get('reason', '')
            installment.save(update_fields=['status', 'rejection_reason'])
        else:
            return Response({'detail': 'Action invalide (verify | reject).'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(InstallmentSerializer(installment).data)


@extend_schema(tags=['payments'])
class AdminPaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Payment.objects.all().select_related('order', 'order__user')
        status_filter = self.request.query_params.get('status')
        gateway_filter = self.request.query_params.get('gateway')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if gateway_filter:
            qs = qs.filter(gateway=gateway_filter)
        return qs.order_by('-created_at')


@extend_schema(tags=['payments'])
class AdminRefundView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        refunds = Refund.objects.all().select_related('payment', 'payment__order').order_by('-created_at')
        serializer = RefundSerializer(refunds, many=True)
        return Response(serializer.data)

    def post(self, request, refund_id):
        try:
            refund = Refund.objects.get(pk=refund_id)
        except Refund.DoesNotExist:
            return Response({'detail': 'Remboursement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        action = request.data.get('action')
        if action == 'approve':
            refund.status = 'approved'
        elif action == 'reject':
            refund.status = 'rejected'
        elif action == 'process':
            refund.status = 'processed'
            refund.processed_at = timezone.now()
            refund.payment.status = 'refunded'
            refund.payment.save(update_fields=['status'])
            refund.payment.order.payment_status = 'refunded'
            refund.payment.order.status = 'refunded'
            refund.payment.order.save(update_fields=['payment_status', 'status'])
        else:
            return Response({'detail': 'Action invalide.'}, status=status.HTTP_400_BAD_REQUEST)
        refund.save()
        serializer = RefundSerializer(refund)
        return Response(serializer.data)
