#!/home/pi/code/envPumma/bin/python3

import minimalmodbus
import paho.mqtt.client as mqtt
import json
import csv
import os
import time
from datetime import datetime
from time import sleep

# Konfigurasi komunikasi Modbus RTU
sensor = minimalmodbus.Instrument('/dev/MPPT', 1)  # Port serial dan address slave
sensor.serial.baudrate = 115200  # Baudrate
sensor.serial.bytesize = 8  # Ukuran byte
sensor.serial.parity = minimalmodbus.serial.PARITY_NONE  # Paritas
sensor.serial.stopbits = 1  # Stop bit
sensor.serial.timeout = 10  # Timeout komunikasi

# Konfigurasi MQTT
MQTT_BROKER = "vps.isi-net.org"
MQTT_PORT = 1883
MQTT_TOPIC = "Pumma/Sebesi_Device"
MQTT_USERNAME = "unila"
MQTT_PASSWORD = "pwdMQTT@123"

# Inisialisasi MQTT client
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Header CSV
FIELDNAMES = ["TS", "pv_voltage", "pv_current", "pv_power", "battery_voltage", "battery_charger_current", "device_current", "device_power", "raspi_temperature"]

# Fungsi untuk menyimpan data ke CSV
def save_to_csv(data):
    date_str = time.strftime("%d-%m-%Y")
    filename = f"/home/pi/Data/InfoSistem_Log/MPPT/MPPT_{date_str}.csv"

    # Pastikan direktori log ada
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow(data)

# Fungsi untuk membaca data dari register
def read_sensor_data():
    try:
        data = sensor.read_registers(0x3100, 11, functioncode=4)
        return data  # Mengembalikan data sebagai array
    except Exception as e:
        print(f"Kesalahan membaca sensor: {e}")
        return []  # Jika ada error, kembalikan array kosong

# Fungsi untuk membaca suhu CPU Raspberry Pi
def read_raspi_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as file:
            temp = int(file.read().strip()) / 1000.0  # Konversi miliCelcius ke Celcius
        return temp
    except Exception as e:
        print(f"Kesalahan membaca suhu Raspberry Pi: {e}")
        return None

# Fungsi utama
if __name__ == "__main__":
    while True:
        try:
            # Membaca data dari sensor
            sensor_data = read_sensor_data()
            raspi_temp = read_raspi_temperature()

            if sensor_data:
                # Mengatur nilai berdasarkan indeks
                pv_voltage = sensor_data[0] / 100.0
                pv_current = sensor_data[1] / 100.0
                pv_power = sensor_data[2] / 100.0
                battery_voltage = sensor_data[4] / 100.0
                battery_charger_current = sensor_data[5] / 100.0
                device_current = sensor_data[9] / 100.0
                device_power = sensor_data[10] / 100.0

                # Membuat data sebagai dictionary
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                combined_data = {
                    "TS": timestamp,
                    "raspi_temperature": raspi_temp,
                    "pv_voltage": pv_voltage,
                    "pv_current": pv_current,
                    "pv_power": pv_power,
                    "battery_voltage": battery_voltage,
                    "battery_charger_current": battery_charger_current,
                    "device_current": device_current,
                    "device_power": device_power
                }

                # Menyimpan data ke CSV
                save_to_csv(combined_data)

                # Mengirim data melalui MQTT
                mqtt_client.publish(MQTT_TOPIC, json.dumps(combined_data))

                print(f"Data terkirim: {combined_data}")
            else:
                print("Gagal membaca data sensor.")

        except Exception as e:
            print(f"Terjadi kesalahan: {e}")
        time.sleep(60)
