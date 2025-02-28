import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import pdfplumber
import os

def categorize(description):
    description = description.lower()
    if 'grocery' in description or 'shoprite' in description:
        return 'Groceries'
    elif 'rent' in description:
        return 'Rent'
    elif 'utility' in description or 'verizon' in description:
        return 'Utilities'
    elif 'entertainment' in description or 'netflix' in description or 'disney' in description:
        return 'Entertainment'
    elif 'restaurant' in description or 'taco bell' in description or 'mcdonald' in description:
        return 'Dining Out'
    elif 'gas' in description or 'exxon' in description:
        return 'Gas'
    else:
        return 'Other'

def extract_transactions(pdf_path):
    transactions = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if "Electronic Deposits" in text:
                lines = text.split('\n')
                capture = False
                for line in lines:
                    if "Electronic Deposits" in line:
                        capture = True
                    if "Checks Paid" in line:
                        capture = False
                    if capture and any(char.isdigit() for char in line):
                        parts = line.split()
                        date = parts[0]
                        amount = parts[-1]
                        description = " ".join(parts[1:-1])
                        transactions.append([date, description, amount])
            elif "Electronic Payments" in text:
                lines = text.split('\n')
                capture = False
                for line in lines:
                    if "Electronic Payments" in line:
                        capture = True
                    if "Daily Balance Summary" in line:
                        capture = False
                    if capture and any(char.isdigit() for char in line):
                        parts = line.split()
                        date = parts[0]
                        amount = parts[-1]
                        description = " ".join(parts[1:-1])
                        transactions.append([date, description, amount])
    return transactions

def convert_and_process_pdf(file_path):
    try:
        transactions = extract_transactions(file_path)
        df = pd.DataFrame(transactions, columns=['Date', 'Description', 'Amount'])
        df['Amount'] = df['Amount'].str.replace(',', '').astype(float)
        df['Category'] = df['Description'].apply(categorize)
        
        # Save DataFrame to CSV
        output_csv_path = os.path.splitext(file_path)[0] + '_processed.csv'
        df.to_csv(output_csv_path, index=False)
        
        messagebox.showinfo("Success", f"Processed CSV saved as {output_csv_path}")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        convert_and_process_pdf(file_path)

# Set up the GUI
root = tk.Tk()
root.title("PDF to CSV Converter")

frame = tk.Frame(root, padx=10, pady=10)
frame.pack(padx=10, pady=10)

label = tk.Label(frame, text="Select a PDF file to convert and process:")
label.pack(pady=5)

button = tk.Button(frame, text="Browse", command=select_file)
button.pack(pady=5)

root.mainloop()

