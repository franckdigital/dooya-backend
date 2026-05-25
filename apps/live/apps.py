from django.apps import AppConfig


class LiveConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.live'
    verbose_name = 'Live Shopping'

    def ready(self):
        import apps.live.signals  # noqa
