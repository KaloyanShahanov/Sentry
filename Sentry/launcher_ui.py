import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import threading
import time
from datetime import datetime

from fetchers import fetch_quotes
from logger_setup import setup_logger

logger = setup_logger("launcher_ui")


class SentryUI:
    def __init__(self, root, pairs, amount_base=1.0, interval_sec=10, gross_threshold_percent=0.5):
        self.root = root
        self.pairs = pairs
        self.amount_base = amount_base
        self.interval_sec = interval_sec
        self.gross_threshold_percent = gross_threshold_percent
        self.running = False

        root.title("Sentry Live Monitor")
        root.geometry("900x500")

        header = tk.Label(
            root,
            text=f"Pairs: {', '.join(self.pairs)} | Interval: {self.interval_sec}s | Amount: {self.amount_base}",
            anchor="w",
            font=("Segoe UI", 11)
        )
        header.pack(fill="x", padx=10, pady=(10, 0))

        self.text = ScrolledText(root, wrap="word", font=("Consolas", 10))
        self.text.pack(fill="both", expand=True, padx=10, pady=10)

        btn_frame = tk.Frame(root)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.start_btn = tk.Button(btn_frame, text="Start", command=self.start)
        self.start_btn.pack(side="left")

        self.stop_btn = tk.Button(btn_frame, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(10, 0))

        self.clear_btn = tk.Button(btn_frame, text="Clear", command=self.clear)
        self.clear_btn.pack(side="left", padx=(10, 0))

        self.status = tk.Label(btn_frame, text="Status: Idle", anchor="w")
        self.status.pack(side="right")

    def log_line(self, line: str):
        self.text.insert("end", line + "\n")
        self.text.see("end")

    def clear(self):
        self.text.delete("1.0", "end")

    def start(self):
        if self.running:
            return
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status.config(text="Status: Running")

        t = threading.Thread(target=self.worker_loop, daemon=True)
        t.start()

    def stop(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status.config(text="Status: Stopped")

    def worker_loop(self):
    # import once (avoids repeated imports)
        from Sentry import compute_arbitrage, format_discord_message #should_alert
        from alerts import send_discord_alert

        test_mode = True # change to False when not testing
        while self.running:
            for pair in self.pairs:
                try:
                     buy, sell = fetch_quotes(pair, self.amount_base)
                     result = compute_arbitrage(buy, sell)
                     
                     alert_sent = False

                     if test_mode:
                         send_discord_alert(format_discord_message(result))
                         alert_sent = True


                    # if should_alert(
                    #    result,
                    #    gross_threshold_percent=self.gross_threshold_percent,
                    #    require_net_profit=True
                    # ):
                    #        send_discord_alert(format_discord_message(result))
                    #        alert_sent = True

                     ts = datetime.now().strftime("%H:%M:%S")
                     status = "Positive" if result["profit_eur"] > 0 else "Negative"
                     line = (
                          f"[{ts}] {pair} | "
                          f"{buy.exchange}: {buy.price_quote:.2f} | "
                          f"{sell.exchange}: {sell.price_quote:.2f} | "
                          f"Gross: {result['gross_spread_percent']:.3f}% | "
                          f"Net: {result['profit_percent_net']:.3f}% | "
                          f"Profit: EUR {result['profit_eur']:.2f} ({status}) | "
                          f"Alert: {'SENT' if alert_sent else 'NO'}"
                     )

                     logger.info(line)
                     self.root.after(0, self.log_line, line)

                except Exception as e:
                    ts = datetime.now().strftime("%H:%M:%S")
                    err = f"[{ts}] {pair} | ERROR: {e}"
                    logger.exception(err)
                    self.root.after(0, self.log_line, err)

            for _ in range(self.interval_sec):
                 if not self.running:
                    break
                 time.sleep(1)

