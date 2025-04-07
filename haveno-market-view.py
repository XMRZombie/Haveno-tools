#!/usr/bin/python3
import tkinter as tk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np


df = pd.read_csv('trade-statistics-all-markets.csv')
df['Date/Time'] = pd.to_datetime(df['Date/Time'])
df['Amount in XMR'] = df['Amount in XMR'].astype(float)
df['Amount'] = df['Amount'].str.extract(r'([\d\.]+)').astype(float)


df['Date'] = df['Date/Time'].dt.date
daily_df = df.groupby('Date').agg({
    'Amount in XMR': 'sum',
    'Price': 'mean',
    'Market': 'count'
}).reset_index()


root = tk.Tk()
root.title("Haveno stats")


notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)


volume_tab = ttk.Frame(notebook)
market_share_tab = ttk.Frame(notebook)

notebook.add(volume_tab, text='Volume Charts')
notebook.add(market_share_tab, text='Market Share')


volume_figure = plt.Figure(figsize=(10, 5), dpi=100)
volume_ax = volume_figure.add_subplot(111)
volume_ax.set_title('Daily Volume Charts')


market_share_figure = plt.Figure(figsize=(10, 5), dpi=100)
currency_share_ax = market_share_figure.add_subplot(121)
currency_share_ax.set_title('Currency Share')
payment_method_share_ax = market_share_figure.add_subplot(122)
payment_method_share_ax.set_title('Payment Method Share')


timeframe_label = tk.Label(volume_tab, text="Select Timeframe:")
timeframe_label.pack()
timeframe_var = tk.StringVar(value="Daily")
timeframe_menu = ttk.Combobox(volume_tab, textvariable=timeframe_var)
timeframe_menu['values'] = ('Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly')
timeframe_menu.pack()

def update_charts():
    timeframe = timeframe_var.get()

    if timeframe == 'Daily':
        aggregated_df = daily_df.copy()
        aggregated_df['Date/Time'] = pd.to_datetime(aggregated_df['Date'])
    elif timeframe == 'Weekly':
        aggregated_df = df.resample('W', on='Date/Time').agg({
            'Amount in XMR': 'sum',
            'Price': 'mean',
            'Market': 'count'
        }).reset_index()
    elif timeframe == 'Monthly':
        aggregated_df = df.resample('M', on='Date/Time').agg({
            'Amount in XMR': 'sum',
            'Price': 'mean',
            'Market': 'count'
        }).reset_index()
    elif timeframe == 'Quarterly':
        aggregated_df = df.resample('Q', on='Date/Time').agg({
            'Amount in XMR': 'sum',
            'Price': 'mean',
            'Market': 'count'
        }).reset_index()
    elif timeframe == 'Yearly':
        aggregated_df = df.resample('Y', on='Date/Time').agg({
            'Amount in XMR': 'sum',
            'Price': 'mean',
            'Market': 'count'
        }).reset_index()

    volume_ax.clear()
    volume_ax.set_title(f'{timeframe} Volume Charts')
    volume_ax.bar(aggregated_df.index, aggregated_df['Amount in XMR'], label='XMR Volume', alpha=0.6)
    volume_ax.set_xlabel('Date')
    volume_ax.set_ylabel('Volume (XMR)')
    volume_ax.legend()
    volume_canvas.draw()


    currency_share_ax.clear()
    currency_share_ax.set_title('Currency Share')
    currency_shares = df['Market'].value_counts()
    currency_share_ax.pie(currency_shares, labels=currency_shares.index, autopct='%1.1f%%', startangle=140)

    payment_method_share_ax.clear()
    payment_method_share_ax.set_title('Payment Method Share')


    if 'Payment method' in df.columns:

        df['Payment method'] = df['Payment method'].replace({
            'Cryptocurrencies Instant': 'Cryptocurrencies',
            'SEPA Instant Payments': 'SEPA'
        })

        payment_method_shares = df['Payment method'].value_counts()

        if not payment_method_shares.empty:
            payment_method_share_ax.pie(payment_method_shares, labels=payment_method_shares.index, autopct='%1.1f%%', startangle=140)
        else:
            payment_method_share_ax.text(0.5, 0.5, 'No Payment Method Data', ha='center', va='center', fontsize=12)
    else:
        payment_method_share_ax.text(0.5, 0.5, 'No Payment Method Data', ha='center', va='center', fontsize=12)

    market_share_canvas.draw()

update_button = tk.Button(volume_tab, text="Update Charts", command=update_charts)
update_button.pack()


volume_canvas = FigureCanvasTkAgg(volume_figure, volume_tab)
volume_canvas.draw()
volume_canvas.get_tk_widget().pack(fill='both', expand=True)

market_share_canvas = FigureCanvasTkAgg(market_share_figure, market_share_tab)
market_share_canvas.draw()
market_share_canvas.get_tk_widget().pack(fill='both', expand=True)

# Run the application
root.mainloop()
