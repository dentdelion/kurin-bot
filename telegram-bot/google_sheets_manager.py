import gspread
import pandas as pd
from datetime import datetime, timedelta
from google.auth.exceptions import GoogleAuthError
import config
import logging
import re

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self):
        self.gc = None
        self.worksheet = None
        self._authenticate()
        self._open_sheet()
        
    def _authenticate(self):
        """Authenticate with Google Sheets API"""
        try:
            self.gc = gspread.service_account(filename=config.GOOGLE_CREDENTIALS_FILE)
            logger.info("Successfully authenticated with Google Sheets")
        except FileNotFoundError:
            logger.error(f"Google credentials file not found: {config.GOOGLE_CREDENTIALS_FILE}")
            raise
        except GoogleAuthError as e:
            logger.error(f"Google authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Google Sheets authentication: {e}")
            raise
    
    def _open_sheet(self):
        """Open the specified Google Sheet"""
        try:
            if not config.GOOGLE_SHEETS_URL:
                raise ValueError("GOOGLE_SHEETS_URL is not configured")
            
            # Extract sheet ID from URL
            sheet_id = self._extract_sheet_id(config.GOOGLE_SHEETS_URL)
            logger.info(f"Extracted sheet ID: {sheet_id}")
            
            # Open sheet by ID
            sheet = self.gc.open_by_key(sheet_id)
            
            # Get worksheet by name
            self.worksheet = sheet.worksheet(config.GOOGLE_SHEET_NAME)
            logger.info(f"Successfully opened worksheet: {config.GOOGLE_SHEET_NAME}")
            
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet '{config.GOOGLE_SHEET_NAME}' not found in the sheet")
            raise
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(f"Spreadsheet not found or access denied: {config.GOOGLE_SHEETS_URL}")
            raise
        except Exception as e:
            logger.error(f"Failed to open Google Sheet: {e}")
            raise
    
    def _extract_sheet_id(self, url):
        """Extract sheet ID from Google Sheets URL"""
        try:
            if '/d/' in url:
                return url.split('/d/')[1].split('/')[0]
            else:
                raise ValueError("Invalid Google Sheets URL format")
        except Exception as e:
            logger.error(f"Failed to extract sheet ID from URL: {e}")
            raise
    
    def read_books(self):
        """Read all books from the sheet"""
        try:
            # Get all records
            records = self.worksheet.get_all_records()
            
            if not records:
                logger.warning("No data found in the sheet")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(records)
            
            # Ensure all required columns exist
            required_columns = list(config.EXCEL_COLUMNS.values())
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                raise ValueError(f"Missing columns in Google Sheet: {missing_columns}")
            
            logger.info(f"Successfully read {len(df)} books from sheet")
            return df
            
        except Exception as e:
            logger.error(f"Failed to read books: {e}")
            raise
    
    def get_books_by_category(self, category, page=0):
        """Get books filtered by category with pagination"""
        df = self.read_books()
        
        if df.empty:
            return [], 0
            
        # Filter by category if not "all"
        if category.lower() != 'all':
            mask = df[config.EXCEL_COLUMNS['categories']].astype(str).str.contains(category, case=False, na=False)
            filtered_df = df[mask]
        else:
            filtered_df = df
            
        total_books = len(filtered_df)
        
        # Apply pagination
        start_idx = page * config.BOOKS_PER_PAGE
        end_idx = start_idx + config.BOOKS_PER_PAGE
        page_df = filtered_df.iloc[start_idx:end_idx]
        
        # Convert to list of dictionaries
        books = []
        for idx, row in page_df.iterrows():
            book_info = {
                'index': idx,
                'id': row[config.EXCEL_COLUMNS['id']],
                'name': row[config.EXCEL_COLUMNS['name']],
                'author': row[config.EXCEL_COLUMNS['author']],
                'edition': row[config.EXCEL_COLUMNS['edition']],
                'pages': row[config.EXCEL_COLUMNS['pages']],
                'description': row[config.EXCEL_COLUMNS['description']],
                'booked_until': row[config.EXCEL_COLUMNS['booked_until']],
                'categories': row[config.EXCEL_COLUMNS['categories']],
                'status': row[config.EXCEL_COLUMNS['status']],
                'is_available': self._is_book_available(row)
            }
            books.append(book_info)
            
        return books, total_books
    
    def _is_book_available(self, row):
        """Check if book is available for booking"""
        booked_until = row[config.EXCEL_COLUMNS['booked_until']]
        status = row[config.EXCEL_COLUMNS['status']]
        
        # Book is available if booked_until is empty and status is empty
        return ((pd.isna(booked_until) or str(booked_until).strip() == '') and 
                (pd.isna(status) or str(status).strip() == ''))
    
    def book_item(self, book_index, user_id, user_name):
        """Mark book as booked with yellow highlighting"""
        try:
            # Convert book_index to row number (adding 2 for header and 1-indexing)
            row_num = book_index + 2
            
            # Get column index for 'status'
            col_index = self._get_column_index(config.EXCEL_COLUMNS['status'])
            
            # Update the status cell to 'booked'
            self.worksheet.update_cell(row_num, col_index, config.STATUS_VALUES['BOOKED'])
            
            # Color the entire row yellow
            self._color_row(row_num, '#FFFF00')
            
            logger.info(f"Book at row {book_index} booked by user {user_id} ({user_name})")
            return True
        except Exception as e:
            logger.error(f"Failed to book item: {e}")
            raise RuntimeError(f"Cannot update Google Sheet: {e}")
    
    def get_books_for_delivery(self):
        """Get books that are booked and need to be delivered"""
        df = self.read_books()
        if df.empty:
            return []
            
        mask = df[config.EXCEL_COLUMNS['status']].astype(str).str.lower() == config.STATUS_VALUES['BOOKED']
        delivery_books = df[mask]
        
        books = []
        for idx, row in delivery_books.iterrows():
            book_info = {
                'index': idx,
                'name': row[config.EXCEL_COLUMNS['name']],
                'author': row[config.EXCEL_COLUMNS['author']],
                'edition': row[config.EXCEL_COLUMNS['edition']]
            }
            books.append(book_info)
            
        return books
    
    def mark_as_delivered(self, book_index):
        """Mark book as delivered (ready for pickup)"""
        try:
            row_num = book_index + 2
            col_index = self._get_column_index(config.EXCEL_COLUMNS['status'])
            
            # Keep status as 'booked' but book is now ready for pickup
            # The row remains yellow until user picks it up
            logger.info(f"Book at row {book_index} marked as delivered and ready for pickup")
            return True
        except Exception as e:
            logger.error(f"Failed to mark book as delivered: {e}")
            raise RuntimeError(f"Cannot update Google Sheet: {e}")
    
    def mark_as_picked_up(self, book_index, user_id):
        """Mark book as picked up by user"""
        try:
            row_num = book_index + 2
            
            # Get column indices
            booked_until_col = self._get_column_index(config.EXCEL_COLUMNS['booked_until'])
            
            # Set due date
            due_date = datetime.now() + timedelta(days=config.ALLOWED_TIME_TO_READ_THE_BOOK)
            
            # Update due date
            self.worksheet.update_cell(row_num, booked_until_col, due_date.strftime('%Y-%m-%d'))
            
            # Status remains 'booked', row remains yellow
            
            logger.info(f"Book at row {book_index} marked as picked up by user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark book as picked up: {e}")
            raise RuntimeError(f"Cannot update Google Sheet: {e}")
    
    def mark_as_returned_by_user(self, book_index):
        """Mark book as returned by user (waiting for admin confirmation)"""
        try:
            row_num = book_index + 2
            
            # Get column index for status
            status_col = self._get_column_index(config.EXCEL_COLUMNS['status'])
            
            # Update status to 'returned' but keep row yellow
            self.worksheet.update_cell(row_num, status_col, config.STATUS_VALUES['RETURNED'])
            
            logger.info(f"Book at row {book_index} marked as returned by user")
            return True
        except Exception as e:
            logger.error(f"Failed to mark book as returned by user: {e}")
            raise RuntimeError(f"Cannot update Google Sheet: {e}")
    
    def confirm_book_return(self, book_index):
        """Admin confirms book return - clear status and color"""
        try:
            row_num = book_index + 2
            
            # Get column indices
            booked_until_col = self._get_column_index(config.EXCEL_COLUMNS['booked_until'])
            status_col = self._get_column_index(config.EXCEL_COLUMNS['status'])
            
            # Clear values
            self.worksheet.update_cell(row_num, booked_until_col, '')
            self.worksheet.update_cell(row_num, status_col, config.STATUS_VALUES['EMPTY'])
            
            # Clear background color
            self._clear_row_color(row_num)
            
            logger.info(f"Book at row {book_index} return confirmed - status and color cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to confirm book return: {e}")
            raise RuntimeError(f"Cannot update Google Sheet: {e}")
    
    def get_returned_books_pending_confirmation(self):
        """Get books that are returned but waiting for admin confirmation"""
        df = self.read_books()
        if df.empty:
            return []
            
        mask = df[config.EXCEL_COLUMNS['status']].astype(str).str.lower() == config.STATUS_VALUES['RETURNED']
        returned_books = df[mask]
        
        books = []
        for idx, row in returned_books.iterrows():
            book_info = {
                'index': idx,
                'name': row[config.EXCEL_COLUMNS['name']],
                'author': row[config.EXCEL_COLUMNS['author']],
                'edition': row[config.EXCEL_COLUMNS['edition']],
                'booked_until': row[config.EXCEL_COLUMNS['booked_until']]
            }
            books.append(book_info)
            
        return books

    def _get_column_index(self, column_name):
        """Get column index by name"""
        try:
            headers = self.worksheet.row_values(1)  # Get first row (headers)
            return headers.index(column_name) + 1  # gspread uses 1-based indexing
        except ValueError:
            logger.error(f"Column '{column_name}' not found in sheet headers")
            raise ValueError(f"Required column '{column_name}' not found in Google Sheet")
        except Exception as e:
            logger.error(f"Failed to read sheet headers: {e}")
            raise RuntimeError(f"Cannot read Google Sheet headers: {e}")
    
    def _color_row(self, row_num, color_hex):
        """Color an entire row with specified color"""
        try:
            # Get the number of columns
            num_cols = len(self.worksheet.row_values(1))
            
            # Create the range (e.g., "A2:H2" for row 2)
            range_name = f"A{row_num}:{chr(ord('A') + num_cols - 1)}{row_num}"
            
            # Apply formatting
            self.worksheet.format(range_name, {
                "backgroundColor": {
                    "red": int(color_hex[1:3], 16) / 255,
                    "green": int(color_hex[3:5], 16) / 255,
                    "blue": int(color_hex[5:7], 16) / 255
                }
            })
        except Exception as e:
            logger.warning(f"Could not color row {row_num}: {e}")
    
    def _clear_row_color(self, row_num):
        """Clear background color from an entire row"""
        try:
            num_cols = len(self.worksheet.row_values(1))
            range_name = f"A{row_num}:{chr(ord('A') + num_cols - 1)}{row_num}"
            
            # Clear formatting
            self.worksheet.format(range_name, {
                "backgroundColor": {
                    "red": 1.0,
                    "green": 1.0, 
                    "blue": 1.0
                }
            })
        except Exception as e:
            logger.warning(f"Could not clear row color {row_num}: {e}")
    
    def get_overdue_books(self):
        """Get books that are overdue"""
        df = self.read_books()
        if df.empty:
            return []
            
        current_date = datetime.now().date()
        overdue_books = []
        
        for idx, row in df.iterrows():
            booked_until = row[config.EXCEL_COLUMNS['booked_until']]
            if pd.notna(booked_until) and str(booked_until).strip() != '':
                try:
                    due_date = pd.to_datetime(booked_until).date()
                    if due_date < current_date:
                        book_info = {
                            'index': idx,
                            'name': row[config.EXCEL_COLUMNS['name']],
                            'author': row[config.EXCEL_COLUMNS['author']],
                            'due_date': due_date,
                            'days_overdue': (current_date - due_date).days
                        }
                        overdue_books.append(book_info)
                except:
                    continue
                    
        return overdue_books
    
    def get_book_by_index(self, book_index):
        """Get specific book by index"""
        df = self.read_books()
        if df.empty or book_index >= len(df):
            return None
            
        row = df.iloc[book_index]
        return {
            'index': book_index,
            'id': row[config.EXCEL_COLUMNS['id']],
            'name': row[config.EXCEL_COLUMNS['name']],
            'author': row[config.EXCEL_COLUMNS['author']],
            'edition': row[config.EXCEL_COLUMNS['edition']],
            'pages': row[config.EXCEL_COLUMNS['pages']],
            'description': row[config.EXCEL_COLUMNS['description']],
            'booked_until': row[config.EXCEL_COLUMNS['booked_until']],
            'categories': row[config.EXCEL_COLUMNS['categories']],
            'status': row[config.EXCEL_COLUMNS['status']],
            'is_available': self._is_book_available(row)
        } 