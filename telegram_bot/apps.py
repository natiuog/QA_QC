from django.apps import AppConfig
import os


class TelegramBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telegram_bot'
    
    def ready(self):
        # Initialize the bot when the app is ready
        from .views import initialize_bot
        initialize_bot()
