import threading
import tkinter as tk
from tkinter import ttk, messagebox

from fx_manager import FXRateManager


class CurrencyConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Currency Converter")
        self.root.geometry("400x400")
        self.manager = FXRateManager()

        # Styles
        style = ttk.Style()
        style.configure("TButton", padding=6, font=('Helvetica', 10))
        style.configure("TLabel", font=('Helvetica', 10))
        style.configure("Header.TLabel", font=('Helvetica', 12, 'bold'))

        # UI Layout
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(main_frame, text="Currency Converter", style="Header.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Amount Input
        ttk.Label(main_frame, text="Amount:").grid(row=1, column=0, sticky="w")
        self.amount_var = tk.StringVar(value="1")
        self.ent_amount = ttk.Entry(main_frame, textvariable=self.amount_var)
        self.ent_amount.grid(row=1, column=1, sticky="ew", pady=5)

        # From Currency
        ttk.Label(main_frame, text="From:").grid(row=2, column=0, sticky="w")
        self.from_currency = ttk.Combobox(main_frame, state="readonly")
        self.from_currency.grid(row=2, column=1, sticky="ew", pady=5)

        # To Currency
        ttk.Label(main_frame, text="To:").grid(row=3, column=0, sticky="w")
        self.to_currency = ttk.Combobox(main_frame, state="readonly")
        self.to_currency.grid(row=3, column=1, sticky="ew", pady=5)

        # Convert Button
        self.btn_convert = ttk.Button(main_frame, text="Convert", command=self.on_convert)
        self.btn_convert.grid(row=4, column=0, columnspan=2, pady=15, sticky="ew")

        # Result Label
        self.lbl_result = ttk.Label(main_frame, text="Result: -", font=('Helvetica', 12, 'bold'), foreground="#2c3e50")
        self.lbl_result.grid(row=5, column=0, columnspan=2, pady=10)

        ttk.Separator(main_frame, orient='horizontal').grid(row=6, column=0, columnspan=2, sticky="ew", pady=10)

        # Footer (Refresh & Status)
        self.btn_refresh = ttk.Button(main_frame, text="Refresh Rates", command=lambda: self.start_refresh_thread(force_network=True))
        self.btn_refresh.grid(row=7, column=0, sticky="w")

        self.lbl_status = ttk.Label(main_frame, text="Last update: N/A", font=('Helvetica', 8))
        self.lbl_status.grid(row=7, column=1, sticky="e")

        # Grid
        main_frame.columnconfigure(1, weight=1)

        self.start_refresh_thread(force_network=False)

    def start_refresh_thread(self, force_network=False):
        # Background thread for network request
        self.btn_refresh.config(state="disabled", text="Updating...")
        thread = threading.Thread(target=self.refresh_data(force_network=force_network))
        thread.daemon = True
        thread.start()

    def refresh_data(self, force_network):
        # Background task to fetch data
        try:
            is_online = self.manager.refresh_rates(force_network=force_network)
            self.root.after(0, lambda: self.update_ui_after_refresh(is_online, None))
        except Exception as e:
            self.root.after(0, lambda: self.update_ui_after_refresh(False, str(e)))

    def update_ui_after_refresh(self, is_online, error_msg):
        # Updates dropdowns and status labels
        self.btn_refresh.config(state="normal", text="Refresh Rates")

        if error_msg:
            messagebox.showerror("Error", f"Failed to load rates: {error_msg}")
            self.lbl_status.config(text="Status: Error", foreground="red")
            return

        # Populate dropdowns
        currencies = sorted(self.manager.rates.keys())
        self.from_currency['values'] = currencies
        self.to_currency['values'] = currencies

        if not self.from_currency.get(): self.from_currency.set('EUR')
        if not self.to_currency.get(): self.to_currency.set('RON')

        timestamp = self.manager.timestamp
        source_text = "BNR (Live)" if is_online else "Cache (Offline)"
        color = "green" if is_online else "orange"

        self.lbl_status.config(text=f"Last update: {timestamp} [{source_text}]", foreground=color)

    def on_convert(self):
        amount_str = self.amount_var.get().strip()

        # Check if input is a valid float
        try:
            amount = float(amount_str)
            if amount < 0:
                raise ValueError("Negative number")

        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid positive number to convert.")
            return

        try:
            from_currency = self.from_currency.get()
            to_currency = self.to_currency.get()

            if not from_currency or not to_currency:
                messagebox.showwarning("Selection Missing", "Please select both currencies.")
                return

            amount_converted = self.manager.convert(amount, from_currency, to_currency)
            self.lbl_result.config(text=f"{amount} {from_currency} = {amount_converted} {to_currency}")

        except Exception as e:
            messagebox.showerror("Error", str(e))
