import tkinter as tk
from launcher_ui import SentryUI

if __name__ == "__main__":
    root = tk.Tk()

    app = SentryUI(
        root,
        pairs=["ETH/EUR", "BTC/EUR"],   # add/remove pairs here
        amount_base=1.0,
        interval_sec=10,
        gross_threshold_percent=0.5
    )

    root.mainloop()
