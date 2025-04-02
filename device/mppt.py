#!/home/pi/code/envPumma/bin/python3

import minimalmodbus
import paho.mqtt.client as mqtt
import json
import csv
import os
import time
import threading
from datetime import datetime
from time import sleep
import psutil

# Konfigurasi komunikasi Modbus RTU
sensor = minimalmodbus.Instrument('/dev/MPPT', 1)  # Port serial dan address slave
sensor.serial.baudrate = 115200
sensor.serial.bytesize = 8
sensor.serial.parity = minimalmodbus.serial.PARITY_NONE
sensor.serial.stopbits = 1
sensor.serial.timeout = 10

# Konfigurasi MQTT
MQTT_BROKER = ""
MQTT_PORT = 1883
MQTT_TOPIC = ""
MQTT_USERNAME = ""
MQTT_PASSWORD = ""

# Inisialisasi MQTT client
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

def connect_mqtt():
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        return True
    except Exception as e:
        print(f"Gagal terhubung ke MQTT: {e}")
        return False

# Header CSV
FIELDNAMES = ["TS", "pv_voltage", "pv_current", "pv_power", "battery_voltage", "battery_charger_current", "device_current", "device_power", "raspi_temperature", "cpu_usage", "disk_free","disk_total","disk_used","disk_percent"]

def save_to_csv(data):
    date_str = time.strftime("%d-%m-%Y")
    filename = f"/home/pi/Data/InfoSistem_Log/Device/Device_{date_str}.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow(data)

def read_sensor_data():
    try:
        data = sensor.read_registers(0x3100, 11, functioncode=4)
        return {
            "pv_voltage": round(data[0] / 100.0, 3),
            "pv_current": round(data[1] / 100.0, 3),
            "pv_power": round(data[2] / 100.0, 3),
            "battery_voltage": round(data[4] / 100.0, 3),
            "battery_charger_current": round(data[5] / 100.0, 3),
            "device_current": round(data[9] / 100.0, 3),
            "device_power": round(data[10] / 100.0, 3)
        }
    except Exception as e:
        print(f"Kesalahan membaca sensor: {e}")
        return {}

def read_raspi_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as file:
            return round(float(file.read().strip()) / 1000.0, 3)
    except Exception as e:
        print(f"Kesalahan membaca suhu Raspberry Pi: {e}")
        return None

def get_system_stats():
    cpu_usage = round(psutil.cpu_percent(interval=1), 3)
    disk_usage = psutil.disk_usage('/')
    return {
        "cpu_usage": cpu_usage,
        "disk_free": round(disk_usage.free / (1024 ** 3), 3),
        "disk_total": round(disk_usage.total / (1024 ** 3), 3),
        "disk_used": round(disk_usage.used / (1024 ** 3), 3),
        "disk_percent": round(disk_usage.percent, 3)
    }

def publish_data(data):
    try:
        mqtt_client.publish(MQTT_TOPIC, json.dumps(data))
        print(f"Data terkirim ke MQTT: {data}")
    except Exception as e:
        print(f"Gagal mengirim data ke MQTT: {e}")

def collect_and_process():
    mqtt_connected = connect_mqtt()

    while True:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        sensor_data = read_sensor_data()
        raspi_temp = read_raspi_temperature()
        system_stats = get_system_stats()

        if sensor_data and raspi_temp is not None:
            combined_data = {
                "TS": timestamp,
                **sensor_data,
                "raspi_temperature": raspi_temp,
                **system_stats
            }
            save_to_csv(combined_data)
            if mqtt_connected:
                publish_data(combined_data)
            else:
                print("Data hanya disimpan ke lokal karena MQTT tidak terhubung.")
        else:
            print("Gagal membaca data sensor atau suhu Raspberry Pi.")
        
        time.sleep(60)  # Interval pengiriman data

if __name__ == "__main__":
    thread = threading.Thread(target=collect_and_process, daemon=True)
    thread.start()
    while True:
        time.sleep(30)  # Menjaga program tetap berjalan
