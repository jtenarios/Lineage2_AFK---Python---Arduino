import random
import time
import threading
from typing import Dict, Tuple, Union, Optional

import serial
import tkinter as tk
from tkinter import ttk

# ---------------- CONFIG ----------------
PORT = "COM17"
BAUDRATE = 9600

KEY_PRESS_TIME = (0.04, 0.12)

# Intervalos en segundos (0 o None = desactivado)
INTERVAL = {
    "F1": 0,
    "F2": 0,
    "F3": (0.8, 2.0),  # /atack
    "F4": (0.8, 2.0),  # /pickup
    "F5": 0,
    "F6": 0,
    "F7": (5, 10),  # combat
    "F8": 0,
    "F9": 0,
    "F10": 120,  # dance buffs
    "F11": 0,
    "F12": 180,  # heal potions
    "ESC": (2, 4),  # esc key
}

PRINT_KEYS = {"F7", "F10", "F12"}
EXTRA_BLOCK = {"F10": 6.0}  # pausa extra bloqueante tras pulsar F10 (como tu script)

ALL_KEYS = [f"F{i}" for i in range(1, 13)] + ["ESC"]
Interval = Union[float, Tuple[float, float]]


# ---------------- HELPERS ----------------
def now() -> float:
    return time.monotonic()


def next_interval(value: Interval) -> float:
    """value puede ser número fijo o tupla (min,max)."""
    if not value:
        return 0.0
    if isinstance(value, tuple):
        return random.uniform(*value)
    return float(value)


def format_interval(cfg: Interval) -> str:
    if not cfg:
        return "-"
    if isinstance(cfg, tuple):
        return f"{cfg[0]}–{cfg[1]}s"
    return f"{cfg}s"


# ---------------- SHARED STATE ----------------
class SharedState:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = True
        self.connected = False
        self.status = "Iniciando..."

        # schedule[key] = monotonic time when next trigger happens
        self.schedule: Dict[str, Optional[float]] = {k: None for k in ALL_KEYS}

        # last_due[key] = previous schedule (used to compute progress)
        self.last_due: Dict[str, Optional[float]] = {k: None for k in ALL_KEYS}

        # last_interval_used[key] = interval seconds actually scheduled for this cycle
        self.last_interval_used: Dict[str, Optional[float]] = {
            k: None for k in ALL_KEYS
        }

        self.last_action = "-"


STATE = SharedState()


# ---------------- SERIAL + SCHEDULER ----------------
def send_key(ser: serial.Serial, key: str) -> None:
    ser.write(f"{key}\n".encode("utf-8"))
    time.sleep(random.uniform(*KEY_PRESS_TIME))

    if key in PRINT_KEYS:
        print(f"Acción {key}", flush=True)

    extra = EXTRA_BLOCK.get(key, 0.0)
    if extra:
        time.sleep(extra)


def scheduler_thread():
    while True:
        with STATE.lock:
            if not STATE.running:
                break

        try:
            with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:
                time.sleep(2)
                with STATE.lock:
                    STATE.connected = True
                    STATE.status = f"Conectado a {PORT} @ {BAUDRATE}"

                    # Inicializa schedule
                    for key in ALL_KEYS:
                        cfg = INTERVAL.get(key, 0)
                        iv = next_interval(cfg)
                        if iv > 0:
                            due = now() + iv
                            STATE.last_due[key] = due - iv
                            STATE.last_interval_used[key] = iv
                            STATE.schedule[key] = due
                        else:
                            STATE.last_due[key] = None
                            STATE.last_interval_used[key] = None
                            STATE.schedule[key] = None

                # Loop principal
                while True:
                    with STATE.lock:
                        if not STATE.running:
                            break

                    t = now()

                    for key in ALL_KEYS:
                        with STATE.lock:
                            due = STATE.schedule.get(key)

                        if due is None:
                            continue

                        if t >= due:
                            send_key(ser, key)

                            with STATE.lock:
                                STATE.last_action = key

                                cfg = INTERVAL.get(key, 0)
                                iv = next_interval(cfg)
                                if iv > 0:
                                    new_due = now() + iv
                                    STATE.last_due[key] = new_due - iv
                                    STATE.last_interval_used[key] = iv
                                    STATE.schedule[key] = new_due
                                else:
                                    STATE.last_due[key] = None
                                    STATE.last_interval_used[key] = None
                                    STATE.schedule[key] = None

                    time.sleep(0.01)

        except serial.SerialException as e:
            with STATE.lock:
                STATE.connected = False
                STATE.status = f"Serial error: {e}. Reintentando..."
            time.sleep(2)
        except Exception as e:
            with STATE.lock:
                STATE.connected = False
                STATE.status = f"Error inesperado: {e}. Parando."
                STATE.running = False
            break


