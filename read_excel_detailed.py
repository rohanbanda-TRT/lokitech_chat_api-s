import pandas as pd
import json

# Read the Excel file
file_path = "/home/com-028/Desktop/TRT/PROJ/DSP_BOT_Structured/Coaching Details.xlsx"
df = pd.read_excel(file_path, header=1)  # Skip the first row as it contains column headers

# Rename columns based on the first row
df.columns = ['Status', 'Date', 'Category', 'Subcategory', 'Severity', 
              'Statement_of_Problem', 'Prior_Discussion', 'Corrective_Action', 'Uploaded_Pictures']

# Display the first few rows with proper column names
print("\nFirst 5 rows with proper column names:")
print(df.head())

# Get unique categories and subcategories
print("\nUnique Categories:")
print(df['Category'].unique())

print("\nUnique Subcategories:")
print(df['Subcategory'].unique())

# Count occurrences of each category
print("\nCategory Counts:")
print(df['Category'].value_counts())

# Count occurrences of each subcategory
print("\nSubcategory Counts:")
print(df['Subcategory'].value_counts())

# Convert to JSON format (as mentioned in the requirements)
json_data = df.to_dict(orient='records')
print("\nJSON Format Example (first record):")
print(json.dumps(json_data[0], indent=2))

# Save to JSON file for future use
with open('coaching_history.json', 'w') as f:
    json.dump(json_data, f, indent=2)
print("\nSaved coaching history to coaching_history.json")
