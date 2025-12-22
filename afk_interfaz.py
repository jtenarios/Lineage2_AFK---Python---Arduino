import random
import time
import threading
from datetime import datetime
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
    "F7": (15, 20),    # combat
    "F8": 0,
    "F9": 0,
    "F10": 120,        # dance buffs
    "F11": 0,
    "F12": 180,        # heal potions
}

PRINT_KEYS = {"F7", "F10", "F12"}
EXTRA_BLOCK = {"F10": 6.0}  # pausa extra (bloqueante) tras F10

ALL_KEYS = [f"F{i}" for i in range(1, 13)]


# ---------------- TIME HELPERS ----------------
def now() -> float:
    return time.monotonic()

def next_interval(value) -> float:
    """value puede ser número fijo o tupla (min,max)."""
    if not value:
        return 0.0
    if isinstance(value, tuple):
        return random.uniform(*value)
    return float(value)


# ---------------- STATE (shared) ----------------
class SharedState:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = True
        self.connected = False
        self.status = "Iniciando..."

        # schedule[key] = monotonic time when next trigger happens
        self.schedule = {k: None for k in ALL_KEYS}

        # last_pressed_mono[key] = monotonic time of last press
        self.last_pressed_mono = {k: None for k in ALL_KEYS}

        # last_pressed_wall[key] = datetime string of last press
        self.last_pressed_wall = {k: "-" for k in ALL_KEYS}

        # last_action_log: last key pressed
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
    while STATE.running:
        try:
            with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:
                time.sleep(2)

                with STATE.lock:
                    STATE.connected = True
                    STATE.status = f"Conectado a {PORT} @ {BAUDRATE}"
                    # Inicializa schedule según tu INTERVAL
                    for key in ALL_KEYS:
                        cfg = INTERVAL.get(key, 0)
                        iv = next_interval(cfg)
                        STATE.schedule[key] = (now() + iv) if iv > 0 else None

                # Loop principal
                while STATE.running:
                    t = now()

                    # Ejecuta teclas vencidas
                    for key in ALL_KEYS:
                        with STATE.lock:
                            due = STATE.schedule.get(key)

                        if due is None:
                            continue

                        if t >= due:
                            # Dispara
                            send_key(ser, key)

                            # Actualiza estado
                            wall = datetime.now().strftime("%H:%M:%S")
                            with STATE.lock:
                                STATE.last_pressed_mono[key] = now()
                                STATE.last_pressed_wall[key] = wall
                                STATE.last_action = key

                                # Reprograma
                                cfg = INTERVAL.get(key, 0)
                                nxt = next_interval(cfg)
                                STATE.schedule[key] = (now() + nxt) if nxt > 0 else None

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


# ---------------- UI ----------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Key Monitor F1–F12")
        self.geometry("820x420")

        # Top status
        self.status_var = tk.StringVar(value="...")
        self.last_action_var = tk.StringVar(value="-")

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Estado:").pack(side="left")
        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=(6, 20))

        ttk.Label(top, text="Última tecla:").pack(side="left")
        ttk.Label(top, textvariable=self.last_action_var).pack(side="left", padx=(6, 20))

        self.run_btn = ttk.Button(top, text="Stop", command=self.toggle_run)
        self.run_btn.pack(side="right")

        # Table
        cols = ("key", "enabled", "interval", "last_press", "cooldown")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)

        self.tree.heading("key", text="Tecla")
        self.tree.heading("enabled", text="Activa")
        self.tree.heading("interval", text="Intervalo")
        self.tree.heading("last_press", text="Última pulsación")
        self.tree.heading("cooldown", text="Cooldown (s)")

        self.tree.column("key", width=60, anchor="center")
        self.tree.column("enabled", width=60, anchor="center")
        self.tree.column("interval", width=140, anchor="center")
        self.tree.column("last_press", width=140, anchor="center")
        self.tree.column("cooldown", width=120, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.items = {}
        for k in ALL_KEYS:
            cfg = INTERVAL.get(k, 0)
            enabled = "Sí" if cfg else "No"
            interval_text = self.format_interval(cfg)
            item = self.tree.insert("", "end", values=(k, enabled, interval_text, "-", "-"))
            self.items[k] = item

        # Start UI refresh loop
        self.after(150, self.refresh)

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def format_interval(self, cfg) -> str:
        if not cfg:
            return "-"
        if isinstance(cfg, tuple):
            return f"{cfg[0]}–{cfg[1]}s"
        return f"{cfg}s"

    def toggle_run(self):
        with STATE.lock:
            STATE.running = not STATE.running
            running = STATE.running

        # Si lo paras, no mato el thread limpiamente aquí (simplificación),
        # pero al reanudar seguirá (si no se ha cerrado). Para un start/stop real
        # habría que rehacer la lógica de scheduler.
        self.run_btn.config(text="Stop" if running else "Start")

    def refresh(self):
        t = now()
        with STATE.lock:
            status = STATE.status
            last_action = STATE.last_action
            schedule_snapshot = dict(STATE.schedule)
            last_wall = dict(STATE.last_pressed_wall)

        self.status_var.set(status)
        self.last_action_var.set(last_action)

        for k in ALL_KEYS:
            due = schedule_snapshot.get(k)
            cfg = INTERVAL.get(k, 0)

            # cooldown
            if not cfg or due is None:
                cooldown = "-"
            else:
                remaining = int(due - t)
                cooldown = "0" if remaining <= 0 else str(remaining)

            values = (
                k,
                "Sí" if cfg else "No",
                self.format_interval(cfg),
                last_wall.get(k, "-"),
                cooldown,
            )
            self.tree.item(self.items[k], values=values)

        self.after(150, self.refresh)

    def on_close(self):
        with STATE.lock:
            STATE.running = False
        self.destroy()


def main():
    th = threading.Thread(target=scheduler_thread, daemon=True)
    th.start()

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
