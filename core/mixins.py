from rest_framework.response import Response
from rest_framework import status


class SuccessResponseMixin:
    def success_response(self, data=None, message='Opération réussie', status_code=status.HTTP_200_OK):
        return Response({'success': True, 'message': message, 'data': data}, status=status_code)

    def created_response(self, data=None, message='Créé avec succès'):
        return self.success_response(data, message, status.HTTP_201_CREATED)

    def error_response(self, message='Une erreur est survenue', errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({'success': False, 'message': message, 'errors': errors}, status=status_code)
