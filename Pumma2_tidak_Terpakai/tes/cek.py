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
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200
MAX_RETRIES = 5

global ser
ser = None

# Konfigurasi MQTT
MQTT_BROKER = "vps.isi-net.org"
MQTT_PORT = 1883
MQTT_TOPIC = "Pumma/Sebesi_serial"
MQTT_USER = "unila"
MQTT_PASSWORD = "pwdMQTT@123"

global client
client = None
last_send_time = time.time()
last_data_time = time.time()
data_error_count = 0
lock = threading.Lock()
event_stop = threading.Event()

def init_serial():
    global ser
    retries = MAX_RETRIES
    while retries:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print("Serial connected")
            return
        except serial.SerialException as e:
            print(f"Failed to connect to serial ({e}), retrying...")
            retries -= 1
            time.sleep(5)
    print("Serial connection failed after retries. Rebooting...")
    os.system("sudo systemctl restart ardunano.service")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker")
    else:
        print(f"Failed to connect to MQTT, return code {rc}. Retrying...")

def on_disconnect(client, userdata, rc):
    print("MQTT Disconnected. Attempting to reconnect...")
    while not event_stop.is_set():
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
    client.loop_forever()

def process_data(data):
    global last_send_time, last_data_time, data_error_count
    try:
        ts_nano = data.get("TS_Nano", 0)
        maxbotic_1 = float(data.get("Maxbotic1", 0.0))
        maxbotic_2 = float(data.get("Maxbotic2", 0.0))
        maxbotic1 = 4.0 - (maxbotic_1 / 100)
        maxbotic2 = 4.0 - (maxbotic_2 / 100)
        ts_human = datetime.utcfromtimestamp(ts_nano).strftime('%Y-%m-%d %H:%M:%S')
        ts_current = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        new_data = {
            "TS": ts_current,
            "TS_Nano": ts_human,
            "maxbotic1": maxbotic1,
            "maxbotic2": maxbotic2
        }

        last_data_time = time.time()
        with lock:
            if time.time() - last_send_time >= 1:
                client.publish(MQTT_TOPIC, json.dumps(new_data), qos=1)
                last_send_time = time.time()
                print("Data sent:", new_data)
    except Exception as e:
        print(f"Error processing data: {e}")
        data_error_count += 1
        if data_error_count > 3:
            print("Too many errors, restarting serial...")
            ser.close()
            init_serial()
            data_error_count = 0

def read_serial():
    global ser
    buffer = ""
    while not event_stop.is_set():
        try:
            chunk = ser.readline().decode('utf-8', errors='ignore').strip()
            if chunk:
                buffer += chunk
                if buffer.startswith("{") and buffer.endswith("}"):
                    try:
                        data = json.loads(buffer)
                        process_data(data)
                    except json.JSONDecodeError:
                        print(f"JSON Decode Error: {buffer}")
                    buffer = ""
                elif len(buffer) > 500:
                    print("Buffer terlalu panjang, reset...")
                    buffer = ""
        except serial.SerialException:
            print("Serial read error. Reinitializing...")
            ser.close()
            init_serial()
        time.sleep(0.05)

def check_serial_timeout():
    global ser
    while not event_stop.is_set():
        if time.time() - last_data_time > 10:
            print("Checking serial connection...")
            try:
                ser.write(b'\n')
                time.sleep(1)
                if ser.in_waiting == 0:
                    print("No data received, restarting serial...")
                    ser.close()
                    init_serial()
            except serial.SerialException:
                print("Serial error. Reinitializing...")
                ser.close()
                init_serial()
        time.sleep(1)

if __name__ == "__main__":
    try:
        psutil.Process().nice(10)
    except Exception as e:
        print(f"Failed to set process priority: {e}")

    init_serial()
    
    mqtt_thread = threading.Thread(target=mqtt_loop, daemon=True)
    serial_thread = threading.Thread(target=read_serial, daemon=True)
    timeout_thread = threading.Thread(target=check_serial_timeout, daemon=True)
    
    mqtt_thread.start()
    serial_thread.start()
    timeout_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Program interrupted. Exiting...")
        event_stop.set()
        if ser:
            ser.close()
        client.disconnect()
