#!/home/pi/code/envPumma/bin/python3
# -*- coding: utf-8 -*-
import minimalmodbus
import time

# Konfigurasi pyranometer
PORT = '/dev/ttyUSB0'  # Pastikan ini sesuai dengan koneksi Anda
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
            # Membaca 1 register dari alamat 0x0000 dengan fungsi 0x03
            solar_radiation = pyranometer.read_register(0x0000, 0, functioncode=3)
            print(f"Solar Radiation: {solar_radiation} W/m²")
            return solar_radiation
        except minimalmodbus.NoResponseError:
            print("[ERROR] No response from pyranometer. Retrying...")
        except minimalmodbus.InvalidResponseError:
            print("[ERROR] Invalid response received. Retrying...")
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}. Retrying...")

        retries += 1
        time.sleep(1)  # Tunggu sebelum mencoba lagi
    
    print("[ERROR] Failed to read pyranometer data after multiple attempts.")
    return None

if __name__ == "__main__":
    result = read_pyranometer()
    if result is not None:
        print("Successfully read pyranometer data.")
    else:
        print("Failed to read pyranometer data.")
