import re
import pandas as pd
import pdfplumber
import tkinter as tk
from tkinter import filedialog
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import joblib
import os

# File paths
MODEL_PATH = 'transaction_categorizer_model.pkl'
LABELLED_DATA_FOLDER = 'ModelTrainDoc'

# Function to normalize the description
def normalize_description(description):
    description = re.sub(r'[^a-zA-Z0-9\s]', '', description).lower()
    return description

# Function to load labeled data from all CSV files in a folder
def load_labeled_data(folder_path):
    all_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.csv')]
    data_frames = [pd.read_csv(file) for file in all_files]
    combined_data = pd.concat(data_frames, ignore_index=True)
    return combined_data

# Function to train and save the model
def train_and_save_model(data, model_path):
    X = data['description']
    y = data['category']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer()),
        ('clf', LogisticRegression())
    ])
    
    pipeline.fit(X_train, y_train)
    joblib.dump(pipeline, model_path)
    print(f"Model trained and saved with accuracy: {pipeline.score(X_test, y_test) * 100:.2f}%")

# Function to load the model
def load_model(model_path):
    return joblib.load(model_path)

# Function to categorize transactions using the trained model
def categorize_transaction_ml(description, model):
    return model.predict([description])[0]

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
                if "ElectronicPayments" in line.replace(" ", ""):
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
def re_categorize_miscellaneous(df, model):
    for index, row in df.iterrows():
        if row['category'] == 'Miscellaneous':
            if index + 1 < len(df):
                additional_info = df.at[index + 1, 'description']
                combined_description = row['description'] + ' ' + additional_info
                new_category = categorize_transaction_ml(combined_description, model)
                df.at[index, 'category'] = new_category
                print(f"Re-categorized: {combined_description} as {new_category}")
    return df

# Function to upload DataFrame to Google Sheets
def upload_to_google_sheets(df, sheet_url):
    spreadsheet_id = sheet_url.split('/d/')[1].split('/')[0]
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
GOOGLE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1gND8cs6kGrQI586ijpX8bJEzah9Aa-Ovk-iZEYV_1Pw/edit?gid=638105783#gid=638105783'

# Create a Tkinter root window
root = tk.Tk()
root.withdraw()

file_path = filedialog.askopenfilename(
    title="Select the PDF file",
    filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
)

# Check if the model file exists
if os.path.exists(MODEL_PATH):
    retrain = input("Model already exists. Do you want to retrain the model? (yes/no): ").strip().lower()
else:
    retrain = 'yes'

if retrain == 'yes':
    # Load labeled data from all CSV files in the folder
    labeled_data = load_labeled_data(LABELLED_DATA_FOLDER)
    # Train and save the model
    train_and_save_model(labeled_data, MODEL_PATH)

# Load the model
model = load_model(MODEL_PATH)

if file_path:
    transactions = extract_transactions_from_pdf(file_path)
    print(f"Extracted Transactions: {transactions}")  # Debugging: Print extracted transactions

    df_transactions = pd.DataFrame(transactions)
    print(f"DataFrame Columns: {df_transactions.columns}")  # Debugging: Print DataFrame columns
    print(f"DataFrame Head: {df_transactions.head()}")  # Debugging: Print the first few rows of the DataFrame

    if 'description' in df_transactions.columns:
        df_transactions['category'] = df_transactions['description'].apply(lambda x: categorize_transaction_ml(x, model))
        
        df_transactions = re_categorize_miscellaneous(df_transactions, model)
        
        print(df_transactions[['date', 'description', 'amount', 'category']].head(20))
        upload_to_google_sheets(df_transactions, GOOGLE_SHEET_URL)
    else:
        print("The 'description' column is missing from the DataFrame")
else:
    print("No file selected")