# ---------------- UI ----------------
class KeyRow(ttk.Frame):
    def __init__(self, parent, key: str):
        super().__init__(parent, padding=(6, 4))
        self.key = key

        self.key_lbl = ttk.Label(self, text=key, width=4)
        self.key_lbl.grid(row=0, column=0, sticky="w")

        self.interval_lbl = ttk.Label(
            self, text=format_interval(INTERVAL.get(key, 0)), width=10
        )
        self.interval_lbl.grid(row=0, column=1, sticky="w", padx=(6, 10))

        self.pb = ttk.Progressbar(
            self, orient="horizontal", length=320, mode="determinate", maximum=100
        )
        self.pb.grid(row=0, column=2, sticky="ew", padx=(0, 10))

        self.cool_lbl = ttk.Label(self, text="-", width=10)
        self.cool_lbl.grid(row=0, column=3, sticky="e")

        self.columnconfigure(2, weight=1)

        self.enabled = bool(INTERVAL.get(key, 0))
        if not self.enabled:
            self.pb["value"] = 0

    def update_row(
        self,
        t: float,
        due: Optional[float],
        last_due: Optional[float],
        interval_used: Optional[float],
    ):
        cfg = INTERVAL.get(self.key, 0)
        enabled = bool(cfg)

        if (
            not enabled
            or due is None
            or last_due is None
            or not interval_used
            or interval_used <= 0
        ):
            self.pb["value"] = 0
            self.cool_lbl.config(text="-")
            return

        remaining = due - t
        if remaining < 0:
            remaining = 0

        # Progreso: 0..100 según cuánto ha pasado desde last_due
        elapsed = t - last_due
        pct = (elapsed / interval_used) * 100.0
        if pct < 0:
            pct = 0
        if pct > 100:
            pct = 100

        self.pb["value"] = pct
        self.cool_lbl.config(text=f"{int(remaining)}s")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Monitor F1–F12 (Cooldown + Progreso)")
        self.geometry("720x520")

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        self.status_var = tk.StringVar(value="...")
        self.last_action_var = tk.StringVar(value="-")

        ttk.Label(top, text="Estado:").pack(side="left")
        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=(6, 18))

        ttk.Label(top, text="Última tecla:").pack(side="left")
        ttk.Label(top, textvariable=self.last_action_var).pack(
            side="left", padx=(6, 18)
        )

        self.stop_btn = ttk.Button(top, text="Salir", command=self.on_close)
        self.stop_btn.pack(side="right")

        # Headers
        hdr = ttk.Frame(self, padding=(10, 0))
        hdr.pack(fill="x")

        ttk.Label(hdr, text="Key", width=4).grid(row=0, column=0, sticky="w")
        ttk.Label(hdr, text="Intervalo", width=10).grid(
            row=0, column=1, sticky="w", padx=(6, 10)
        )
        ttk.Label(hdr, text="Progreso hasta siguiente", width=28).grid(
            row=0, column=2, sticky="w"
        )
        ttk.Label(hdr, text="Cooldown", width=10).grid(row=0, column=3, sticky="e")

        # Rows
        body = ttk.Frame(self, padding=10)
        body.pack(fill="both", expand=True)

        self.rows: Dict[str, KeyRow] = {}
        for r, key in enumerate(ALL_KEYS):
            row = KeyRow(body, key)
            row.grid(row=r, column=0, sticky="ew", pady=2)
            self.rows[key] = row
        body.columnconfigure(0, weight=1)

        self.after(100, self.refresh)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def refresh(self):
        t = now()
        with STATE.lock:
            self.status_var.set(STATE.status)
            self.last_action_var.set(STATE.last_action)
            schedule = dict(STATE.schedule)
            last_due = dict(STATE.last_due)
            interval_used = dict(STATE.last_interval_used)

        for key in ALL_KEYS:
            self.rows[key].update_row(
                t=t,
                due=schedule.get(key),
                last_due=last_due.get(key),
                interval_used=interval_used.get(key),
            )

        if STATE.running:
            self.after(100, self.refresh)

    def on_close(self):
        with STATE.lock:
            STATE.running = False
            STATE.status = "Cerrando..."
        self.destroy()


def main():
    th = threading.Thread(target=scheduler_thread, daemon=True)
    th.start()

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
