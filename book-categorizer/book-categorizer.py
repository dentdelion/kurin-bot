from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import json
import anthropic
from typing import List, Optional
import time
import os

class BookCategorizer:
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the Claude-based book categorizer
        
        Args:
            api_key: Anthropic API key (can also be set via ANTHROPIC_API_KEY environment variable)
            model: Claude model to use
        """
        # Set up Anthropic client
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
        elif "ANTHROPIC_API_KEY" in os.environ:
            self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        else:
            raise ValueError("Anthropic API key must be provided either as parameter or ANTHROPIC_API_KEY environment variable")
        
        self.model = model
        
        # Define available categories
        self.available_categories = [
            "історія",
            "політологія", 
            "антропологія",
            "соціологія",
            "українська література",
            "світова література",
            "в оригіналі",
            "художня література",
            "літературознавство",
            "краєзнавство",
            "філософія",
            "суспільствознавство",
            "мовознавство",
            "мистецтво",
            "архітектура",
            "музика",
            "кіно",
            "зіни",
            "комікси",
            "біографії (про художників)"
        ]
        
        # Create the system prompt for categorization
        self.system_prompt = f"""You are a professional librarian and book categorization expert. Your task is to categorize books based on their metadata into Ukrainian categories.

Available categories:
{', '.join(self.available_categories)}

Rules:
1. Analyze the book title, author, edition, and description carefully
2. Select exactly 1 or 2 most appropriate categories from the list above
3. If the book doesn't clearly fit any category, use "нон-фікшен" as default
4. Consider the language of the book (Ukrainian, Russian, English) but categorize based on content, not language
5. For books in original language that haven't been translated, consider adding "в оригіналі" as one of the categories
6. Be precise and conservative in categorization
7. For Ukrainian authors or books specifically about Ukraine, consider "українська література" if it's literary work
8. Distinguish between "художня література" (fiction) and "світова література" (world literature/classics)
9. "біографії (про художників)" is specifically for biographies about artists, painters, musicians, etc.

Respond ONLY with valid JSON in this exact format:
{{"categories": ["category1", "category2"]}}

