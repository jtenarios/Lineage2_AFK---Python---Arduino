import serial
import time

ser = serial.Serial('COM17', 9600)
time.sleep(2)  # tiempo para que Arduino reinicie

while True:
    ser.write(b'Jaime\n')
    time.sleep(1)