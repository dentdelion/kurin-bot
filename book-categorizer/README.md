# kurin-bot

# Book Categorizer

This project categorizes books in an Excel file using the Anthropic Claude API.

## Requirements
- Python 3.8+
- Anthropic API key (see below)

## Installation

1. Clone the repository and navigate to the project directory.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Setup

You need an Anthropic API key to use this script. Set it as an environment variable:

```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

Or pass it as a parameter to the script (see code for details).

## Usage

Place your Excel file (e.g., `books.xlsx`) in the `book-categorizer` directory.

Run the categorizer script:

```bash
python book-categorizer/book-categorizer.py
```

Or, to process a specific file and output:

```bash
python book-categorizer/book-categorizer.py --input books.xlsx --output books_categorized.xlsx
```

### Script Arguments
- `--input`: Path to the input Excel file (default: `books.xlsx`)
- `--output`: Path to the output Excel file (default: `books_categorized.xlsx`)
- `--batch-size`: Number of books to process before saving progress (default: 50)
- `--delay`: Delay (in seconds) between API calls (default: 0.5)
- `--force-recategorize`: Re-categorize all books even if already categorized

## Example

```bash
python book-categorizer/book-categorizer.py --input books.xlsx --output books_categorized.xlsx --batch-size 20 --delay 1
```

## Notes
- The script will create a new column `categories` in your Excel file.
- Make sure your Excel file has the required columns: Назва, Автор, Видавництво та рік видання, Короткий опис.
- For more details, see the script docstrings.
