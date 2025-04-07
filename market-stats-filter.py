#!/usr/bin/python3
import csv
from datetime import datetime
import argparse

# Define the input and output file paths
input_file = 'trade-statistics-all-markets.csv'
output_file = 'filtered-trades.csv'

# Set up argument parsing
parser = argparse.ArgumentParser(description='Filter trades based on year, month, payment method, and currency.')
parser.add_argument('--year', type=int, help='Year to filter trades')
parser.add_argument('--month', type=int, help='Month to filter trades')
parser.add_argument('--payment_method', type=str, help='Payment method to filter trades')
parser.add_argument('--currency', type=str, help='Currency to filter trades')

args = parser.parse_args()

# Open the input CSV file and read the data
with open(input_file, mode='r', newline='') as infile:
    reader = csv.DictReader(infile)
    rows = list(reader)

# Filter the rows based on the provided arguments
filtered_rows = []
for row in rows:
    date_str = row['Date/Time']
    payment_method = row['Payment method']
    amount = row['Amount']

    # Parse the date string to a datetime object
    date_obj = datetime.strptime(date_str, "%b %d, %Y %I:%M:%S %p")

    # Check the date, payment method, and currency
    if (args.year is None or date_obj.year == args.year) and \
       (args.month is None or date_obj.month == args.month) and \
       (args.payment_method is None or payment_method == args.payment_method) and \
       (args.currency is None or args.currency in amount):
        filtered_rows.append(row)

# Write the filtered rows to the output CSV file
with open(output_file, mode='w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
    writer.writeheader()
    writer.writerows(filtered_rows)

print(f"Filtered data has been written to {output_file}")
