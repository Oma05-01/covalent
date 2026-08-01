from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        # Import the signals so the @receiver decorators get registered
        import accounts.signals