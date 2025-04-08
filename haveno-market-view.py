#!/usr/bin/python3
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import gc
import time
import os
import numpy as np
import atexit
from concurrent.futures import ThreadPoolExecutor

def load_data(file_path):
    if not os.path.exists(file_path):
        messagebox.showerror("Error", f"Data file '{file_path}' not found.")
        return pd.DataFrame()
    try:
        use_cols = ['Date/Time', 'Amount in XMR', 'Amount', 'Market', 'Payment method']
        df = pd.read_csv(file_path, usecols=use_cols)
        df['Date/Time'] = pd.to_datetime(df['Date/Time'])
        df['Amount in XMR'] = df['Amount in XMR'].astype(float)

        # Merge 'SEPA Instant Payment' with 'SEPA'
        df['Payment method'] = df['Payment method'].replace('SEPA Instant Payments', 'SEPA')

        # Merge 'Cryptocurrencies Instant' with 'Cryptocurrencies'
        df['Payment method'] = df['Payment method'].replace('Cryptocurrencies Instant', 'Cryptocurrencies')

        return df
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load data: {e}")
        return pd.DataFrame()

def get_date_range(df):
    if df.empty:
        return None, None
    first_date = df['Date/Time'].min().date()
    last_date = df['Date/Time'].max().date()
    return first_date, last_date

def create_main_window():
    root = tk.Tk()
    root.title("Haveno stats")
    return root

def create_notebook(root):
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True)
    return notebook

def create_market_share_tab(notebook, df, first_date, last_date):
    market_share_tab = ttk.Frame(notebook)
    notebook.add(market_share_tab, text='Market Share')

    market_share_figure = plt.Figure(figsize=(18, 6), dpi=100)
    currency_share_ax = market_share_figure.add_subplot(131)
    currency_share_ax.set_title('Currency Share')
    payment_method_share_ax = market_share_figure.add_subplot(132)
    payment_method_share_ax.set_title('Payment Method Share')
    amount_xmr_share_ax = market_share_figure.add_subplot(133)
    amount_xmr_share_ax.set_title('Amount in XMR Ranges')

    # Adjust layout to add more space between pies
    market_share_figure.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1, wspace=0.3)

    info_frame = ttk.Frame(market_share_tab)
    info_frame.pack(fill='x', padx=10, pady=5)

    start_date_label = tk.Label(info_frame, text=f"From: {first_date if first_date else 'N/A'}")
    start_date_label.pack(side='left')

    end_date_label = tk.Label(info_frame, text=f"To: {last_date if last_date else 'N/A'}")
    end_date_label.pack(side='left', padx=10)

    total_volume_label = tk.Label(info_frame, text="Total Volume in XMR: ")
    total_volume_label.pack(side='left')

    market_share_canvas = FigureCanvasTkAgg(market_share_figure, market_share_tab)
    market_share_canvas.get_tk_widget().pack(fill='both', expand=True)

    annotation = None
    currency_wedges = []
    payment_wedges = []
    amount_xmr_wedges = []
    last_hover_time = 0
    debounce_interval = 0.1  # 100 ms debounce interval
    background = None

    def update_charts():
        nonlocal annotation, currency_wedges, payment_wedges, amount_xmr_wedges, background
        if df.empty:
            messagebox.showwarning("Warning", "No data available to display charts.")
            return

        total_volume_xmr = df['Amount in XMR'].sum()
        total_volume_label.config(text=f"Total Volume in XMR: {total_volume_xmr:.2f}")

        currency_shares = df['Market'].value_counts()
        payment_method_shares = df['Payment method'].value_counts() if 'Payment method' in df.columns else pd.Series()

        # Define the ranges for 'Amount in XMR'
        bins = [0, 10, 50, 100, 200, 300, 400, np.inf]
        labels = ['0-10', '10-50', '50-100', '100-200', '200-300', '300-400', '400+']
        df['Amount Range'] = pd.cut(df['Amount in XMR'], bins=bins, labels=labels)
        amount_xmr_shares = df['Amount Range'].value_counts()

        currency_wedges = create_pie_chart(currency_share_ax, currency_shares, 'Currency Share')
        payment_wedges = create_pie_chart(payment_method_share_ax, payment_method_shares, 'Payment Method Share')
        amount_xmr_wedges = create_pie_chart(amount_xmr_share_ax, amount_xmr_shares, 'Amount in XMR Ranges')

        # Cache the background
        market_share_canvas.draw()
        background = market_share_canvas.copy_from_bbox(market_share_figure.bbox)

        def on_hover(event):
            nonlocal annotation, last_hover_time
            current_time = time.time()
            if current_time - last_hover_time < debounce_interval:
                return
            last_hover_time = current_time

            remove_annotation()
            if event.inaxes == currency_share_ax:
                handle_hover(event, currency_wedges, currency_shares, currency_share_ax, df)
            elif event.inaxes == payment_method_share_ax:
                handle_hover(event, payment_wedges, payment_method_shares, payment_method_share_ax, df)
            elif event.inaxes == amount_xmr_share_ax:
                handle_hover(event, amount_xmr_wedges, amount_xmr_shares, amount_xmr_share_ax, df)

        def remove_annotation():
            nonlocal annotation
            if annotation:
                annotation.remove()
                annotation = None
                market_share_canvas.restore_region(background)
                market_share_canvas.blit(market_share_figure.bbox)

        def on_resize(event):
            nonlocal background
            market_share_canvas.draw()
            background = market_share_canvas.copy_from_bbox(market_share_figure.bbox)

        market_share_figure.canvas.mpl_connect('motion_notify_event', on_hover)
        market_share_figure.canvas.mpl_connect('resize_event', on_resize)
        market_share_canvas.draw()
        gc.collect()

    def create_pie_chart(ax, shares, title):
        if shares.empty:
            ax.clear()
            ax.set_title(title)
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', fontsize=12)
            return []
        else:
            wedges, _, _ = ax.pie(shares, labels=shares.index, autopct='%1.1f%%', startangle=140, pctdistance=0.85)
            ax.set_title(title)
            return wedges

    def handle_hover(event, wedges, shares, ax, df):
        nonlocal annotation
        for wedge in wedges:
            if wedge.contains(event)[0]:
                label = wedge.get_label()
                percentage = shares[label] / shares.sum() * 100
                total_xmr = df[df['Market' if ax == currency_share_ax else 'Payment method' if ax == payment_method_share_ax else 'Amount Range'] == label]['Amount in XMR'].sum()
                annotation = ax.annotate(f'{label}: {percentage:.2f}%\nTotal XMR: {total_xmr:.2f}', xy=(event.xdata, event.ydata), xycoords='data',
                                         xytext=(0, 30), textcoords='offset points',
                                         arrowprops=dict(arrowstyle="->"),
                                         bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="lightyellow"))
                market_share_canvas.restore_region(background)
                ax.draw_artist(annotation)
                market_share_canvas.blit(market_share_figure.bbox)
                break

    update_charts()

def cleanup():
    gc.collect()
    print("Cleanup completed.")

def main():
    root = create_main_window()
    notebook = create_notebook(root)

    def load_data_and_update_ui(file_path):
        with ThreadPoolExecutor() as executor:
            future = executor.submit(load_data, file_path)
            df = future.result()
            first_date, last_date = get_date_range(df)
            create_market_share_tab(notebook, df, first_date, last_date)

    # Start loading data in a separate thread
    load_data_and_update_ui('trade-statistics-all-markets.csv')

    # Register the cleanup function to be called on exit
    atexit.register(cleanup)

    root.mainloop()

if __name__ == "__main__":
    main()
