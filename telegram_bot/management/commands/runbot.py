import asyncio
import logging
from django.core.management.base import BaseCommand
from telegram_bot.views import initialize_bot

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Start the Telegram bot'

    def handle(self, *args, **options):
        self.stdout.write('Starting Telegram bot...')
        bot_app = initialize_bot()
        
        if bot_app:
            self.stdout.write(
                self.style.SUCCESS('Telegram bot initialized successfully')
            )
            # Run the bot until manually stopped
            try:
                bot_app.run_polling()
            except KeyboardInterrupt:
                self.stdout.write('\nStopping bot...')
        else:
            self.stdout.write(
                self.style.ERROR('Failed to initialize Telegram bot')
            )