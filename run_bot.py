#!/usr/bin/env python
"""
Script to run the Telegram bot separately in polling mode.
This is useful for development or when webhooks are not suitable.
"""

import os
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    # Run the custom management command to start the bot
    execute_from_command_line(['manage.py', 'runbot'])