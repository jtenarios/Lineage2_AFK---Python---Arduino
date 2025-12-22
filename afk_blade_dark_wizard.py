import serial
import time
import random


# ---------- CONFIG ----------
PORT = "COM17"
BAUDRATE = 9600

KEY_F1 = "F1"
KEY_F2 = "F2"
KEY_F3 = "F3"
KEY_F4 = "F4"
KEY_F5 = "F5"
KEY_F6 = "F6"
KEY_F7 = "F7"
KEY_F8 = "F8"
KEY_F9 = "F9"
KEY_F10 = "F10"
KEY_F11 = "F11"
KEY_F12 = "F12"


def random_interval(init, end):
    return random.uniform(init, end)


KEY_F1_INTERVAL = 0
KEY_F2_INTERVAL = 0
KEY_F3_INTERVAL = random_interval(0.8, 1.2)  # /atact
KEY_F4_INTERVAL = random_interval(0.8, 1.2)  # /pickup
KEY_F5_INTERVAL = 0
KEY_F6_INTERVAL = 0
KEY_F7_INTERVAL = random_interval(15, 20)  # combat
KEY_F8_INTERVAL = 0
KEY_F9_INTERVAL = 0
KEY_F10_INTERVAL = 120  # Dance Buffs
KEY_F11_INTERVAL = 0
KEY_F12_INTERVAL = 180  # Healt potion


# COMBAT_WAIT = (9.0, 12.0)
# LOOT_WAIT = (0.8, 1.2)
KEY_PRESS_TIME = (0.04, 0.12)

# HEAL_INTERVAL = 180
# BUFF_INTERVAL = 120
# COMBAT_VANILLA_INTERNAL = 5
# PICKUP_VANILLA_INTERNAL = 5
# ----------------------------

ser = serial.Serial(PORT, BAUDRATE)
time.sleep(2)


def human_keypress(key):
    ser.write(f"{key}\n".encode())
    time.sleep(random.uniform(*KEY_PRESS_TIME))

    # Print only some KEYS
    if key in ["F7", "F10", "F12"]:
        print("Acción " + f"{key}\n")

    if key in ["F10"]:
        time.sleep(6)  # esperar 5 seg que acaben las danzas


def print_counters(current_time, keys):
    lines = []

    for key, interval, last_name in keys:
        if interval <= 0:
            continue

        remaining = int((globals()[last_name] + interval) - current_time)
        if remaining < 0:
            continue

        lines.append(f"{key} en {remaining} s")

    if lines:
        print(" | ".join(lines))


def now():
    return time.time()


# timers
# last_heal = now()
# last_buff = now()
last_f1 = now()
last_f2 = now()
last_f3 = now()
last_f4 = now()
last_f5 = now()
last_f6 = now()
last_f7 = now()
last_f8 = now()
last_f9 = now()
last_f10 = now()
last_f11 = now()
last_f12 = now()


state = "COMBAT"

last_counter_print = 0

print("AFK bot activo. No mires la pantalla demasiado, canta.")

while True:
    current_time = now()

    keys = [
        (KEY_F1, KEY_F1_INTERVAL, "last_f1"),
        (KEY_F2, KEY_F2_INTERVAL, "last_f2"),
        (KEY_F3, KEY_F3_INTERVAL, "last_f3"),
        (KEY_F4, KEY_F4_INTERVAL, "last_f4"),
        (KEY_F5, KEY_F5_INTERVAL, "last_f5"),
        (KEY_F6, KEY_F6_INTERVAL, "last_f6"),
        (KEY_F7, KEY_F7_INTERVAL, "last_f7"),
        (KEY_F8, KEY_F8_INTERVAL, "last_f8"),
        (KEY_F9, KEY_F9_INTERVAL, "last_f9"),
        (KEY_F10, KEY_F10_INTERVAL, "last_f10"),
        (KEY_F11, KEY_F11_INTERVAL, "last_f11"),
        (KEY_F12, KEY_F12_INTERVAL, "last_f12"),
    ]

    # ---- CONTADOR POR TECLA (CADA SEGUNDO) ----
    if current_time - last_counter_print >= 1:
        print_counters(current_time, keys)
        last_counter_print = current_time

    # ---- EJECUCIÓN ----
    for key, interval, last_name in keys:
        if interval > 0 and current_time - globals()[last_name] >= interval:
            human_keypress(key)
            globals()[last_name] = current_time

    time.sleep(0.01)

    # if KEY_F1_INTERVAL > 0 and current_time - last_f1 >= KEY_F1_INTERVAL:
    #     human_keypress(KEY_F1)
    #     last_f1 = current_time

    # if KEY_F2_INTERVAL > 0 and current_time - last_f2 >= KEY_F2_INTERVAL:
    #     human_keypress(KEY_F2)
    #     last_f2 = current_time

    # if KEY_F3_INTERVAL > 0 and current_time - last_f3 >= KEY_F3_INTERVAL:
    #     human_keypress(KEY_F3)
    #     last_f3 = current_time

    # if KEY_F4_INTERVAL > 0 and current_time - last_f4 >= KEY_F4_INTERVAL:
    #     human_keypress(KEY_F4)
    #     last_f4 = current_time

    # if KEY_F5_INTERVAL > 0 and current_time - last_f5 >= KEY_F5_INTERVAL:
    #     human_keypress(KEY_F5)
    #     last_f5 = current_time

    # if KEY_F6_INTERVAL > 0 and current_time - last_f6 >= KEY_F6_INTERVAL:
    #     human_keypress(KEY_F6)
    #     last_f6 = current_time

    # if KEY_F7_INTERVAL > 0 and current_time - last_f7 >= KEY_F7_INTERVAL:
    #     human_keypress(KEY_F7)
    #     last_f7 = current_time

    # if KEY_F8_INTERVAL > 0 and current_time - last_f8 >= KEY_F8_INTERVAL:
    #     human_keypress(KEY_F8)
    #     last_f8 = current_time

    # if KEY_F9_INTERVAL > 0 and current_time - last_f9 >= KEY_F9_INTERVAL:
    #     human_keypress(KEY_F9)
    #     last_f9 = current_time

    # if KEY_F10_INTERVAL > 0 and current_time - last_f10 >= KEY_F10_INTERVAL:
    #     human_keypress(KEY_F10)
    #     last_f10 = current_time

    # if KEY_F11_INTERVAL > 0 and current_time - last_f11 >= KEY_F11_INTERVAL:
    #     human_keypress(KEY_F11)
    #     last_f11 = current_time

    # if KEY_F12_INTERVAL > 0 and current_time - last_f12 >= KEY_F12_INTERVAL:
    #     human_keypress(KEY_F12)
    #     last_f12 = current_time
