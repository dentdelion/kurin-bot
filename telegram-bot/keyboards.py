from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
import config

def get_phone_keyboard():
    """Keyboard for requesting phone number"""
    keyboard = [
        [KeyboardButton("📱 Поділитися номером телефону", request_contact=True)],
        [KeyboardButton("🏠 Головне меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_main_menu_keyboard(is_admin=False):
    """Main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("📚 Переглянути книги", callback_data="browse_books")],
        [InlineKeyboardButton("📖 Мої книги", callback_data="my_books")]
    ]
    
    if is_admin:
        keyboard.extend([
            [InlineKeyboardButton("🔧 Адмін панель", callback_data="admin_panel")]
        ])
    
    return InlineKeyboardMarkup(keyboard)

def get_categories_keyboard():
    """Categories selection keyboard"""
    keyboard = []
    
    # Add categories in rows of 2
    for i in range(0, len(config.BOOK_CATEGORIES), 2):
        row = []
        for j in range(2):
            if i + j < len(config.BOOK_CATEGORIES):
                category = config.BOOK_CATEGORIES[i + j]
                row.append(InlineKeyboardButton(
                    category, 
                    callback_data=f"category_{category}"
                ))
        keyboard.append(row)
    
    # Add "All books" option
    keyboard.append([InlineKeyboardButton("📚 Всі книги", callback_data="category_all")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)

def get_books_navigation_keyboard(page, total_pages, category, books=None, has_prev=True, has_next=True):
    """Books list navigation keyboard"""
    keyboard = []
    
    # Add individual book buttons if books are provided
    if books:
        # Calculate starting number for this page (same as in _format_books_list)
        start_num = page * config.BOOKS_PER_PAGE + 1
        
        # Create rows of book buttons (3 buttons per row for better layout)
        book_buttons = []
        for i, book in enumerate(books, start_num):  # Use enumerate with start_num like in _format_books_list
            book_number = i  # i is already the absolute number due to enumerate(books, start_num)
            status_icon = "📚" if book['is_available'] else "🚫"
            button_text = f"{status_icon} {book_number}"
            book_buttons.append(InlineKeyboardButton(button_text, callback_data=f"book_info_{book['index']}"))
        
        # Arrange buttons in rows of 3
        for i in range(0, len(book_buttons), 3):
            row = book_buttons[i:i+3]
            keyboard.append(row)
    
    # Navigation buttons
    nav_row = []
    if has_prev and page > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"nav_prev_{category}_{page-1}"))
    
    nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="current_page"))
    
    if has_next and page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"nav_next_{category}_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Back button
    keyboard.append([InlineKeyboardButton("⬅️ Назад до категорій", callback_data="browse_books")])
    keyboard.append([InlineKeyboardButton("🏠 Головне меню", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)

def get_book_actions_keyboard(book_index, is_available=True):
    """Book actions keyboard"""
    keyboard = []
    
    if is_available:
        keyboard.append([InlineKeyboardButton("📚 Забронювати", callback_data=f"book_select_{book_index}")])
    
    keyboard.append([InlineKeyboardButton("ℹ️ Детальна інформація", callback_data=f"book_info_{book_index}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад до списку", callback_data="back_to_books")])
    
    return InlineKeyboardMarkup(keyboard)

def get_booking_confirmation_keyboard(book_index):
    """Booking confirmation keyboard"""
    keyboard = [
        [InlineKeyboardButton("✅ Так, бронюю", callback_data=f"confirm_book_{book_index}")],
        [InlineKeyboardButton("❌ Скасувати", callback_data="back_to_books")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_admin_panel_keyboard():
    """Admin panel keyboard"""
    keyboard = [
        [InlineKeyboardButton("📦 Книги до доставки", callback_data="admin_delivery_queue")],
        [InlineKeyboardButton("📚 Позначити як доставлено", callback_data="admin_mark_delivered")],
        [InlineKeyboardButton("🔄 Підтвердити повернення", callback_data="admin_confirm_returns")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_statistics")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_delivery_books_keyboard(books):
    """Keyboard for books in delivery queue"""
    keyboard = []
    
    for book in books:
        keyboard.append([InlineKeyboardButton(
            f"📚 {book['name']} - {book['author']}", 
            callback_data=f"admin_deliver_{book['index']}"
        )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад до адмін панелі", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

def get_user_book_actions_keyboard():
    """User book actions keyboard"""
    keyboard = [
        [InlineKeyboardButton("✅ Забрав книгу", callback_data="user_picked_up")],
        [InlineKeyboardButton("📤 Повернути книгу", callback_data="return_books")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_user_return_books_keyboard(active_books):
    """Keyboard for selecting book to return"""
    keyboard = []
    
    for i, book in enumerate(active_books, 1):
        button_text = f"📚 {i}. {book['display_name']}"
        keyboard.append([InlineKeyboardButton(
            button_text, 
            callback_data=f"return_select_{book['book_id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад до моїх книг", callback_data="my_books")])
    
    return InlineKeyboardMarkup(keyboard)

def get_return_confirmation_keyboard_user(book_id):
    """Return confirmation keyboard for user"""
    keyboard = [
        [InlineKeyboardButton("📷 Надіслати фото та підтвердити", callback_data=f"return_confirm_{book_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="return_books")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_returned_books_keyboard(books):
    """Keyboard for books pending return confirmation"""
    keyboard = []
    
    for book in books:
        keyboard.append([InlineKeyboardButton(
            f"📚 {book['name']} - {book['author']}", 
            callback_data=f"admin_confirm_return_{book['index']}"
        )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад до адмін панелі", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

def get_return_confirmation_keyboard(book_index):
    """Return confirmation keyboard for admin"""
    keyboard = [
        [InlineKeyboardButton("✅ Підтвердити повернення", callback_data=f"admin_confirmed_return_{book_index}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_confirm_returns")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_admin_delivery_actions_keyboard(book_index):
    """Admin delivery actions keyboard"""
    keyboard = [
        [InlineKeyboardButton("✅ Доставлено на полицю", callback_data=f"admin_delivered_{book_index}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_delivery_queue")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_admin_statistics_keyboard():
    """Admin statistics keyboard"""
    keyboard = [
        [InlineKeyboardButton("📈 Топ 10 забраних книг (місяць)", callback_data="admin_stats_top_picked")],
        [InlineKeyboardButton("📋 Загальна статистика", callback_data="admin_stats_general")],
        [InlineKeyboardButton("⬅️ Назад до адмін панелі", callback_data="admin_panel")]
    ]
    
    return InlineKeyboardMarkup(keyboard) 