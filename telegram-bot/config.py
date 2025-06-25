import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [id.strip() for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://root:password@localhost:3306/kurin_bot')

# Google Sheets configuration
GOOGLE_SHEETS_URL = os.getenv('GOOGLE_SHEETS_URL', '')
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', 'Books')  # Name of the worksheet

ALLOWED_TIME_TO_READ_THE_BOOK = int(os.getenv('ALLOWED_TIME_TO_READ_THE_BOOK', '14'))
RULES_TEXT = os.getenv('RULES_TEXT', 'Правила користування бібліотекою будуть тут...')

# Book categories
BOOK_CATEGORIES = [
    'історія',
    'політологія', 
    'антропологія',
    'соціологія',
    'українська література',
    'світова література',
    'в оригіналі',
    'художня література',
    'літературознавство',
    'краєзнавство',
    'філософія',
    'суспільствознавство',
    'мовознавство',
    'нон-фікшен',
    'мистецтво',
    'архітектура',
    'музика',
    'кіно',
    'зіни',
    'комікси',
    'біографії',
    'нові надходження'
]

# Excel column mappings
EXCEL_COLUMNS = {
    'id': 'id',
    'name': 'Назва',
    'author': 'Автор', 
    'edition': 'Видавництво та рік видання',
    'pages': 'К-сть с.',
    'description': 'Короткий опис',
    'booked_until': 'Заброньовано до:',
    'categories': 'Categories',
    'status': 'Status'
}

# Status values
STATUS_VALUES = {
    'BOOKED': 'booked',
    'RETURNED': 'returned',
    'EMPTY': '',
    'IN_QUEUE_FOR_DELIVERY': 'in queue for delivery',
    'DELIVERED': 'delivered'
}

# Pagination
BOOKS_PER_PAGE = 10 