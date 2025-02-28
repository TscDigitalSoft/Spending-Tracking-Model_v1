import re
import pandas as pd
import pdfplumber
import tkinter as tk
from tkinter import filedialog

# Function to normalize the description
def normalize_description(description):
    # Lowercase and remove special characters
    description = re.sub(r'[^a-zA-Z0-9\s]', '', description).lower()
    return description

# Function to categorize transactions based on the description
def categorize_transaction(description):
    description = normalize_description(description)  # Normalize before matching
    # Define keywords for each category
    food_keywords = [
        'taco bell', 'mcdonalds', 'dominos', 'pizza hut', 'starbucks', 'subway', 
        'chipotle', 'rook coffee', 'circus wines', 'mcdonald s', '1st cup', 
        'the atlantic diner', 'valentinos restaurant', 'coffee', 'bagels', 
        'pantry 1 food market', 'food', 'holmdel bagels', 'uber eats'
    ]
    if any(keyword in description for keyword in food_keywords):
        return 'Food'
    elif any(keyword in description for keyword in ['shoprite', 'whole foods', 'supermarket', 'trader joes', 'kroger', 'safeway', 'aldi']):
        return 'Groceries'
    elif any(keyword in description for keyword in ['zelle', 'etransfer', 'online transfer', 'paypal', 'venmo', 'square']):
        return 'Transfers'
    elif 'amazon prime' in description:
        return 'Subscriptions'
    elif any(keyword in description for keyword in ['amazon', 'walmart', 'target', 'ebay', 'etsy', 'macys']):
        return 'Shopping'
    elif any(keyword in description for keyword in ['netflix', 'hulu', 'disney', 'cinemark', 'playstation', 'xbox']):
        return 'Entertainment'
    elif any(keyword in description for keyword in ['verizon', 'at&t', 'comcast', 'spectrum']):
        return 'Utilities'
    else:
        return 'Miscellaneous'

# Function to extract transactions from a PDF
def extract_transactions_from_pdf(pdf_path):
    transactions = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')
            i = 0
            while i < len(lines) - 1:
                line = lines[i]
                # Check for the start of a transaction (date and potential amount at the end)
                if line.startswith(('01/', '12/')) and line.split()[-1].replace('.', '', 1).isdigit():
                    date = line.split()[0]
                    amount = line.split()[-1]
                    description = ' '.join(line.split()[1:-1])
                    # Assume the next line is part of the description
                    if i + 1 < len(lines):
                        description += ' ' + lines[i + 1]
                        i += 1  # Skip the next line as it's part of the current transaction description
                    transactions.append({'date': date, 'description': description, 'amount': amount})
                i += 1
    return transactions

# Create a Tkinter root window
root = tk.Tk()
root.withdraw()  # Hide the root window

# Open a file dialog to select a PDF file
file_path = filedialog.askopenfilename(
    title="Select the PDF file",
    filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
)

# Check if a file was selected
if file_path:
    # Extract transactions from the selected PDF file
    transactions = extract_transactions_from_pdf(file_path)
    df_transactions = pd.DataFrame(transactions)

    # Apply the categorization to the transaction descriptions
    df_transactions['category'] = df_transactions['description'].apply(categorize_transaction)

    # Display the results
    print(df_transactions[['date', 'description', 'amount', 'category']].head(20))
else:
    print("No file selected")
