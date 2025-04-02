#!/home/pi/code/envPumma/bin/python3

import serial
import json
import paho.mqtt.client as mqtt
import time
import os
from datetime import datetime
import threading
import psutil

# Konfigurasi Serial
SERIAL_PORT = '/dev/Nano'
BAUD_RATE = 115200
MAX_RETRIES = 5  # Max retries for serial connection

# Konfigurasi MQTT
MQTT_BROKER = "vps.isi-net.org"
MQTT_PORT = 1883
MQTT_TOPIC = "Pumma/Sebesi_serial"
MQTT_USER = "unila"
MQTT_PASSWORD = "pwdMQTT@123"

# Global variables
ser = None
client = None
last_send_time = time.time()
last_data_time = time.time()
data_error_count = 0
lock = threading.Lock()  # Lock for shared resources


def init_serial():
    """Inisialisasi koneksi serial dengan retry jika gagal."""
    retries = MAX_RETRIES
    while retries:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print("Serial connected")
            return ser
        except serial.SerialException:
            print("Failed to connect to serial, retrying...")
            retries -= 1
            time.sleep(15)
    print("Serial connection failed after retries. Rebooting...")
    os.system("sudo reboot")
    return None


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker")
    else:
        print(f"Failed to connect to MQTT, return code {rc}. Retrying...")


def on_disconnect(client, userdata, rc):
    print("MQTT Disconnected. Attempting to reconnect...")
    while True:
        try:
            client.reconnect()
            print("Reconnected to MQTT Broker")
            break
        except:
            print("Reconnection failed. Retrying in 5 seconds...")
            time.sleep(5)


def mqtt_loop():
    global client
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()


def save_log(ts_nano, maxbotic1):
    date_str = datetime.now().strftime("%d-%m-%Y")
    file_path = f"/home/pi/Data/Log_maxbo/Log_MB{date_str}.txt"
    with open(file_path, "a") as file:
        file.write(f"{ts_nano},{maxbotic1}\n")


def process_data(data):
    global last_send_time, last_data_time, data_error_count
    try:
        ts_nano = data.get("TS_Nano", "")
        air_pres = float(data.get("Air_Pres", 0.0))
        maxbotic_1 = float(data.get("Maxbotic1", 0))
        maxbotic_2 = float(data.get("Maxbotic2", 0))
        maxbotic1 = 4.0 - (maxbotic_1 / 100)
        maxbotic2 = 4.0 - (maxbotic_2 / 100)

        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_data = {
            "TS": current_timestamp,
            "TS_Nano": ts_nano,
            "air_pressure": air_pres,
            "maxbotic2": maxbotic2
        }

        last_data_time = time.time()

        # Publish data if 1 second has passed
        with lock:
            if time.time() - last_send_time >= 1:
                try:
                    client.publish(MQTT_TOPIC, json.dumps(new_data), qos=1)
                    last_send_time = time.time()
                    save_log(ts_nano, maxbotic1)
                    print("Data sent:", new_data)
                except Exception as e:
                    print("MQTT Publish Error:", e)

    except (ValueError, TypeError, KeyError) as e:
        print(f"Error processing data: {e}")
        data_error_count += 1
        if data_error_count > 3:
            print("Too many processing errors, restarting serial...")
            ser.close()
            ser = init_serial()
            data_error_count = 0


def read_serial():
    global ser
    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            if line:
                try:
                    data = json.loads(line)
                    process_data(data)
                except json.JSONDecodeError:
                    print("Error decoding JSON line:", line)
        except serial.SerialException:
            print("Serial read error. Reinitializing connection...")
            ser.close()
            ser = init_serial()
        time.sleep(0.1)


def check_serial_timeout():
    global ser
    while True:
        if time.time() - last_data_time > 10:
            print("No data received for 10 seconds. Restarting serial connection...")
            ser.close()
            ser = init_serial()
        time.sleep(1)


if __name__ == "__main__":
    # Menetapkan prioritas proses ke low
    try:
        psutil.Process().nice(10)  # Prioritas rendah (nilai lebih besar, prioritas lebih rendah)
    except Exception as e:
        print(f"Failed to set process priority: {e}")

    # Initialize serial connection and MQTT loop
    ser = init_serial()
    mqtt_loop()

    # Start serial read and timeout check in separate threads
    serial_thread = threading.Thread(target=read_serial, daemon=True)
    timeout_thread = threading.Thread(target=check_serial_timeout, daemon=True)
    serial_thread.start()
    timeout_thread.start()

    # Main loop for program logic
    try:
        while True:
            time.sleep(1)  # Main thread can sleep or manage other tasks
    except KeyboardInterrupt:
        print("Program interrupted. Exiting...")
        if ser:
            ser.close()
        client.loop_stop()
        client.disconnect()
