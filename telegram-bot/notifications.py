import logging
from telegram import Bot
import config

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def notify_admins_book_requested(self, book_info, user_info):
        """Notify admins that a book was requested for delivery"""
        message = (
            f"🔔 <b>Нова заявка на доставку книги</b>\n\n"
            f"📚 <b>Книга:</b> {book_info['name']}\n"
            f"👤 <b>Автор:</b> {book_info['author']}\n"
            f"📖 <b>Видавництво:</b> {book_info['edition']}\n\n"
            f"👨‍💼 <b>Замовник:</b> {user_info['name']}\n"
            f"📱 <b>Телефон:</b> {user_info['phone']}\n\n"
            f"Потрібно доставити книгу на полицю."
        )
        
        for admin_id in config.ADMIN_IDS:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error sending notification to admin {admin_id}: {e}")
    
    async def notify_user_book_ready(self, user_id, book_info):
        """Notify user that book is ready for pickup"""
        message = (
            f"📚 <b>Книга готова до отримання!</b>\n\n"
            f"<b>Назва:</b> {book_info['name']}\n"
            f"<b>Автор:</b> {book_info['author']}\n\n"
            f"Книга вже на полиці і чекає на вас! 📖\n"
            f"Після отримання, будь ласка, підтвердіть це в боті."
        )
        
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}")
    
    async def notify_admins_book_picked_up(self, book_info, user_info):
        """Notify admins that book was picked up"""
        message = (
            f"✅ <b>Книга забрана</b>\n\n"
            f"📚 <b>Книга:</b> {book_info['name']}\n"
            f"👤 <b>Автор:</b> {book_info['author']}\n\n"
            f"👨‍💼 <b>Взяв:</b> {user_info['name']}\n"
            f"📱 <b>Телефон:</b> {user_info['phone']}\n\n"
            f"Книга повинна бути повернена до: {book_info.get('due_date', 'не вказано')}"
        )
        
        for admin_id in config.ADMIN_IDS:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error sending notification to admin {admin_id}: {e}")
    
    async def notify_user_book_overdue(self, user_id, book_info):
        """Notify user that book is overdue"""
        message = (
            f"⏰ <b>Час повертати книгу!</b>\n\n"
            f"📚 <b>Книга:</b> {book_info['name']}\n"
            f"👤 <b>Автор:</b> {book_info['author']}\n\n"
            f"Термін повернення: {book_info['due_date']}\n"
            f"Прострочено на: {book_info['days_overdue']} днів\n\n"
            f"Будь ласка, поверніть книгу якнайшвидше! 📖"
        )
        
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error sending overdue notification to user {user_id}: {e}")
    
    async def notify_admins_book_returned(self, book_info, user_info, photo_id=None):
        """Notify admins that book was returned"""
        message = (
            f"📤 <b>Книга повернена</b>\n\n"
            f"📚 <b>Книга:</b> {book_info['name']}\n"
            f"👤 <b>Автор:</b> {book_info['author']}\n\n"
            f"👨‍💼 <b>Повернув:</b> {user_info['name']}\n"
            f"📱 <b>Телефон:</b> {user_info['phone']}\n\n"
            f"Потрібно забрати книгу з полиці та перевірити її стан."
        )
        
        for admin_id in config.ADMIN_IDS:
            try:
                if photo_id:
                    await self.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo_id,
                        caption=message,
                        parse_mode='HTML'
                    )
                else:
                    await self.bot.send_message(
                        chat_id=admin_id,
                        text=message,
                        parse_mode='HTML'
                    )
            except Exception as e:
                logger.error(f"Error sending return notification to admin {admin_id}: {e}")
    
    async def send_rules_to_user(self, user_id):
        """Send library rules to user"""
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=config.RULES_TEXT,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error sending rules to user {user_id}: {e}") 