#!/usr/bin/python3
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import gc
import time
import os

def load_data(file_path):
    if not os.path.exists(file_path):
        messagebox.showerror("Error", f"Data file '{file_path}' not found.")
        return pd.DataFrame()
    try:
        use_cols = ['Date/Time', 'Amount in XMR', 'Amount', 'Market', 'Payment method']
        df = pd.read_csv(file_path, usecols=use_cols)
        df['Date/Time'] = pd.to_datetime(df['Date/Time'])
        df['Amount in XMR'] = df['Amount in XMR'].astype(float)
        df['Amount'] = df['Amount'].str.extract(r'([\d\.]+)').astype(float)
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

    market_share_figure = plt.Figure(figsize=(10, 5), dpi=100)
    currency_share_ax = market_share_figure.add_subplot(121)
    currency_share_ax.set_title('Currency Share')
    payment_method_share_ax = market_share_figure.add_subplot(122)
    payment_method_share_ax.set_title('Payment Method Share')

    start_date_label = tk.Label(market_share_tab, text=f"From: {first_date if first_date else 'N/A'}")
    start_date_label.pack()

    end_date_label = tk.Label(market_share_tab, text=f"To: {last_date if last_date else 'N/A'}")
    end_date_label.pack()

    total_volume_label = tk.Label(market_share_tab, text="Total Volume in XMR: ")
    total_volume_label.pack()

    market_share_canvas = FigureCanvasTkAgg(market_share_figure, market_share_tab)
    market_share_canvas.get_tk_widget().pack(fill='both', expand=True)

    annotation = None
    currency_wedges = []
    payment_wedges = []
    last_hover_time = 0
    debounce_interval = 0.1  # 100 ms debounce interval
    background = None

    def update_charts():
        nonlocal annotation, currency_wedges, payment_wedges, background
        if df.empty:
            messagebox.showwarning("Warning", "No data available to display charts.")
            return

        total_volume_xmr = df['Amount in XMR'].sum()
        total_volume_label.config(text=f"Total Volume in XMR: {total_volume_xmr:.2f}")

        currency_shares = df['Market'].value_counts()
        payment_method_shares = df['Payment method'].value_counts() if 'Payment method' in df.columns else pd.Series()

        currency_wedges = create_pie_chart(currency_share_ax, currency_shares, 'Currency Share')
        payment_wedges = create_pie_chart(payment_method_share_ax, payment_method_shares, 'Payment Method Share')

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
                handle_hover(event, currency_wedges, currency_shares, currency_share_ax)
            elif event.inaxes == payment_method_share_ax:
                handle_hover(event, payment_wedges, payment_method_shares, payment_method_share_ax)

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
            wedges, _, _ = ax.pie(shares, labels=shares.index, autopct='%1.1f%%', startangle=140)
            ax.set_title(title)
            return wedges

    def handle_hover(event, wedges, shares, ax):
        nonlocal annotation
        for wedge in wedges:
            if wedge.contains(event)[0]:
                label = wedge.get_label()
                percentage = shares[label] / shares.sum() * 100
                annotation = ax.annotate(f'{label}: {percentage:.2f}%', xy=(event.xdata, event.ydata), xycoords='data',
                                         xytext=(0, 30), textcoords='offset points',
                                         arrowprops=dict(arrowstyle="->"),
                                         bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="lightyellow"))
                market_share_canvas.restore_region(background)
                ax.draw_artist(annotation)
                market_share_canvas.blit(market_share_figure.bbox)
                break

    update_charts()

def main():
    df = load_data('trades.csv')
    first_date, last_date = get_date_range(df)
    root = create_main_window()
    notebook = create_notebook(root)
    create_market_share_tab(notebook, df, first_date, last_date)
    root.mainloop()

if __name__ == "__main__":
    main()
