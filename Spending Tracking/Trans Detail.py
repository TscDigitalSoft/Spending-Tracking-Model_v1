import re
import pandas as pd
import pdfplumber
import tkinter as tk
from tkinter import filedialog
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Function to normalize the description
def normalize_description(description):
    description = re.sub(r'[^a-zA-Z0-9\s]', '', description).lower()
    return description

# Function to categorize transactions based on the description
def categorize_transaction(description):
    description = normalize_description(description)
    food_keywords = [
        'taco bell', 'mcdonalds', 'dominos', 'pizza hut', 'starbucks', 'subway',
        'chipotle', 'rook coffee', 'circus wines', 'mcdonald s', '1st cup',
        'the atlantic diner', 'valentinos restaurant', 'coffee', 'bagels',
        'pantry 1 food market', 'food', 'holmdel bagels', 'uber eats'
    ]
    if any(keyword.lower() in description for keyword in food_keywords):
        return 'Food'
    elif any(keyword.lower() in description for keyword in ['shoprite', 'whole foods', 'supermarket', 'trader joes', 'kroger', 'safeway', 'aldi']):
        return 'Groceries'
    elif any(keyword.lower() in description for keyword in ['zelle', 'etransfer', 'online transfer', 'paypal', 'venmo', 'square']):
        return 'Transfers'
    elif 'amazon prime' in description:
        return 'Subscriptions'
    elif any(keyword.lower() in description for keyword in ['amazon', 'walmart', 'target', 'ebay', 'etsy', 'macys']):
        return 'Shopping'
    elif any(keyword.lower() in description for keyword in ['netflix', 'hulu', 'disney', 'cinemark', 'playstation', 'xbox']):
        return 'Entertainment'
    elif any(keyword.lower() in description for keyword in ['verizon', 'at&t', 'comcast', 'spectrum']):
        return 'Utilities'
    else:
        return 'Miscellaneous'

# Function to extract transactions from a PDF
def extract_transactions_from_pdf(pdf_path):
    transactions = []
    capturing_transactions = False
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]
                print(f"Processing line: {line}")  # Log each line processed
                if "Electronic Payments".lower() in line.lower().replace(" ", ""):
                    capturing_transactions = True
                    i += 1
                    continue
                if capturing_transactions:
                    if re.match(r'\d{2}/\d{2}', line[:5]) and re.match(r'-?\d+\.\d{2}', line.split()[-1]):
                        date = line.split()[0]
                        amount = line.split()[-1]
                        description = ' '.join(line.split()[1:-1])
                        if (i + 1 < len(lines)) and not re.match(r'\d{2}/\d{2}', lines[i + 1][:5]):
                            description += ' ' + lines[i + 1].strip()
                            i += 1  # Skip the next line as it's part of the current transaction description
                        transactions.append({'date': date, 'description': description, 'amount': amount})
                        print(f"Extracted Description: {description}")  # Log the full description
                i += 1
    return transactions

# Function to re-categorize transactions if initially classified as 'Miscellaneous'
def re_categorize_miscellaneous(df):
    for index, row in df.iterrows():
        if row['category'] == 'Miscellaneous':
            if index + 1 < len(df):
                additional_info = df.at[index + 1, 'description']
                combined_description = row['description'] + ' ' + additional_info
                new_category = categorize_transaction(combined_description)
                df.at[index, 'category'] = new_category
                print(f"Re-categorized: {combined_description} as {new_category}")
    return df

# Function to upload DataFrame to Google Sheets
def upload_to_google_sheets(df, sheet_url):
    spreadsheet_id = sheet_url.split('/')[5]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('budgetizerv1-f0a6af649026.json', scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(spreadsheet_id)
    
    new_sheet_name = datetime.now().strftime('Transactions_%Y%m%d_%H%M%S')
    sheet = spreadsheet.add_worksheet(title=new_sheet_name, rows="100", cols="20")
    
    sheet.append_row(df.columns.tolist())
    rows = df.values.tolist()
    
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        sheet.append_rows(rows[i:i+batch_size])
    print(f"Data uploaded to Google Sheet: {new_sheet_name}")

# Hardcoded Google Sheet URL
GOOGLE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1gND8cs6kGrQI586ijpX8bJEzah9Aa-Ovk-iZEYV_1Pw/edit?gid=465134039#gid=465134039'

# Create a Tkinter root window
root = tk.Tk()
root.withdraw()

file_path = filedialog.askopenfilename(
    title="Select the PDF file",
    filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
)

if file_path:
    transactions = extract_transactions_from_pdf(file_path)
    print(f"Extracted Transactions: {transactions}")  # Debugging: Print extracted transactions

    df_transactions = pd.DataFrame(transactions)
    print(f"DataFrame Columns: {df_transactions.columns}")  # Debugging: Print DataFrame columns
    print(f"DataFrame Head: {df_transactions.head()}")  # Debugging: Print the first few rows of the DataFrame

    if 'description' in df_transactions.columns:
        df_transactions['category'] = df_transactions['description'].apply(categorize_transaction)
        
        df_transactions = re_categorize_miscellaneous(df_transactions)
        
        print(df_transactions[['date', 'description', 'amount', 'category']].head(20))
        upload_to_google_sheets(df_transactions, GOOGLE_SHEET_URL)
    else:
        print("The 'description' column is missing from the DataFrame")
else:
    print("No file selected")
