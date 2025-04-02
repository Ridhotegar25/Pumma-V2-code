#!/home/pi/code/envPumma/bin/python3
# -*- coding: utf-8 -*-
import minimalmodbus
import time

# Konfigurasi pyranometer
PORT = '/dev/Pyrano'  # Pastikan ini sesuai dengan koneksi Anda
UNIT_ID = 5  # Sesuai dengan ID perangkat
BAUDRATE = 4800
TIMEOUT = 0.5  # Timeout komunikasi 2 detik
MAX_RETRIES = 5  # Maksimum percobaan membaca data

def read_pyranometer():
    """Membaca data pyranometer dengan retry jika terjadi error."""
    pyranometer = minimalmodbus.Instrument(PORT, UNIT_ID)  # Port dan Unit ID
    pyranometer.serial.baudrate = BAUDRATE
    pyranometer.serial.timeout = TIMEOUT
    pyranometer.mode = minimalmodbus.MODE_RTU

    retries = 0
    while retries < MAX_RETRIES:
        try:
            return pyranometer.read_register(0x0000, 0, functioncode=3)
        except (minimalmodbus.NoResponseError, minimalmodbus.InvalidResponseError, Exception):
            retries += 1
            time.sleep(1)  # Tunggu sebelum mencoba lagi
    
    return None

if __name__ == "__main__":
    result = read_pyranometer()
    print(result)
