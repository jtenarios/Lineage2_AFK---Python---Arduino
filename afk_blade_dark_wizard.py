import random
import time
import serial

PORT = "COM17"
BAUDRATE = 9600

KEY_PRESS_TIME = (0.04, 0.12)

# Intervalos en segundos (0 o None = desactivado)
INTERVAL = {
    "F1": 0,
    "F2": 0,
    "F3": (0.8, 2.0), # /atack
    "F4": (0.8, 2.0), # /pickup
    "F5": 0,
    "F6": 0,
    "F7": (15, 20),# combat
    "F8": 0,
    "F9": 0,
    "F10": 120, # dance buffs
    "F11": 0,
    "F12": 180, # heal potions
}

PRINT_KEYS = {"F7", "F10", "F12"}
EXTRA_BLOCK = {"F10": 6.0}  # si de verdad quieres bloquear todo

def now() -> float:
    return time.monotonic()

def next_interval(value) -> float:
    """value puede ser número fijo o tupla (min,max)."""
    if not value:
        return 0.0
    if isinstance(value, tuple):
        return random.uniform(*value)
    return float(value)

def send_key(ser: serial.Serial, key: str) -> None:
    ser.write(f"{key}\n".encode("utf-8"))
    time.sleep(random.uniform(*KEY_PRESS_TIME))

    if key in PRINT_KEYS:
        print(f"Acción {key}", flush=True)

    extra = EXTRA_BLOCK.get(key, 0.0)
    if extra:
        time.sleep(extra)

def print_counters(current: float, schedule: dict[str, float]) -> None:
    # schedule[key] = tiempo (monotonic) cuando toca disparar
    lines = []
    for key, due in schedule.items():
        remaining = int(due - current)
        if remaining >= 0:
            lines.append(f"{key} en {remaining}s")
    if lines:
        print(" | ".join(lines), flush=True)

def main():
    with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:
        time.sleep(2)

        # Calcula el próximo disparo por tecla
        schedule = {}
        for key, cfg in INTERVAL.items():
            iv = next_interval(cfg)
            if iv > 0:
                schedule[key] = now() + iv

        last_counter_print = 0.0
        print("AFK bot activo.", flush=True)

        while True:
            t = now()

            if t - last_counter_print >= 1.0:
                print_counters(t, schedule)
                last_counter_print = t

            # Ejecuta las teclas vencidas
            for key in list(schedule.keys()):
                if t >= schedule[key]:
                    send_key(ser, key)
                    schedule[key] = now() + next_interval(INTERVAL[key])

            time.sleep(0.01)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.", flush=True)
