#!/home/pi/code/envPumma/bin/python3

import serial
import json
import paho.mqtt.client as mqtt
import time
import os
from datetime import datetime

# Konfigurasi Serial
SERIAL_PORT = '/dev/Nano'
BAUD_RATE = 115200
MAX_RETRIES = 5
SERIAL_TIMEOUT = 1

# Konfigurasi MQTT
MQTT_BROKER = ""
MQTT_PORT = 1883
MQTT_TOPIC = ""
MQTT_USER = ""
MQTT_PASSWORD = ""

# Global variables
ser = None
client = None
last_send_time = time.time()
last_data_time = time.time()
data_error_count = 0

def init_serial():
    """Inisialisasi koneksi serial dengan retry jika gagal."""
    global ser
    for attempt in range(MAX_RETRIES):
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT)
            print(f"Serial connected on attempt {attempt + 1}")
            return ser
        except serial.SerialException as e:
            print(f"Failed to connect to serial (attempt {attempt + 1}): {e}")
            time.sleep(2)  # Tunggu sebelum mencoba ulang
    print("Failed to connect to serial after retries. Please check hardware.")
    return None

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker")
    else:
        print(f"Failed to connect to MQTT, return code {rc}")

def on_disconnect(client, userdata, rc):
    print("MQTT Disconnected. Attempting to reconnect...")
    try:
        client.reconnect()
        print("Reconnected to MQTT Broker")
    except Exception as e:
        print(f"Failed to reconnect to MQTT: {e}")

def init_mqtt():
    """Inisialisasi koneksi MQTT."""
    global client
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        return client
    except Exception as e:
        print(f"MQTT initialization error: {e}")
        return None

def process_data(data):
    """Memproses data dari serial dan mengirimkan ke MQTT."""
    global last_send_time, data_error_count
    try:
        ts_nano = data.get("TS_Nano", 0)
        maxbotic_1 = float(data.get("Maxbotic2", 0.0))
        maxbotic_mentah = round((maxbotic_1 / 100), 3)
        maxbotic_hitung = round(2.198 - maxbotic_mentah, 2)
        maxbotic1 = 1.0 + maxbotic_hitung

        ts_human = datetime.utcfromtimestamp(ts_nano).strftime('%Y-%m-%d %H:%M:%S')
        ts_current = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        new_data = {
            "TS": ts_current,
            "TS_Nano": ts_human,
            "maxbotic2": maxbotic1
        }

        current_time = time.time()
        if current_time - last_send_time >= 1:  # Kirim data tiap 1 detik
            result = client.publish(MQTT_TOPIC, json.dumps(new_data), qos=0)
            if result.rc == 0:
                print("Data sent:", new_data)
                last_send_time = current_time
            else:
                print("Failed to publish data, result code:", result.rc)

    except (ValueError, TypeError, KeyError) as e:
        print(f"Error processing data: {e}")
        data_error_count += 1
        if data_error_count > 3:
            print("Too many errors, resetting serial buffer...")
            ser.reset_input_buffer()
            data_error_count = 0

def read_serial():
    """Membaca data dari serial port."""
    global last_data_time
    buffer = ""
    try:
        while ser.in_waiting:
            chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            buffer += chunk
            if buffer.startswith("{") and buffer.endswith("}"):
                try:
                    data = json.loads(buffer)
                    process_data(data)
                    buffer = ""
                    last_data_time = time.time()
                except json.JSONDecodeError:
                    print(f"JSON Decode Error: {buffer}")
                    buffer = ""
    except serial.SerialException as e:
        print(f"Serial read error: {e}. Reinitializing connection...")
        ser.close()
        return init_serial()

def check_serial_timeout():
    """Memeriksa apakah koneksi serial masih aktif."""
    global ser
    if time.time() - last_data_time > 10:  # Jika tidak ada data selama 10 detik
        print("No data received for 10 seconds. Restarting serial connection...")
        try:
            ser.close()
        except Exception as e:
            print(f"Error closing serial: {e}")
        return init_serial()
    return ser

if __name__ == "__main__":
    ser = init_serial()
    client = init_mqtt()

    if ser and client:
        try:
            while True:  # Loop utama tanpa threading
                ser = check_serial_timeout()
                if ser:
                    ser = read_serial()
                time.sleep(0.01)  # Interval loop utama
        except KeyboardInterrupt:
            print("Program interrupted. Exiting...")
        finally:
            if ser:
                ser.close()
            if client:
                client.loop_stop()
                client.disconnect()
    else:
        print("Failed to initialize serial or MQTT connection. Exiting...")
