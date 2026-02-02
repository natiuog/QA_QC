import json
import logging
import tempfile
import os
from datetime import datetime
from io import BytesIO
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.shortcuts import render
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponse
from django.http import FileResponse
import openpyxl
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
import google.generativeai as genai
from .models import Document, DocumentType

logger = logging.getLogger(__name__)

# Initialize the Gemini AI client
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

# Admin password hash (you can generate this using Django's hashing function)
ADMIN_PASSWORD_HASH = make_password(os.environ.get('ADMIN_PASSWORD', 'admin123'))

# Global variable to store the bot application instance
bot_app = None

def initialize_bot():
    """Initialize the Telegram bot application"""
    global bot_app
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set")
        return None
    
    bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    bot_app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    bot_app.add_handler(CommandHandler("start", start_command))
    bot_app.add_handler(CallbackQueryHandler(button_click_handler))
    
    return bot_app

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    keyboard = [
        [InlineKeyboardButton("Download Excel Report", callback_data='download_excel')],
        [InlineKeyboardButton("Admin Panel", callback_data='admin_panel')],
        [InlineKeyboardButton("Ask Bot", callback_data='ask_bot')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        'Welcome to the Technical Document Classification Bot!\n\n'
        'I silently monitor documents in group chats and classify them based on their type.',
        reply_markup=reply_markup
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming documents and classify them using Gemini AI"""
    try:
        # Check if the message is from a group
        if update.effective_chat.type not in ['group', 'supergroup']:
            return  # Only process documents from groups
        
        # Get document info
        document = update.message.document
        file_id = document.file_id
        file_name = document.file_name
        user_name = update.effective_user.full_name
        
        # Download the file
        file = await context.bot.get_file(file_id)
        
        # Save file temporarily
        file_extension = os.path.splitext(file_name)[1]
        temp_file_path = f"/tmp/{file_id}{file_extension}"
        await file.download_to_drive(custom_path=temp_file_path)
        
        # Use Gemini AI to analyze the document
        document_type, project_name, is_replied, scan_copy_present = await analyze_document_with_gemini(temp_file_path, file_name)
        
        # Determine if document is replied and has scan copy
        is_replied = is_replied or scan_copy_present
        
        # Save to database
        doc_entry = Document.objects.create(
            document_type=document_type,
            project_name=project_name,
            user_name=user_name,
            file_name=file_name,
            file_path=temp_file_path,
            is_replied=is_replied,
            scan_copy_present=scan_copy_present,
            remarks="Automatically classified" if document_type else "Could not classify"
        )
        
        # Move file to permanent storage
        file_path = f"documents/{doc_entry.id}_{file_name}"
        with open(temp_file_path, 'rb') as f:
            file_content = ContentFile(f.read(), name=f"{doc_entry.id}_{file_name}")
            saved_path = default_storage.save(file_path, file_content)
            doc_entry.file_path = saved_path
            doc_entry.save()
        
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        logger.info(f"Document processed: {file_name} - Type: {document_type}, Project: {project_name}")
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")

async def analyze_document_with_gemini(file_path, file_name):
    """Analyze document content using Gemini AI to determine type and project"""
    try:
        if not GEMINI_API_KEY:
            # Fallback to filename analysis if no API key
            return analyze_filename_fallback(file_name)
        
        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Convert PDF to text if needed (for now we'll just pass the filename to Gemini)
        prompt = f"""
        Analyze this document and determine:
        1. Document type: Choose from these categories:
           - Technical Specification
           - Technical Evaluation  
           - After Delivery
           - Terms of Reference
        2. Project name: Extract the project name from the document
        3. Is replied: Whether this document indicates a reply (contains 'done', 'replied', or similar)
        4. Scan copy present: Whether the document is a scanned copy (has scan artifacts, low quality images, etc.)
        
        Return the result in JSON format:
        {{
          "document_type": "specification|evaluation|after_delivery|terms_of_reference",
          "project_name": "project name here",
          "is_replied": true|false,
          "scan_copy_present": true|false
        }}
        
        Document name: {file_name}
        """
        
        response = model.generate_content(prompt)
        result = json.loads(response.text.strip())
        
        # Map the response to our choices
        type_mapping = {
            'specification': DocumentType.SPECIFICATION,
            'evaluation': DocumentType.EVALUATION,
            'after_delivery': DocumentType.AFTER_DELIVERY,
            'terms_of_reference': DocumentType.TERMS_OF_REFERENCE
        }
        
        doc_type = type_mapping.get(result.get('document_type', 'specification'), DocumentType.SPECIFICATION)
        project_name = result.get('project_name', 'Unknown Project')
        is_replied = result.get('is_replied', False)
        scan_copy_present = result.get('scan_copy_present', False)
        
        return doc_type, project_name, is_replied, scan_copy_present
        
    except Exception as e:
        logger.error(f"Error analyzing document with Gemini: {str(e)}")
        # Fallback to filename analysis
        return analyze_filename_fallback(file_name)

def analyze_filename_fallback(file_name):
    """Fallback method to analyze document based on filename"""
    file_lower = file_name.lower()
    
    # Determine document type based on keywords in filename
    if 'spec' in file_lower or 'specification' in file_lower:
        doc_type = DocumentType.SPECIFICATION
    elif 'eval' in file_lower or 'evaluation' in file_lower:
        doc_type = DocumentType.EVALUATION
    elif 'delivery' in file_lower or 'after' in file_lower:
        doc_type = DocumentType.AFTER_DELIVERY
    elif 'tor' in file_lower or 'terms' in file_lower or 'reference' in file_lower:
        doc_type = DocumentType.TERMS_OF_REFERENCE
    else:
        doc_type = DocumentType.SPECIFICATION  # Default
    
    # Extract project name (simple approach: take words before document type indicators)
    parts = file_name.split('.')
    name_part = parts[0]  # Remove extension
    project_name = name_part.replace('_', ' ').replace('-', ' ')
    
    # Check if it's replied (contains 'done' or similar)
    is_replied = 'done' in file_lower or 'replied' in file_lower
    
    # Check if it's a scan copy (contains 'scan' or similar)
    scan_copy_present = 'scan' in file_lower or 'scanned' in file_lower
    
    return doc_type, project_name, is_replied, scan_copy_present

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'download_excel':
        # In real implementation, this would trigger a download
        await query.edit_message_text(text="Excel report generation initiated...")
        # Since we can't directly download via inline query, we'll send a message
        await query.message.reply_text("Excel report generated successfully!")
        
    elif query.data.startswith('admin_login_'):
        password = query.data[len('admin_login_'):]
        if check_password(password, ADMIN_PASSWORD_HASH):
            keyboard = [
                [InlineKeyboardButton("Add Comment", callback_data='add_comment')],
                [InlineKeyboardButton("Back to Main Menu", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Admin panel accessed. What would you like to do?", reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="Incorrect password. Access denied.")
    
    elif query.data == 'admin_panel':
        await query.edit_message_text(text="Please enter the admin password:")
        # In real implementation, we'd need to implement a password input mechanism
        # For now, we'll provide a placeholder
        
    elif query.data == 'ask_bot':
        await query.edit_message_text(text="You can ask me questions about documents. What would you like to know?")
    
    elif query.data == 'main_menu':
        keyboard = [
            [InlineKeyboardButton("Download Excel Report", callback_data='download_excel')],
            [InlineKeyboardButton("Admin Panel", callback_data='admin_panel')],
            [InlineKeyboardButton("Ask Bot", callback_data='ask_bot')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text='Welcome to the Technical Document Classification Bot!\n\n'
                 'I silently monitor documents in group chats and classify them based on their type.',
            reply_markup=reply_markup
        )

@csrf_exempt
@require_POST
def telegram_webhook(request):
    """Handle incoming webhook requests from Telegram"""
    global bot_app
    if not bot_app:
        bot_app = initialize_bot()
        if not bot_app:
            return JsonResponse({"error": "Bot initialization failed"}, status=500)
    
    try:
        # Parse the incoming update
        update_json = json.loads(request.body.decode('utf-8'))
        update = Update.de_json(update_json, bot_app.bot)
        
        # Process the update
        bot_app.run_until_complete(bot_app.process_update(update))
        
        return JsonResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

def generate_excel_report(request):
    """Generate and return Excel report of all documents"""
    # Create workbook and worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Document Reports"
    
    # Define headers
    headers = [
        "ID", "Document Type", "Project Name", "User Name", 
        "File Name", "Uploaded At", "Is Replied", 
        "Scan Copy Present", "Remarks", "Comments"
    ]
    
    # Write headers
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")
    
    # Write data rows
    documents = Document.objects.all()
    for row_num, doc in enumerate(documents, 2):
        ws.cell(row=row_num, column=1, value=doc.id)
        ws.cell(row=row_num, column=2, value=doc.get_document_type_display())
        ws.cell(row=row_num, column=3, value=doc.project_name)
        ws.cell(row=row_num, column=4, value=doc.user_name)
        ws.cell(row=row_num, column=5, value=doc.file_name)
        ws.cell(row=row_num, column=6, value=doc.uploaded_at.strftime('%Y-%m-%d %H:%M:%S') if doc.uploaded_at else "")
        ws.cell(row=row_num, column=7, value="Yes" if doc.is_replied else "No")
        ws.cell(row=row_num, column=8, value="Yes" if doc.scan_copy_present else "No")
        ws.cell(row=row_num, column=9, value=doc.remarks or "")
        ws.cell(row=row_num, column=10, value=doc.comments or "")
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        
        adjusted_width = min(max_length + 2, 50)  # Max width of 50
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Save to BytesIO
    from io import BytesIO
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    # Create HTTP response
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=document_report.xlsx'
    
    return response

def health_check(request):
    """Health check endpoint"""
    return JsonResponse({"status": "healthy", "timestamp": timezone.now().isoformat()})

def get_document_status(request):
    """API endpoint to check if a specific document exists and is completed"""
    doc_type = request.GET.get('type')
    project = request.GET.get('project')
    user = request.GET.get('user')
    
    if doc_type and project:
        # Find matching documents
        docs = Document.objects.filter(
            document_type=doc_type,
            project_name__icontains=project
        )
        
        if user:
            docs = docs.filter(user_name__icontains=user)
        
        if docs.exists():
            completed_docs = docs.filter(scan_copy_present=True)
            if completed_docs.exists():
                return JsonResponse({
                    "exists": True,
                    "completed": True,
                    "message": f"Yes, the {doc_type} document for {project} has been sent and completed."
                })
            else:
                return JsonResponse({
                    "exists": True,
                    "completed": False,
                    "message": f"Yes, the {doc_type} document for {project} has been sent but is not yet completed."
                })
    
    return JsonResponse({
        "exists": False,
        "completed": False,
        "message": "Document not found in records."
    })
