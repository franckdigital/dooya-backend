from django.apps import AppConfig


class SavConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sav'
    verbose_name = 'SAV'

    def ready(self):
        import apps.sav.signals  # noqa
