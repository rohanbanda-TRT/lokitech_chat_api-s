import pandas as pd

# Read the Excel file
file_path = "/home/com-028/Desktop/TRT/PROJ/DSP_BOT_Structured/Coaching Details.xlsx"
df = pd.read_excel(file_path)

# Display the column names
print("Column Names:")
print(df.columns.tolist())

# Display the first few rows to understand the structure
print("\nFirst 5 rows:")
print(df.head())

# Get basic information about the data
print("\nBasic Information:")
print(df.info())

# Check for unique values in key columns (if any)
if 'Category' in df.columns:
    print("\nUnique Categories:")
    print(df['Category'].unique())

if 'Date' in df.columns:
    print("\nDate Range:")
    print(f"Earliest: {df['Date'].min()}")
    print(f"Latest: {df['Date'].max()}")
