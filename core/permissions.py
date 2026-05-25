from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.role == 'admin' or request.user.is_staff or request.user.is_superuser
        )


class IsVendor(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'vendor'


class IsActiveVendor(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.role == 'vendor'):
            return False
        return hasattr(request.user, 'store') and request.user.store.status == 'active'


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'customer'


class IsDelivery(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'delivery'


class IsAffiliate(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'affiliate'


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user and request.user.is_authenticated and (
            request.user.role == 'admin' or request.user.is_staff or request.user.is_superuser
        )


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user and (request.user.role == 'admin' or request.user.is_staff or request.user.is_superuser):
            return True
        user_field = getattr(obj, 'user', None)
        return user_field == request.user


class IsCommercial(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'commercial'


class IsAssistance(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'assistance'


class IsAdminOrAssistance(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.role in ('admin', 'assistance') or
            request.user.is_staff or request.user.is_superuser
        )


class IsAdminOrCommercial(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.role in ('admin', 'commercial') or
            request.user.is_staff or request.user.is_superuser
        )
