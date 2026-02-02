# Telegram Document Classification Bot

A Django-based Telegram bot that silently monitors group chats, classifies technical documents, and maintains records in Excel format.

## Features

- **Silent Monitoring**: Runs quietly in group chats without disturbing users
- **Document Classification**: Uses Google Gemini AI to classify documents into:
  - Technical Specification
  - Technical Evaluation
  - After Delivery
  - Terms of Reference
- **Status Tracking**: Identifies if documents are replied and contain scan copies
- **Excel Reporting**: Generates comprehensive reports in Excel format
- **Admin Interface**: Secure admin panel for adding comments
- **Document Query**: Ask bot about specific document status

## Requirements

- Python 3.8+
- Django 4.2.7
- python-telegram-bot 20.7
- google-generativeai 0.4.1
- openpyxl 3.1.2

## Setup Instructions

### 1. Environment Variables

Create a `.env` file in your project root with the following variables:

```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_google_gemini_api_key_here
ADMIN_PASSWORD=your_admin_password_here
```

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd <repository-name>

# Install dependencies
pip install -r telegram_bot_project/requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (optional, for Django admin)
python manage.py createsuperuser
```

### 3. Running the Application

#### For Webhook Mode (Production):

```bash
# Set environment variables
export TELEGRAM_BOT_TOKEN=your_token
export GEMINI_API_KEY=your_gemini_key
export ADMIN_PASSWORD=your_password

# Start the Django server
python manage.py runserver 0.0.0.0:8000
```

Then set up the webhook with Telegram:
```bash
curl -F "url=https://your-domain.com/telegram/webhook/" https://api.telegram.org/bot<TOKEN>/setWebhook
```

#### For Polling Mode (Development):

```bash
# Run the bot separately in polling mode
python run_bot.py
```

### 4. Configuration

#### Webhook URL:
Your webhook endpoint will be: `https://your-domain.com/telegram/webhook/`

#### Health Check:
Monitor bot health at: `https://your-domain.com/telegram/health/`

#### Excel Export:
Download reports at: `https://your-domain.com/telegram/generate-excel/`

#### Document Status API:
Check document status at: `https://your-domain.com/telegram/document-status/?type={type}&project={project_name}`

## Usage

### Bot Commands
- `/start` - Shows main menu with options

### Bot Menu Options
- **Download Excel Report** - Generate and download Excel report
- **Admin Panel** - Access admin features with password
- **Ask Bot** - Query about documents

### Document Processing Flow
1. Documents are posted in monitored group chats
2. Bot analyzes document using Gemini AI
3. Classifies document type and extracts project name
4. Determines if document is replied and has scan copy
5. Saves to database with metadata
6. Updates Excel report

### Admin Functions
- Add comments to documents
- View all processed documents
- Manage document records

## Project Structure

```
├── config/                   # Django project settings
├── telegram_bot/             # Main bot application
│   ├── models.py            # Document model definitions
│   ├── views.py             # Bot logic and webhook handlers
│   ├── urls.py              # URL routing
│   └── management/          # Custom management commands
├── media/                   # Uploaded document storage
├── start_server.sh          # Startup script
├── run_bot.py               # Bot runner script
└── requirements.txt         # Dependencies
```

## Security Notes

- Change the default SECRET_KEY in production
- Restrict ALLOWED_HOSTS to your domain in production
- Use strong passwords for admin access
- Keep API keys secure and never commit to version control

## Deployment

For production deployment, consider:
- Using a WSGI server like Gunicorn
- Reverse proxy with Nginx
- SSL/TLS certificates
- Proper database configuration
- Environment-specific settings

## Troubleshooting

- Make sure your server can accept inbound connections on the webhook URL
- Verify that your bot token and API keys are correctly configured
- Check Django logs for any errors
- Ensure the bot has necessary permissions in the target groups