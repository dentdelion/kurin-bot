import logging
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

import config
from google_sheets_manager import GoogleSheetsManager
from user_manager import UserManager
from notifications import NotificationManager
import keyboards

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class LibraryBot:
    def __init__(self):
        self.application = Application.builder().token(config.BOT_TOKEN).build()
        try:
            self.sheets_manager = GoogleSheetsManager()
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
            raise
        
        self.user_manager = UserManager()
        self.notification_manager = NotificationManager(self.application.bot)
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all command and callback handlers"""
        # Commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Contact handler for phone number
        self.application.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))
        
        # Photo handler for book returns
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        # Callback handlers
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        if self.user_manager.is_user_registered(user_id):
            # User is registered, show main menu
            is_admin = str(user_id) in config.ADMIN_IDS
            await update.message.reply_text(
                "🏠 Головне меню",
                reply_markup=keyboards.get_main_menu_keyboard(is_admin)
            )
        else:
            # Request registration
            await update.message.reply_text(
                "👋 Вітаємо в бібліотеці!\n\n"
                "Для користування ботом потрібно зареєструватися. "
                "Будь ласка, поділіться вашим номером телефону:",
                reply_markup=keyboards.get_phone_keyboard()
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "📚 <b>Довідка по боту бібліотеки</b>\n\n"
            "🔹 /start - головне меню\n"
            "🔹 /help - ця довідка\n\n"
            "<b>Як користуватися:</b>\n"
            "1. Оберіть категорію книг\n"
            "2. Переглядайте список книг\n"
            "3. Забронюйте потрібну книгу\n"
            "4. Дочекайтеся доставки на полицю\n"
            "5. Заберіть книгу та підтвердіть в боті\n"
            "6. Поверніть книгу вчасно\n\n"
            "❓ При проблемах звертайтеся до адміністраторів"
        )
        
        await update.message.reply_text(help_text, parse_mode='HTML')
    
    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle contact sharing for registration"""
        contact = update.message.contact
        user_id = update.effective_user.id
        
        # Register user
        self.user_manager.register_user(
            user_id=user_id,
            phone_number=contact.phone_number,
            first_name=contact.first_name,
            last_name=contact.last_name
        )
        
        # Show main menu
        is_admin = str(user_id) in config.ADMIN_IDS
        await update.message.reply_text(
            "✅ Реєстрацію завершено!\n\n🏠 Головне меню:",
            reply_markup=keyboards.get_main_menu_keyboard(is_admin)
        )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo for book return"""
        user_id = update.effective_user.id
        
        if not self.user_manager.is_user_registered(user_id):
            await update.message.reply_text("Спочатку потрібно зареєструватися. Використайте /start")
            return
        
        # Store photo for book return (this would be enhanced to track which book is being returned)
        photo = update.message.photo[-1]  # Get highest resolution
        
        # For now, just acknowledge receipt
        await update.message.reply_text(
            "📷 Фото отримано! Адміністратори будуть повідомлені про повернення книги.",
            reply_markup=keyboards.get_return_confirmation_keyboard()
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        
        # Check registration for non-admin callbacks
        if not data.startswith('admin_') and not self.user_manager.is_user_registered(user_id):
            await query.edit_message_text("Спочатку потрібно зареєструватися. Використайте /start")
            return
        
        try:
            # Route callbacks
            if data == "browse_books":
                await self._handle_browse_books(query)
            elif data == "my_books":
                await self._handle_my_books(query)
            elif data == "back_to_main":
                await self._handle_back_to_main(query)
            elif data.startswith("category_"):
                await self._handle_category_selection(query, data)
            elif data.startswith("nav_"):
                await self._handle_navigation(query, data)
            elif data.startswith("book_select_"):
                await self._handle_book_selection(query, data)
            elif data.startswith("book_info_"):
                await self._handle_book_info(query, data)
            elif data.startswith("confirm_book_"):
                await self._handle_book_confirmation(query, data)
            elif data.startswith("admin_"):
                await self._handle_admin_callbacks(query, data)
            elif data == "user_picked_up":
                await self._handle_user_picked_up(query)
            elif data == "user_returned":
                await self._handle_user_returned(query)
            elif data == "confirm_return":
                await self._handle_confirm_return(query)
            elif data == "back_to_books":
                await self._handle_back_to_books(query)
        except Exception as e:
            logger.error(f"Error handling callback {data}: {e}")
            await query.edit_message_text(
                "❌ Виникла помилка при обробці запиту. "
                "Можливо, проблема з підключенням до Google Sheets. "
                "Спробуйте пізніше або зверніться до адміністратора."
            )
    
    async def _handle_browse_books(self, query):
        """Handle browse books callback"""
        await query.edit_message_text(
            "📚 Оберіть категорію книг:",
            reply_markup=keyboards.get_categories_keyboard()
        )
    
    async def _handle_my_books(self, query):
        """Handle my books callback"""
        user_id = query.from_user.id
        # This would show user's current books
        await query.edit_message_text(
            "📖 Ваші книги:\n\n"
            "Тут будуть показані ваші поточні книги...",
            reply_markup=keyboards.get_user_book_actions_keyboard()
        )
    
    async def _handle_back_to_main(self, query):
        """Handle back to main menu"""
        user_id = query.from_user.id
        is_admin = str(user_id) in config.ADMIN_IDS
        
        await query.edit_message_text(
            "🏠 Головне меню",
            reply_markup=keyboards.get_main_menu_keyboard(is_admin)
        )
    
    async def _handle_category_selection(self, query, data):
        """Handle category selection"""
        category = data.replace("category_", "")
        user_id = query.from_user.id
        
        # Update user's current category
        self.user_manager.update_user_category(user_id, category)
        
        # Get books for this category
        books, total_books = self.sheets_manager.get_books_by_category(category, page=0)
        
        if not books:
            await query.edit_message_text(
                f"📚 Категорія: {category}\n\n"
                "Книг в цій категорії поки немає.",
                reply_markup=keyboards.get_categories_keyboard()
            )
            return
        
        # Format books list
        books_text = self._format_books_list(books, category, 0, total_books)
        total_pages = (total_books + config.BOOKS_PER_PAGE - 1) // config.BOOKS_PER_PAGE
        
        await query.edit_message_text(
            books_text,
            reply_markup=keyboards.get_books_navigation_keyboard(0, total_pages, category, books),
            parse_mode='HTML'
        )
    
    async def _handle_navigation(self, query, data):
        """Handle pagination navigation"""
        parts = data.split("_")
        direction = parts[1]  # prev or next
        category = parts[2]
        page = int(parts[3])
        
        user_id = query.from_user.id
        self.user_manager.update_user_page(user_id, page)
        
        books, total_books = self.sheets_manager.get_books_by_category(category, page)
        books_text = self._format_books_list(books, category, page, total_books)
        total_pages = (total_books + config.BOOKS_PER_PAGE - 1) // config.BOOKS_PER_PAGE
        
        await query.edit_message_text(
            books_text,
            reply_markup=keyboards.get_books_navigation_keyboard(page, total_pages, category, books),
            parse_mode='HTML'
        )
    
    async def _handle_book_selection(self, query, data):
        """Handle book selection for booking"""
        book_index = int(data.replace("book_select_", ""))
        book = self.sheets_manager.get_book_by_index(book_index)
        
        if not book:
            await query.edit_message_text("❌ Книга не знайдена.")
            return
        
        if not book['is_available']:
            await query.edit_message_text("❌ Ця книга вже заброньована.")
            return
        
        # Show booking confirmation
        book_text = (
            f"📚 <b>{book['name']}</b>\n"
            f"👤 <b>Автор:</b> {book['author']}\n"
            f"📖 <b>Видавництво:</b> {book['edition']}\n\n"
            "Ви дійсно хочете забронювати цю книгу?\n\n"
            "⚠️ Після підтвердження книга буде доставлена на полицю протягом 1-2 днів."
        )
        
        await query.edit_message_text(
            book_text,
            reply_markup=keyboards.get_booking_confirmation_keyboard(book_index),
            parse_mode='HTML'
        )
    
    async def _handle_book_info(self, query, data):
        """Handle book info request"""
        book_index = int(data.replace("book_info_", ""))
        book = self.sheets_manager.get_book_by_index(book_index)
        
        if not book:
            await query.edit_message_text("❌ Книга не знайдена.")
            return
        
        status = "✅ Доступна" if book['is_available'] else "❌ Заброньована"
        
        book_text = (
            f"📚 <b>{book['name']}</b>\n"
            f"👤 <b>Автор:</b> {book['author']}\n"
            f"📖 <b>Видавництво:</b> {book['edition']}\n"
            f"📄 <b>Сторінок:</b> {book['pages']}\n"
            f"📋 <b>Опис:</b> {book['description']}\n"
            f"🏷️ <b>Категорії:</b> {book['categories']}\n"
            f"📊 <b>Статус:</b> {status}"
        )
        
        await query.edit_message_text(
            book_text,
            reply_markup=keyboards.get_book_actions_keyboard(book_index, book['is_available']),
            parse_mode='HTML'
        )
    
    async def _handle_book_confirmation(self, query, data):
        """Handle book booking confirmation"""
        book_index = int(data.replace("confirm_book_", ""))
        user_id = query.from_user.id
        
        # Get book and user info
        book = self.sheets_manager.get_book_by_index(book_index)
        user = self.user_manager.get_user(user_id)
        
        if not book or not book['is_available']:
            await query.edit_message_text("❌ Книга більше недоступна для бронювання.")
            return
        
        # Book the item
        user_name = self.user_manager.get_user_display_name(user_id)
        try:
            self.sheets_manager.book_item(book_index, user_id, user_name)
            
            # Add to user history
            self.user_manager.add_book_to_history(user_id, book_index, "booked")
            
            # Send notifications to admins - get user info safely
            book_info = {
                'name': book['name'],
                'author': book['author'],
                'edition': book['edition']
            }
            
            # Get phone number safely
            phone_number = "не вказано"
            if user and 'phone_number' in user:
                phone_number = user['phone_number']
            
            user_info = {
                'name': user_name,
                'phone': phone_number
            }
            
            await self.notification_manager.notify_admins_book_requested(book_info, user_info)
            
            # Send rules to user
            await self.notification_manager.send_rules_to_user(user_id)
            
            logger.info(f"Book {book_index} successfully booked by user {user_id} ({user_name}), admin notifications sent")
            
            await query.edit_message_text(
                f"✅ Книга '{book['name']}' успішно заброньована!\n\n"
                "📋 Правила користування надіслані в окремому повідомленні.\n"
                "📦 Адміністраторів повідомлено про доставку.\n"
                "⏰ Очікуйте повідомлення про готовність книги (1-2 дні)."
            )
        except Exception as e:
            logger.error(f"Failed to book item: {e}")
            await query.edit_message_text("❌ Помилка при бронюванні книги. Спробуйте пізніше.")
    
    async def _handle_admin_callbacks(self, query, data):
        """Handle admin panel callbacks"""
        user_id = query.from_user.id
        
        if str(user_id) not in config.ADMIN_IDS:
            await query.edit_message_text("❌ Доступ заборонено.")
            return
        
        try:
            if data == "admin_panel":
                await query.edit_message_text(
                    "🔧 Адміністративна панель",
                    reply_markup=keyboards.get_admin_panel_keyboard()
                )
            elif data == "admin_delivery_queue":
                books = self.sheets_manager.get_books_for_delivery()
                logger.info(f"Admin {user_id} requested delivery queue, found {len(books)} books")
                
                if books:
                    await query.edit_message_text(
                        f"📦 Книги до доставки ({len(books)}):",
                        reply_markup=keyboards.get_delivery_books_keyboard(books)
                    )
                else:
                    # Show debug information if no books are found
                    try:
                        # Try to read all books and see how many have in_queue_for_delivery = 'yes'
                        df = self.sheets_manager.read_books()
                        if not df.empty:
                            total_books = len(df)
                            in_queue_count = len(df[df[config.EXCEL_COLUMNS['in_queue_for_delivery']].astype(str).str.lower() == 'yes'])
                            debug_text = (
                                f"📦 Немає книг для доставки\n\n"
                                f"🔍 Відладочна інформація:\n"
                                f"Всього книг в таблиці: {total_books}\n"
                                f"Книг з 'In queue for delivery' = 'yes': {in_queue_count}\n\n"
                                f"Перевірте, чи є книги з позначкою 'yes' в колонці 'In queue for delivery'"
                            )
                        else:
                            debug_text = "📦 Немає книг для доставки\n\n❌ Не вдалося прочитати дані з таблиці"
                    except Exception as debug_e:
                        logger.error(f"Debug info error: {debug_e}")
                        debug_text = f"📦 Немає книг для доставки\n\n❌ Помилка отримання відладочної інформації: {debug_e}"
                    
                    await query.edit_message_text(
                        debug_text,
                        reply_markup=keyboards.get_admin_panel_keyboard()
                    )
            elif data.startswith("admin_deliver_"):
                book_index = int(data.replace("admin_deliver_", ""))
                book = self.sheets_manager.get_book_by_index(book_index)
                if book:
                    await query.edit_message_text(
                        f"📚 {book['name']}\n👤 {book['author']}\n\nПідтвердити доставку на полицю?",
                        reply_markup=keyboards.get_admin_delivery_actions_keyboard(book_index)
                    )
            elif data.startswith("admin_delivered_"):
                book_index = int(data.replace("admin_delivered_", ""))
                try:
                    self.sheets_manager.mark_as_delivered(book_index)
                    book = self.sheets_manager.get_book_by_index(book_index)
                    # Here we would notify the user who booked the book
                    await query.edit_message_text("✅ Книга позначена як доставлена на полицю!")
                except Exception as e:
                    logger.error(f"Failed to mark book as delivered: {e}")
                    await query.edit_message_text("❌ Помилка при позначенні книги як доставленої.")
        except Exception as e:
            logger.error(f"Error in admin callback {data}: {e}")
            await query.edit_message_text(
                "❌ Виникла помилка при роботі з Google Sheets. "
                "Перевірте підключення та спробуйте пізніше."
            )
    
    async def _handle_user_picked_up(self, query):
        """Handle user picked up book"""
        user_id = query.from_user.id
        # This would be enhanced to track which specific book was picked up
        await query.edit_message_text(
            "✅ Дякуємо! Книга позначена як забрана.\n"
            "📅 Не забувайте повернути її вчасно!"
        )
    
    async def _handle_user_returned(self, query):
        """Handle user returned book"""
        await query.edit_message_text(
            "📤 Для повернення книги:\n\n"
            "1. Покладіть книгу на полицю\n"
            "2. Зробіть фото книги на полиці\n"
            "3. Надішліть фото в цей чат\n\n"
            "📷 Очікую фото..."
        )
    
    async def _handle_confirm_return(self, query):
        """Handle confirm book return"""
        await query.edit_message_text(
            "✅ Повернення підтверджено!\n"
            "Адміністраторів повідомлено про необхідність забрати книгу."
        )
    
    async def _handle_back_to_books(self, query):
        """Handle back to books list"""
        user_id = query.from_user.id
        user_data = self.user_manager.get_user(user_id)
        
        if user_data and 'current_category' in user_data:
            category = user_data['current_category']
            page = user_data.get('current_page', 0)
            
            # Get books for current category and page
            books, total_books = self.sheets_manager.get_books_by_category(category, page)
            books_text = self._format_books_list(books, category, page, total_books)
            total_pages = (total_books + config.BOOKS_PER_PAGE - 1) // config.BOOKS_PER_PAGE
            
            await query.edit_message_text(
                books_text,
                reply_markup=keyboards.get_books_navigation_keyboard(page, total_pages, category, books),
                parse_mode='HTML'
            )
        else:
            # Fallback to categories if no current category
            await query.edit_message_text(
                "📚 Оберіть категорію книг:",
                reply_markup=keyboards.get_categories_keyboard()
            )
    
    def _format_books_list(self, books, category, page, total_books):
        """Format books list for display"""
        start_num = page * config.BOOKS_PER_PAGE + 1
        
        text = f"📚 <b>Категорія:</b> {category}\n"
        text += f"📖 <b>Книги {start_num}-{start_num + len(books) - 1} з {total_books}</b>\n\n"
        
        for i, book in enumerate(books, start_num):
            status = "" if book['is_available'] else " (заброньовано)"
            text += f"{i}. <b>{book['name']}</b>{status}\n"
            text += f"   👤 {book['author']}\n"
            text += f"   📖 {book['edition']}\n\n"
        
        return text
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Library Bot...")
        self.application.run_polling()

if __name__ == "__main__":
    try:
        bot = LibraryBot()
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print("❌ Bot failed to start. Please check your Google Sheets configuration.")
        print("Run 'python setup_google_sheets.py' to validate your setup.")
        exit(1) 