Do not include any explanations, reasoning, or additional text - just the JSON response."""

    def categorize_book(self, title: str, author: str, publisher_year: str, description: str, page_count: str = None) -> List[str]:
        """
        Categorize a book using Claude analysis
        Returns a list of up to 2 categories
        """
        # Prepare the book information
        book_info_parts = [
            f"Title: {title if title and str(title) != 'nan' else 'N/A'}",
            f"Author: {author if author and str(author) != 'nan' else 'N/A'}",
            f"Publisher/Year: {publisher_year if publisher_year and str(publisher_year) != 'nan' else 'N/A'}",
            f"Description: {description if description and str(description) != 'nan' else 'N/A'}"
        ]
        
        # Add page count if available
        if page_count and str(page_count) != 'nan':
            book_info_parts.append(f"Page count: {page_count}")
            
        book_info = "\n".join(book_info_parts)
        
        try:
            # Make API call to Claude
            message = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                temperature=0.1,  # Low temperature for consistent results
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": f"Please categorize this book:\n\n{book_info}"}
                ]
            )
            
            # Extract the response content
            response_text = message.content[0].text.strip()
            
            # Parse JSON response
            try:
                result = json.loads(response_text)
                categories = result.get("categories", ["нон-фікшен"])
                
                # Validate categories
                valid_categories = []
                for cat in categories[:2]:  # Max 2 categories
                    if cat in self.available_categories or cat == "нон-фікшен":
                        valid_categories.append(cat)
                
                # If no valid categories found, use default
                if not valid_categories:
                    valid_categories = ["нон-фікшен"]
                
                return valid_categories
                
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON response for book '{title}': {response_text}")
                return ["нон-фікшен"]
                
        except Exception as e:
            print(f"Error categorizing book '{title}': {str(e)}")
            return ["нон-фікшен"]

    def process_excel_file(self, input_file: str, output_file: str = None, batch_size: int = 50, delay: float = 0.5, force_recategorize: bool = False):
        """
        Process the Excel file and add categorization using Claude
        
        Args:
            input_file: Path to input Excel file
            output_file: Path to output Excel file (optional)
            batch_size: Number of books to process before saving progress
            delay: Delay between API calls to avoid rate limits
            force_recategorize: If True, re-categorize all books even if already categorized
        """
        try:
            # Read the Excel file
            df = pd.read_excel(input_file)
            
            # Map Ukrainian column names to English internal names
            column_mapping = {
                'Назва': 'book_name',
                'Автор': 'book_author', 
                'Видавництво та рік видання': 'book_edition',
                'К-сть с.': 'page_count',
                'Короткий опис': 'book_description',
                'Заброньовано до:': 'reserved_until'
            }
            
            # Check if we have the expected Ukrainian headers
            ukrainian_headers = ['Назва', 'Автор', 'Видавництво та рік видання', 'Короткий опис']
            
            if all(header in df.columns for header in ukrainian_headers):
                print("Found Ukrainian headers. Mapping to internal column names...")
                # Rename columns using the mapping
                df = df.rename(columns=column_mapping)
                print("Column mapping complete.")
            elif len(df.columns) >= 4:
                # Fallback: assume first 4 columns are the required ones
                print("Ukrainian headers not found. Using positional mapping...")
                df.columns = ['book_name', 'book_author', 'book_edition', 'book_description'] + list(df.columns[4:])
            else:
                raise ValueError("Excel file must have at least 4 columns with book data")
            
            # Verify we have the required columns after mapping
            required_columns = ['book_name', 'book_author', 'book_edition', 'book_description']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns after mapping: {missing_columns}")
            
            # Determine output file name
            if output_file is None:
                output_file = input_file.replace('.xlsx', '_categorized.xlsx')
            
            # Check if categories column exists
            if 'categories' not in df.columns:
                df['categories'] = ""
                print("Categories column not found. Creating new 'categories' column.")
            else:
                print("Categories column found.")
                if force_recategorize:
                    print("Force recategorization enabled. All books will be re-categorized.")
                    df['categories'] = ""  # Clear existing categories
                else:
                    # Count already categorized books
                    already_categorized = df['categories'].notna() & (df['categories'] != '')
                    categorized_count = already_categorized.sum()
                    print(f"Found {categorized_count} already categorized books. They will be skipped.")
            
            print(f"\nColumn structure:")
            print(f"  Book name: '{df.columns[df.columns.get_loc('book_name')]}'")
            print(f"  Author: '{df.columns[df.columns.get_loc('book_author')]}'") 
            print(f"  Publisher/Year: '{df.columns[df.columns.get_loc('book_edition')]}'")
            print(f"  Description: '{df.columns[df.columns.get_loc('book_description')]}'")
            if 'page_count' in df.columns:
                print(f"  Page count: '{df.columns[df.columns.get_loc('page_count')]}'")
            if 'reserved_until' in df.columns:
                print(f"  Reserved until: '{df.columns[df.columns.get_loc('reserved_until')]}'")
            print(f"  Categories: 'categories' (will be added/updated)")
            
            processed_count = 0
            skipped_count = 0
            
            print(f"\nProcessing {len(df)} books using Claude Sonnet 4...")
            print(f"Model: {self.model}")
            print(f"Batch size: {batch_size}, Delay: {delay}s")
            print(f"Force recategorize: {force_recategorize}")
            print("-" * 60)
            
            # Process each row
            for index, row in df.iterrows():
                # Skip if already processed (unless force_recategorize is True)
                if not force_recategorize and pd.notna(row.get('categories', '')) and row.get('categories', '') != '':
                    skipped_count += 1
                    if skipped_count % 100 == 0:  # Show progress for skipped books too
                        print(f"Skipped {skipped_count} already categorized books...")
                    continue
                
                # Categorize the book
                page_count = row.get('page_count', None) if 'page_count' in df.columns else None
                categories = self.categorize_book(
                    str(row['book_name']),
                    str(row['book_author']),
                    str(row['book_edition']),
                    str(row['book_description']),
                    str(page_count) if page_count else None
                )
                
                # Join categories with comma
                categories_str = ', '.join(categories)
                processed_count += 1
                
                print(f"Book {index + 1}/{len(df)}: '{row['book_name']}' -> {categories_str}")
                
                # Update the dataframe
                df.at[index, 'categories'] = categories_str
                
                # Add delay to avoid rate limits
                if delay > 0:
                    time.sleep(delay)
                
                # Save progress periodically
                if processed_count % batch_size == 0:
                    df.to_excel(output_file, index=False)
                    print(f"Progress saved at {processed_count} processed books...")
            
            # Final save
            df.to_excel(output_file, index=False)
            
            print("\n" + "="*60)
            print("CATEGORIZATION COMPLETE!")
            print("="*60)
            print(f"Results saved to: {output_file}")
            print(f"Total books in file: {len(df)}")
            print(f"Books processed: {processed_count}")
            print(f"Books skipped: {skipped_count}")
            
            # Show category statistics
            self._show_category_stats(df)
            
            return df
            
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            raise

    def _show_category_stats(self, df: pd.DataFrame):
        """Show statistics about categories"""
        print("\nCATEGORY DISTRIBUTION:")
        print("-" * 40)
        
        all_categories = []
        for cat_str in df['categories']:
            if pd.notna(cat_str) and cat_str != '':
                all_categories.extend(cat_str.split(', '))
        
        category_counts = {}
        for cat in all_categories:
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(df)) * 100
            print(f"  {cat:<25}: {count:4d} ({percentage:5.1f}%)")
        
        print(f"\nTotal categories assigned: {len(all_categories)}")
        print(f"Average categories per book: {len(all_categories) / len(df):.2f}")

# Example usage
if __name__ == "__main__":
    # Initialize the categorizer with your Anthropic API key
    try:
        categorizer = BookCategorizer()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set your Anthropic API key:")
        print("1. Set environment variable: export ANTHROPIC_API_KEY='your-key-here'")
        print("2. Or modify the code to pass api_key parameter directly")
        exit(1)
    
    # Configuration
    input_file = "books.xlsx"
    output_file = "books_categorized.xlsx"
    
    print("CLAUDE BOOK CATEGORIZATION TOOL")
    print("=" * 50)
    
    # Check if output file already exists and has categories
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_excel(output_file)
            if 'categories' in existing_df.columns:
                categorized_count = (existing_df['categories'].notna() & (existing_df['categories'] != '')).sum()
                print(f"Found existing categorized file with {categorized_count} categorized books.")
                print("\nOptions:")
                print("1. Continue categorization (skip already categorized books)")
                print("2. Force re-categorize all books")
                print("3. Exit")
                
                choice = input("\nChoose option (1-3): ").strip()
                
                if choice == "1":
                    force_recategorize = False
                    input_file = output_file  # Use the existing file as input
                elif choice == "2":
                    force_recategorize = True
                    input_file = output_file  # Use the existing file as input
                elif choice == "3":
                    print("Exiting...")
                    exit(0)
                else:
                    print("Invalid choice. Defaulting to continue categorization.")
                    force_recategorize = False
                    input_file = output_file
            else:
                force_recategorize = False
        except Exception as e:
            print(f"Error reading existing file: {e}")
            force_recategorize = False
    else:
        force_recategorize = False
    
    try:
        result_df = categorizer.process_excel_file(
            input_file, 
            output_file,
            batch_size=50,              # Save progress every 50 books
            delay=0.5,                  # 0.5 second delay between API calls
            force_recategorize=force_recategorize
        )
        print("\nSuccess! Categorization complete.")
        
    except FileNotFoundError:
        print(f"File '{input_file}' not found. Please check the file path.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Check if your Anthropic API key is valid and you have sufficient credits.")