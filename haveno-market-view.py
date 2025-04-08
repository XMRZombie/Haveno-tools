#!/usr/bin/python3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import gc
import time
import os
import numpy as np
import atexit
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

class HavenoStatsApp:
    def __init__(self, root, file_path):
        self.root = root
        self.file_path = file_path
        self.df = pd.DataFrame()
        self.first_date = None
        self.last_date = None
        self.lock = Lock()
        self.annotation = None
        self.background = None
        self.last_hover_time = 0
        self.debounce_interval = 0.1  # 100 ms debounce interval

        self.create_ui()
        self.load_data_and_update_ui()

    def create_ui(self):
        self.root.title("Haveno Stats")

        # Create the notebook widget for tabbed layout
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)

        # Create the Market Share tab
        self.market_share_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.market_share_tab, text='Market Share')

        # Set up labels for start date, end date, and total volume
        self.info_frame = ttk.Frame(self.market_share_tab)
        self.info_frame.pack(fill='x', padx=10, pady=5)
        self.start_date_label = tk.Label(self.info_frame, text="From: N/A")
        self.start_date_label.pack(side='left')
        self.end_date_label = tk.Label(self.info_frame, text="To: N/A")
        self.end_date_label.pack(side='left', padx=10)
        self.total_volume_label = tk.Label(self.info_frame, text="Total Volume in XMR: 0")
        self.total_volume_label.pack(side='left')

        # Create Matplotlib Figure and Subplots
        self.market_share_figure = plt.Figure(figsize=(18, 6), dpi=100)
        self.currency_share_ax = self.market_share_figure.add_subplot(131)
        self.payment_method_share_ax = self.market_share_figure.add_subplot(132)
        self.amount_xmr_share_ax = self.market_share_figure.add_subplot(133)

        # Adjust layout for the figure
        self.market_share_figure.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1, wspace=0.3)

        # Create canvas to embed Matplotlib figure in Tkinter
        self.market_share_canvas = FigureCanvasTkAgg(self.market_share_figure, self.market_share_tab)
        self.market_share_canvas.get_tk_widget().pack(fill='both', expand=True)

        # Bind hover and resize events
        self.market_share_figure.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.market_share_figure.canvas.mpl_connect('resize_event', self.on_resize)

    def load_data(self):
        if not os.path.exists(self.file_path):
            messagebox.showerror("Error", f"Data file '{self.file_path}' not found.")
            return pd.DataFrame()

        try:
            use_cols = ['Date/Time', 'Amount in XMR', 'Amount', 'Market', 'Payment method']
            df = pd.read_csv(self.file_path, usecols=use_cols)
            df['Date/Time'] = pd.to_datetime(df['Date/Time'])
            df['Amount in XMR'] = df['Amount in XMR'].astype(float)

            # Clean up payment methods
            df['Payment method'] = df['Payment method'].replace({
                'SEPA Instant Payments': 'SEPA',
                'Cryptocurrencies Instant': 'Cryptocurrencies'
            })

            return df
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")
            return pd.DataFrame()

    def update_ui(self):
        with self.lock:
            if self.df.empty:
                messagebox.showwarning("Warning", "No data available to display charts.")
                return

            total_volume_xmr = self.df['Amount in XMR'].sum()
            self.total_volume_label.config(text=f"Total Volume in XMR: {total_volume_xmr:.2f}")

            # Update charts
            currency_shares = self.df['Market'].value_counts()
            payment_method_shares = self.df['Payment method'].value_counts() if 'Payment method' in self.df.columns else pd.Series()
            amount_xmr_shares_percentage = self.compute_amount_xmr_shares()

            self.create_pie_chart(self.currency_share_ax, currency_shares, 'Currency Share')
            self.create_pie_chart(self.payment_method_share_ax, payment_method_shares, 'Payment Method Share')
            self.create_pie_chart(self.amount_xmr_share_ax, amount_xmr_shares_percentage, 'Amount in XMR Ranges')

            # Cache the background for hover annotations
            self.market_share_canvas.draw()
            self.background = self.market_share_canvas.copy_from_bbox(self.market_share_figure.bbox)

            # Update the labels for date range
            self.start_date_label.config(text=f"From: {self.first_date if self.first_date else 'N/A'}")
            self.end_date_label.config(text=f"To: {self.last_date if self.last_date else 'N/A'}")

    def load_data_and_update_ui(self):
        with ThreadPoolExecutor() as executor:
            future = executor.submit(self.load_data)
            self.df = future.result()
            if not self.df.empty:
                self.first_date, self.last_date = self.get_date_range()
                self.update_ui()

    def get_date_range(self):
        if self.df.empty:
            return None, None
        first_date = self.df['Date/Time'].min().date()
        last_date = self.df['Date/Time'].max().date()
        return first_date, last_date

    def compute_amount_xmr_shares(self):
        # Define the ranges for 'Amount in XMR'
        bins = [0, 10, 50, 100, 200, 300, 400, np.inf]
        labels = ['0-10', '10-50', '50-100', '100-200', '200-300', '300-400', '400+']
        self.df['Amount Range'] = pd.cut(self.df['Amount in XMR'], bins=bins, labels=labels)

        # Calculate total XMR in each range (sum, not count)
        amount_xmr_shares = self.df.groupby('Amount Range')['Amount in XMR'].sum()

        # Calculate percentage shares of the amount ranges, relative to the total XMR
        total_xmr = amount_xmr_shares.sum()
        amount_xmr_shares_percentage = (amount_xmr_shares / total_xmr) * 100

        return amount_xmr_shares_percentage

    def create_pie_chart(self, ax, shares, title):
        if shares.empty:
            ax.clear()
            ax.set_title(title)
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', fontsize=12)
        else:
            wedges, _, _ = ax.pie(shares, labels=shares.index, autopct='%1.1f%%', startangle=140, pctdistance=0.85)
            ax.set_title(title)
            return wedges

    def on_hover(self, event):
        current_time = time.time()
        if current_time - self.last_hover_time < self.debounce_interval:
            return

        self.last_hover_time = current_time
        self.remove_annotation()

        if event.inaxes == self.currency_share_ax:
            self.handle_hover(event, self.currency_share_ax, self.df['Market'])
        elif event.inaxes == self.payment_method_share_ax:
            self.handle_hover(event, self.payment_method_share_ax, self.df['Payment method'])
        elif event.inaxes == self.amount_xmr_share_ax:
            self.handle_hover(event, self.amount_xmr_share_ax, self.df['Amount Range'])

    def handle_hover(self, event, ax, column_data):
        for wedge in ax.patches:
            if wedge.contains(event)[0]:
                label = wedge.get_label()
                percentage = column_data.value_counts()[label] / column_data.value_counts().sum() * 100
                total_xmr = self.df[self.df[column_data.name] == label]['Amount in XMR'].sum()
                self.annotation = ax.annotate(f'{label}: {percentage:.2f}%\nTotal XMR: {total_xmr:.2f}',
                                              xy=(event.xdata, event.ydata), xycoords='data',
                                              xytext=(0, 30), textcoords='offset points',
                                              arrowprops=dict(arrowstyle="->"),
                                              bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="lightyellow"))
                self.market_share_canvas.restore_region(self.background)
                ax.draw_artist(self.annotation)
                self.market_share_canvas.blit(self.market_share_figure.bbox)
                break

    def remove_annotation(self):
        if self.annotation:
            self.annotation.remove()
            self.annotation = None
            self.market_share_canvas.restore_region(self.background)
            self.market_share_canvas.blit(self.market_share_figure.bbox)

    def on_resize(self, event):
        self.market_share_canvas.draw()
        self.background = self.market_share_canvas.copy_from_bbox(self.market_share_figure.bbox)

def cleanup():
    gc.collect()
    print("Cleanup completed.")

def main():
    root = tk.Tk()

    # Open file dialog to select the CSV file
    file_path = filedialog.askopenfilename(title="Select CSV file containing market stats", filetypes=[("CSV Files", "*.csv")])
    if not file_path:
        messagebox.showerror("Error", "No file selected.")
        return

    app = HavenoStatsApp(root, file_path)

    # Register cleanup function on exit
    atexit.register(cleanup)

    # Start the Tkinter main loop
    root.mainloop()

if __name__ == "__main__":
    main()
