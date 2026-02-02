#!/bin/bash

echo "Starting Django Telegram Bot Webhook Server..."

# Collect static files
python manage.py collectstatic --noinput

# Run database migrations
python manage.py migrate

# Start the Django development server in the background
echo "Starting Django server..."
python manage.py runserver 0.0.0.0:8000 &

# Wait a moment for the server to start
sleep 5

echo "Server started successfully!"

# Keep the container running
tail -f /dev/null