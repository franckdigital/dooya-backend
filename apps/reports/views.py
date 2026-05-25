from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin
from core.pagination import StandardPagination
from .models import Report
from .serializers import ReportSerializer, ReportRequestSerializer


@extend_schema(tags=['reports'])
class ReportListView(generics.ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Report.objects.filter(generated_by=self.request.user).order_by('-created_at')


@extend_schema(tags=['reports'])
class ReportRequestView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        serializer = ReportRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        report = serializer.save(generated_by=request.user)
        from .tasks import generate_report
        generate_report.delay(report.pk)
        return Response(ReportSerializer(report, context={'request': request}).data, status=status.HTTP_202_ACCEPTED)


@extend_schema(tags=['reports'])
class ReportDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            report = Report.objects.get(pk=pk, generated_by=request.user)
        except Report.DoesNotExist:
            if request.user.role == 'admin':
                try:
                    report = Report.objects.get(pk=pk)
                except Report.DoesNotExist:
                    return Response({'detail': 'Rapport introuvable.'}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({'detail': 'Rapport introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if report.status != 'ready' or not report.file:
            return Response({'detail': f'Rapport non disponible. Statut: {report.status}'}, status=status.HTTP_400_BAD_REQUEST)
        from django.http import FileResponse
        return FileResponse(report.file.open(), as_attachment=True, filename=f'{report.name}.xlsx')


@extend_schema(tags=['reports'])
class AdminReportView(generics.ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Report.objects.all().select_related('generated_by')
        report_type = self.request.query_params.get('type')
        report_status = self.request.query_params.get('status')
        if report_type:
            qs = qs.filter(type=report_type)
        if report_status:
            qs = qs.filter(status=report_status)
        return qs.order_by('-created_at')
