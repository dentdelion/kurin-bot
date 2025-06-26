import logging
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from datetime import datetime
import pandas as pd

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
        
        # Store pending returns (user_id -> book_id)
        self.pending_returns = {}
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all command and callback handlers"""
        # Commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Contact handler for phone number
        self.application.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))
        
        # Main menu text handler
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🏠 Головне меню$"), self.handle_main_menu_text))
        
        # Photo handler for book returns
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        # Callback handlers
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        try:
            # Check if user is registered with error handling
            is_registered = self.user_manager.is_user_registered(user_id)
            logger.info(f"User {user_id} registration check: {is_registered}")
            
            if is_registered:
                # User is registered, show main menu
                is_admin = str(user_id) in config.ADMIN_IDS
                logger.info(f"Showing main menu to registered user {user_id} (admin: {is_admin})")
                await update.message.reply_text(
                    "🏠 Головне меню",
                    reply_markup=keyboards.get_main_menu_keyboard(is_admin)
                )
            else:
                # User not registered, request registration
                logger.info(f"Requesting registration from unregistered user {user_id}")
                await update.message.reply_text(
                    "👋 Вітаємо в бібліотеці!\n\n"
                    "Для користування ботом потрібно зареєструватися. "
                    "Будь ласка, поділіться вашим номером телефону:",
                    reply_markup=keyboards.get_phone_keyboard()
                )
        except Exception as e:
            logger.error(f"Error in start_command for user {user_id}: {e}")
            # Fallback to registration request if there's an error
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
    
    async def handle_main_menu_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle main menu text button"""
        user_id = update.effective_user.id
        
        try:
            # Check if user is registered
            is_registered = self.user_manager.is_user_registered(user_id)
            
            if is_registered:
                # User is registered, show main menu
                is_admin = str(user_id) in config.ADMIN_IDS
                logger.info(f"Showing main menu to registered user {user_id} via text button")
                await update.message.reply_text(
                    "🏠 Головне меню",
                    reply_markup=keyboards.get_main_menu_keyboard(is_admin)
                )
            else:
                # User not registered, show registration message
                logger.info(f"User {user_id} tried to access main menu but not registered")
                await update.message.reply_text(
                    "❌ Спочатку потрібно зареєструватися.\n\n"
                    "Для користування ботом потрібно поділитися номером телефону:",
                    reply_markup=keyboards.get_phone_keyboard()
                )
        except Exception as e:
            logger.error(f"Error in handle_main_menu_text for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ Виникла помилка. Спробуйте ще раз або використайте команду /start"
            )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo for book return"""
        user_id = update.effective_user.id
        
        if not self.user_manager.is_user_registered(user_id):
            await update.message.reply_text("Спочатку потрібно зареєструватися. Використайте /start")
            return
        
        
        # Process book return
        book_id = self.pending_returns[user_id]
        photo = update.message.photo[-1]  # Get highest resolution
        
        try:
            # Get book and user info for notifications
            book_name = self._get_book_name_by_id(book_id)
            if not book_name:
                book_name = f"Книга ID: {book_id}"
            
            user_info = self.user_manager.get_user(user_id)
            user_display_name = self.user_manager.get_user_display_name(user_id)
            
            # Prepare book info for admin notification
            book_info = {
                'name': book_name.split(' - ')[0] if ' - ' in book_name else book_name,
                'author': book_name.split(' - ')[1] if ' - ' in book_name else 'Невідомий автор'
            }
            
            # Prepare user info for admin notification
            user_notification_info = {
                'name': user_display_name,
                'phone': user_info.get('phone_number', 'не вказано') if user_info else 'не вказано'
            }
            
            # Mark book as returned in Google Sheets
            try:
                # Find book in sheets and mark as returned
                df = self.sheets_manager.read_books()
                if not df.empty:
                    book_row = df[df[config.EXCEL_COLUMNS['id']].astype(str) == str(book_id)]
                    if not book_row.empty:
                        book_index = book_row.index[0]
                        # Mark as returned by user (waiting for admin confirmation)
                        self.sheets_manager.mark_as_returned_by_user(book_index)
                        logger.info(f"Book {book_id} marked as returned by user {user_id} in Google Sheets")
            except Exception as sheets_error:
                logger.error(f"Error updating Google Sheets for return: {sheets_error}")
                # Continue with notification even if sheets update fails
            
            # Mark as returned in local database
            self.user_manager.mark_book_returned(user_id, book_id)
            
            # Send notification to admins with photo
            await self.notification_manager.notify_admins_book_returned(
                book_info, 
                user_notification_info, 
                photo_id=photo.file_id
            )
            
            # Clear pending return
            del self.pending_returns[user_id]
            
            # Acknowledge to user
            await update.message.reply_text(
                f"✅ <b>Повернення підтверджено!</b>\n\n"
                f"📚 <b>Книга:</b> {book_info['name']}\n\n"
                f"📷 Фото отримано та передано адміністраторам.\n"
                f"Адміністратор забере книгу з полиці та підтвердить повернення в системі.\n\n"
                f"Дякуємо за користування бібліотекою! 📖",
                parse_mode='HTML'
            )
            
            logger.info(f"Book {book_id} return processed with photo for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing book return photo for user {user_id}, book {book_id}: {e}")
            await update.message.reply_text(
                "❌ Виникла помилка при обробці повернення книги. "
                "Спробуйте ще раз або зверніться до адміністратора."
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
            elif data == "return_books":
                await self._handle_return_books(query)
            elif data.startswith("return_select_"):
                await self._handle_return_book_selection(query, data)
            elif data.startswith("return_confirm_"):
                await self._handle_return_confirmation(query, data)
            elif data == "user_returned":
                await self._handle_user_returned(query)
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
        
        try:
            active_books = self.user_manager.get_user_active_books(user_id)
            
            if not active_books:
                text = "📖 <b>Ваші книги</b>\n\n У вас немає активних книг"
            else:
                # Read books data once to avoid multiple API calls
                try:
                    books_df = self.sheets_manager.read_books()
                except Exception as e:
                    logger.error(f"Failed to read books from Google Sheets: {e}")
                    books_df = pd.DataFrame()  # Empty dataframe as fallback
                
                text, ready_for_pickup = self._build_user_books_text(active_books, books_df)
                
                # Add special message if books are ready for pickup
                if ready_for_pickup:
                    text += "💡 <b>Увага:</b> У вас є книги готові до отримання! Натисніть '✅ Забрав книгу' після того, як заберете їх з полиці.\n\n"
            
            await query.edit_message_text(
                text,
                reply_markup=keyboards.get_user_book_actions_keyboard(),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error getting user books: {e}")
            await query.edit_message_text(
                "❌ Помилка отримання інформації про ваші книги",
                reply_markup=keyboards.get_user_book_actions_keyboard()
            )
    
    def _build_user_books_text(self, active_books, books_df):
        """Build the text for user's active books"""
        text = "📖 <b>Ваші активні книги:</b>\n\n"
        ready_for_pickup = []
        
        for book in active_books:
            book_id = book['book_id']
            book_name = self._get_book_name_by_id_cached(book_id, books_df)
            if not book_name:
                book_name = f"Книга ID: {book_id}"
            
            book_status, is_ready_for_pickup = self._determine_book_status(book, book_id, books_df)
            if is_ready_for_pickup:
                ready_for_pickup.append(book_id)
            
            text += f"📚 <b>{book_name}</b>\n"
            text += f"🗓 Заброньовано: {book['date_booked'].strftime('%d.%m.%Y')}\n"
            text += f"📅 Повернути до: {book['expiry_date'].strftime('%d.%m.%Y')}\n"
            text += f"{book_status}\n\n"
        
        return text, ready_for_pickup
    
    def _determine_book_status(self, book, book_id, books_df):
        """Determine the status of a user's book"""
        days_since_booking = (datetime.now() - book['date_booked']).days
        days_left_text = f"📅 Залишилось днів: {book['days_left']}"
        
        # Check if book is overdue
        if book['days_left'] <= 0:
            return "⏰ Прострочено", False
        
        # Check if book is ready for pickup (status is 'delivered')
        try:
            if not books_df.empty:
                book_row = books_df[books_df[config.EXCEL_COLUMNS['id']].astype(str) == str(book_id)]
                if not book_row.empty:
                    row = book_row.iloc[0]
                    status = row[config.EXCEL_COLUMNS['status']]
                    
                    # If status is 'delivered', book is ready for pickup
                    if str(status).lower() == config.STATUS_VALUES['DELIVERED']:
                        return "📦 Готова до отримання!", True
                    
                    return days_left_text, False
                
            return days_left_text, False
        except Exception as e:
            logger.error(f"Error checking book status for {book_id}: {e}")
            return days_left_text, False
    
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
            
            # Add to database statistics using book_id instead of book_name
            book_id = book['id']  # Use the book ID from the sheet
            self.user_manager.add_book_to_statistics(user_id, book_id)
            
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
                await self._handle_admin_panel(query)
            elif data == "admin_delivery_queue":
                await self._handle_admin_delivery_queue(query)
            elif data == "admin_mark_delivered":
                await self._handle_admin_mark_delivered(query)
            elif data == "admin_confirm_returns":
                await self._handle_admin_confirm_returns(query)
            elif data.startswith("admin_deliver_"):
                await self._handle_admin_deliver_book(query, data)
            elif data.startswith("admin_delivered_"):
                await self._handle_admin_book_delivered(query, data)
            elif data.startswith("admin_confirm_return_"):
                await self._handle_admin_confirm_return(query, data)
            elif data.startswith("admin_confirmed_return_"):
                await self._handle_admin_confirmed_return(query, data)
        except Exception as e:
            logger.error(f"Error in admin callback {data}: {e}")
            await query.edit_message_text(
                "❌ Виникла помилка при роботі з базою даних. "
                "Перевірте підключення та спробуйте пізніше."
            )
    
    async def _handle_admin_panel(self, query):
        """Handle admin panel main menu"""
        await query.edit_message_text(
            "🔧 Адміністративна панель",
            reply_markup=keyboards.get_admin_panel_keyboard()
        )
    
    async def _handle_admin_delivery_queue(self, query):
        """Handle admin delivery queue request"""
        user_id = query.from_user.id
        books = self.sheets_manager.get_books_for_delivery()
        logger.info(f"Admin {user_id} requested delivery queue, found {len(books)} books")
        
        if books:
            await query.edit_message_text(
                f"📦 Книги до доставки ({len(books)}):",
                reply_markup=keyboards.get_delivery_books_keyboard(books)
            )
        else:
            # Show debug information if no books are found
            debug_text = await self._get_delivery_debug_info("📦 Немає книг для доставки")
            await query.edit_message_text(
                debug_text,
                reply_markup=keyboards.get_admin_panel_keyboard()
            )
    
    async def _handle_admin_mark_delivered(self, query):
        """Handle admin mark delivered request"""
        user_id = query.from_user.id
        books = self.sheets_manager.get_books_for_delivery()
        logger.info(f"Admin {user_id} requested mark delivered, found {len(books)} books")
        
        if books:
            await query.edit_message_text(
                f"📚 Оберіть книгу для позначення як доставлена ({len(books)}):",
                reply_markup=keyboards.get_delivery_books_keyboard(books)
            )
        else:
            # Show debug information if no books are found
            debug_text = await self._get_delivery_debug_info("📚 Немає книг для позначення як доставлено")
            await query.edit_message_text(
                debug_text,
                reply_markup=keyboards.get_admin_panel_keyboard()
            )
    
    async def _handle_admin_deliver_book(self, query, data):
        """Handle admin book delivery confirmation request"""
        book_index = int(data.replace("admin_deliver_", ""))
        book = self.sheets_manager.get_book_by_index(book_index)
        
        if book:
            await query.edit_message_text(
                f"📚 {book['name']}\n👤 {book['author']}\n\nПідтвердити доставку на полицю?",
                reply_markup=keyboards.get_admin_delivery_actions_keyboard(book_index)
            )
        else:
            await query.edit_message_text("❌ Книга не знайдена.")
    
    async def _handle_admin_book_delivered(self, query, data):
        """Handle admin book delivered confirmation"""
        book_index = int(data.replace("admin_delivered_", ""))
        
        try:
            # Get book info before marking as delivered
            book = self.sheets_manager.get_book_by_index(book_index)
            if not book:
                await query.edit_message_text("❌ Книга не знайдена.")
                return
            
            logger.info(f"Admin marking book as delivered: index={book_index}, book_id={book['id']}, name={book['name']}")
            
            # Mark as delivered in sheets
            self.sheets_manager.mark_as_delivered(book_index)
            
            # Find the user who booked this book
            book_id = book['id']
            logger.info(f"Looking for user with active book_id: {book_id}")
            user_info = self.user_manager.get_user_with_active_book(book_id)
            
            if user_info:
                logger.info(f"Found user for book delivery: user_id={user_info['user_id']}, user_name={user_info['user_name']}")
                
                # Prepare book info for notification
                book_info = {
                    'name': book['name'],
                    'author': book['author']
                }
                
                # Send notification to user
                try:
                    await self.notification_manager.notify_user_book_ready(user_info['user_id'], book_info)
                    logger.info(f"✅ Successfully sent book ready notification to user {user_info['user_id']} for book {book['name']}")
                except Exception as notify_error:
                    logger.error(f"❌ Failed to send notification to user {user_info['user_id']}: {notify_error}")
                    # Continue with the admin response even if notification fails
                
                await query.edit_message_text(
                    f"✅ Книга позначена як доставлена на полицю!\n\n"
                    f"📚 {book['name']}\n"
                    f"👤 Користувача {user_info['user_name']} повідомлено про готовність книги."
                )
            else:
                logger.warning(f"❌ No active booking found for book_id: {book_id}, book_name: {book['name']}")
                
                
                # No active booking found
                await query.edit_message_text(
                    f"✅ Книга позначена як доставлена на полицю!\n\n"
                    f"📚 {book['name']}\n"
                    f"⚠️ Не знайдено активного бронювання для цієї книги.\n"
                    f"Book ID: {book_id} (перевірте логи для деталей)"
                )
                
        except Exception as e:
            logger.error(f"Failed to mark book as delivered: {e}")
            await query.edit_message_text("❌ Помилка при позначенні книги як доставленої.")
    
    async def _handle_admin_statistics(self, query):
        """Handle admin statistics request"""
        try:
            top_books = self.user_manager.get_top_books_last_month(10)
            
            if top_books:
                text = "📊 <b>Топ-10 найменш популярних книг за останній місяць</b>\n\n"
                for i, book in enumerate(top_books, 1):
                    # Get book name from sheets using book_id
                    book_name = self._get_book_name_by_id(book['book_id'])
                    if not book_name:
                        book_name = f"Книга ID: {book['book_id']}"
                    
                    text += f"{i}. <b>{book_name}</b>\n"
                    text += f"   📈 Забронювань: {book['booking_count']}\n\n"
            else:
                text = "📊 <b>Статистика за останній місяць</b>\n\n❌ Немає даних про бронювання за останній місяць"
            
            await query.edit_message_text(
                text,
                reply_markup=keyboards.get_admin_panel_keyboard(),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error getting admin statistics: {e}")
            await query.edit_message_text(
                "❌ Помилка отримання статистики",
                reply_markup=keyboards.get_admin_panel_keyboard()
            )
    
    async def _handle_admin_confirm_returns(self, query):
        """Handle admin confirm returns request"""
        user_id = query.from_user.id
        books = self.sheets_manager.get_returned_books_pending_confirmation()
        logger.info(f"Admin {user_id} requested returned books, found {len(books)} books")
        
        if books:
            await query.edit_message_text(
                f"🔄 Книги очікують підтвердження повернення ({len(books)}):",
                reply_markup=keyboards.get_returned_books_keyboard(books)
            )
        else:
            await query.edit_message_text(
                "🔄 Немає книг, що очікують підтвердження повернення",
                reply_markup=keyboards.get_admin_panel_keyboard()
            )
    
    async def _handle_admin_confirm_return(self, query, data):
        """Handle admin book return confirmation request"""
        book_index = int(data.replace("admin_confirm_return_", ""))
        book = self.sheets_manager.get_book_by_index(book_index)
        
        if book:
            await query.edit_message_text(
                f"📚 <b>{book['name']}</b>\n"
                f"👤 <b>Автор:</b> {book['author']}\n"
                f"📖 <b>Видавництво:</b> {book['edition']}\n"
                f"📅 <b>Було заброньовано до:</b> {book['booked_until']}\n\n"
                "Підтвердити повернення книги?\n"
                "Це очистить статус і забарвлення рядка.",
                reply_markup=keyboards.get_return_confirmation_keyboard(book_index),
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text("❌ Книга не знайдена.")
    
    async def _handle_admin_confirmed_return(self, query, data):
        """Handle admin book return confirmation"""
        book_index = int(data.replace("admin_confirmed_return_", ""))
        
        try:
            # Get book info before clearing
            book = self.sheets_manager.get_book_by_index(book_index)
            book_name = f"{book['name']} - {book['author']}" if book else "Unknown book"
            
            # Confirm return in sheets (clears status and color)
            self.sheets_manager.confirm_book_return(book_index)
            
            # Also mark as returned in database if user exists
            # Note: This requires enhancing to track which user had the book
            # For now, we'll just log the return
            logger.info(f"Book {book_index} ({book_name}) return confirmed by admin")
            
            await query.edit_message_text(
                f"✅ Повернення книги підтверджено!\n\n"
                f"📚 {book_name}\n\n"
                "Статус очищено, забарвлення знято."
            )
        except Exception as e:
            logger.error(f"Failed to confirm book return: {e}")
            await query.edit_message_text("❌ Помилка при підтвердженні повернення книги.")
    
    async def _get_delivery_debug_info(self, base_message):
        """Get debug information for delivery queue"""
        try:
            df = self.sheets_manager.read_books()
            if not df.empty:
                total_books = len(df)
                booked_count = len(df[df[config.EXCEL_COLUMNS['status']].astype(str).str.lower() == config.STATUS_VALUES['BOOKED']])
                debug_text = (
                    f"{base_message}\n\n"
                    f"🔍 Відладочна інформація:\n"
                    f"Всього книг в таблиці: {total_books}\n"
                    f"Книг зі статусом 'booked': {booked_count}\n\n"
                    f"Перевірте, чи є книги зі статусом 'booked' в колонці 'Status'"
                )
            else:
                debug_text = f"{base_message}\n\n❌ Не вдалося прочитати дані з таблиці"
        except Exception as debug_e:
            logger.error(f"Debug info error: {debug_e}")
            debug_text = f"{base_message}\n\n❌ Помилка отримання відладочної інформації: {debug_e}"
        
        return debug_text
    
    async def _handle_user_picked_up(self, query):
        """Handle user picked up book"""
        user_id = query.from_user.id
        
        try:
            # Get user's active books
            active_books = self.user_manager.get_user_active_books(user_id)
            
            if not active_books:
                await query.edit_message_text(
                    "❌ У вас немає активних книг для підтвердження отримання.",
                    reply_markup=keyboards.get_user_book_actions_keyboard()
                )
                return
            
            # For now, handle the first active book (in future versions, let user choose)
            book = active_books[0]
            book_id = book['book_id']
            
            # Read books data once to avoid multiple API calls
            try:
                df = self.sheets_manager.read_books()
            except Exception as e:
                logger.error(f"Failed to read books from Google Sheets: {e}")
                await query.edit_message_text(
                    "❌ Помилка при підключенні до Google Sheets.",
                    reply_markup=keyboards.get_user_book_actions_keyboard()
                )
                return
            
            # Get book name for display using cached data
            book_name = self._get_book_name_by_id_cached(book_id, df)
            if not book_name:
                book_name = f"Книга ID: {book_id}"
            
            # Find the book in Google Sheets to mark as picked up using cached data
            try:
                book_row = df[df[config.EXCEL_COLUMNS['id']].astype(str) == str(book_id)]
                
                if not book_row.empty:
                    book_index = book_row.index[0]
                    
                    # Mark as picked up in Google Sheets (set due date)
                    self.sheets_manager.mark_as_picked_up(book_index, user_id)
                    
                    # Get user info for admin notification
                    user_info = self.user_manager.get_user(user_id)
                    user_display_info = {
                        'name': self.user_manager.get_user_display_name(user_id),
                        'phone': user_info.get('phone_number', 'не вказано') if user_info else 'не вказано'
                    }
                    
                    # Prepare book info for admin notification
                    book_info = {
                        'name': book_name.split(' - ')[0] if ' - ' in book_name else book_name,
                        'author': book_name.split(' - ')[1] if ' - ' in book_name else 'Невідомий автор',
                        'due_date': book['expiry_date'].strftime('%d.%m.%Y')
                    }
                    
                    # Notify admins about pickup
                    await self.notification_manager.notify_admins_book_picked_up(book_info, user_display_info)
                    
                    logger.info(f"User {user_id} confirmed pickup of book {book_id} ({book_name})")
                    
                    await query.edit_message_text(
                        f"✅ Дякуємо! Підтверджено отримання книги:\n\n"
                        f"📚 <b>{book_name}</b>\n"
                        f"📅 Повернути до: {book['expiry_date'].strftime('%d.%m.%Y')}\n\n"
                        "Не забувайте повернути книгу вчасно!",
                        parse_mode='HTML'
                    )
                else:
                    logger.error(f"Could not find book {book_id} in Google Sheets for pickup confirmation")
                    await query.edit_message_text(
                        f"✅ Підтверджено отримання книги:\n\n"
                        f"📚 <b>{book_name}</b>\n"
                        f"📅 Повернути до: {book['expiry_date'].strftime('%d.%m.%Y')}\n\n"
                        "⚠️ Помилка оновлення в таблиці. Зверніться до адміністратора.",
                        parse_mode='HTML'
                    )
                    
            except Exception as sheets_error:
                logger.error(f"Error updating Google Sheets for pickup: {sheets_error}")
                await query.edit_message_text(
                    f"✅ Підтверджено отримання книги:\n\n"
                    f"📚 <b>{book_name}</b>\n"
                    f"📅 Повернути до: {book['expiry_date'].strftime('%d.%m.%Y')}\n\n"
                    "⚠️ Помилка оновлення в таблиці. Зверніться до адміністратора.",
                    parse_mode='HTML'
                )
        
        except Exception as e:
            logger.error(f"Error in user pickup confirmation: {e}")
            await query.edit_message_text(
                "❌ Помилка при підтвердженні отримання книги.",
                reply_markup=keyboards.get_user_book_actions_keyboard()
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
    
    def _get_book_name_by_id_cached(self, book_id, books_df):
        """Get book name by book_id from cached dataframe"""
        try:
            if books_df.empty:
                return None
            
            # Find book by ID
            book_row = books_df[books_df[config.EXCEL_COLUMNS['id']].astype(str) == str(book_id)]
            if not book_row.empty:
                row = book_row.iloc[0]
                return f"{row[config.EXCEL_COLUMNS['name']]} - {row[config.EXCEL_COLUMNS['author']]}"
            return None
        except Exception as e:
            logger.error(f"Error getting book name for ID {book_id}: {e}")
            return None
    
    def _get_book_name_by_id(self, book_id):
        """Get book name by book_id from the sheets"""
        try:
            df = self.sheets_manager.read_books()
            return self._get_book_name_by_id_cached(book_id, df)
        except Exception as e:
            logger.error(f"Error getting book name for ID {book_id}: {e}")
            return None
    
    async def _handle_return_books(self, query):
        """Handle return books - show list of books to select from"""
        user_id = query.from_user.id
        
        try:
            # Get user's active books
            active_books = self.user_manager.get_user_active_books(user_id)
            
            if not active_books:
                await query.edit_message_text(
                    "❌ У вас немає активних книг для повернення.",
                    reply_markup=keyboards.get_user_book_actions_keyboard()
                )
                return
            
            # Read books data once to avoid multiple API calls
            try:
                books_df = self.sheets_manager.read_books()
            except Exception as e:
                logger.error(f"Failed to read books from Google Sheets: {e}")
                books_df = pd.DataFrame()  # Empty dataframe as fallback
            
            # Prepare books for selection with display names
            books_for_selection = []
            for book in active_books:
                book_id = book['book_id']
                book_name = self._get_book_name_by_id_cached(book_id, books_df)
                if not book_name:
                    book_name = f"Книга ID: {book_id}"
                
                books_for_selection.append({
                    'book_id': book_id,
                    'display_name': book_name.split(' - ')[0] if ' - ' in book_name else book_name,
                    'expiry_date': book['expiry_date']
                })
            
            # Show selection keyboard
            text = "📤 <b>Повернення книги</b>\n\n"
            text += "Оберіть книгу, яку ви хочете повернути:\n\n"
            
            for i, book in enumerate(books_for_selection, 1):
                text += f"{i}. <b>{book['display_name']}</b>\n"
                text += f"   📅 Повернути до: {book['expiry_date'].strftime('%d.%m.%Y')}\n\n"
            
            await query.edit_message_text(
                text,
                reply_markup=keyboards.get_user_return_books_keyboard(books_for_selection),
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Error in return books handler: {e}")
            await query.edit_message_text(
                "❌ Помилка при отриманні списку книг для повернення.",
                reply_markup=keyboards.get_user_book_actions_keyboard()
            )
    
    async def _handle_return_book_selection(self, query, data):
        """Handle specific book selection for return"""
        book_id = data.replace("return_select_", "")
        user_id = query.from_user.id
        
        try:
            # Get book name for display
            book_name = self._get_book_name_by_id(book_id)
            if not book_name:
                book_name = f"Книга ID: {book_id}"
            
            # Show confirmation with instructions
            text = (
                f"📤 <b>Повернення книги</b>\n\n"
                f"📚 <b>Обрана книга:</b> {book_name.split(' - ')[0] if ' - ' in book_name else book_name}\n\n"
                f"<b>Інструкції для повернення:</b>\n"
                f"1. Покладіть книгу на полицю\n"
                f"2. Натисніть кнопку нижче\n"
                f"3. Зробіть фото книги на полиці\n"
                f"4. Надішліть фото в чат\n\n"
                f"Після отримання фото, адміністратор буде повідомлений про необхідність забрати книгу."
            )
            
            await query.edit_message_text(
                text,
                reply_markup=keyboards.get_return_confirmation_keyboard_user(book_id),
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Error in return book selection: {e}")
            await query.edit_message_text(
                "❌ Помилка при обробці вибору книги.",
                reply_markup=keyboards.get_user_book_actions_keyboard()
            )
    
    async def _handle_return_confirmation(self, query, data):
        """Handle return confirmation - request photo"""
        book_id = data.replace("return_confirm_", "")
        user_id = query.from_user.id
        
        # Store book_id for photo processing
        self.pending_returns[user_id] = book_id
        
        try:
            book_name = self._get_book_name_by_id(book_id)
            if not book_name:
                book_name = f"Книга ID: {book_id}"
            
            text = (
                f"📷 <b>Надішліть фото книги</b>\n\n"
                f"📚 <b>Книга:</b> {book_name.split(' - ')[0] if ' - ' in book_name else book_name}\n\n"
                f"Зробіть фото книги на полиці та надішліть його в цей чат.\n"
                f"Після отримання фото, адміністратор буде автоматично повідомлений."
            )
            
            await query.edit_message_text(text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error in return confirmation: {e}")
            await query.edit_message_text(
                "❌ Помилка при підтвердженні повернення.",
                reply_markup=keyboards.get_user_book_actions_keyboard()
            )
    
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