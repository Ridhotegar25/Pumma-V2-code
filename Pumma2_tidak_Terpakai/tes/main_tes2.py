#!/home/pi/code/envPumma/bin/python3

import serial
import json
import paho.mqtt.client as mqtt
import time
import os
from datetime import datetime
import threading
import RPi.GPIO as GPIO

# Konfigurasi Serial
SERIAL_PORT = '/dev/Nano'
BAUD_RATE = 9600

# Konfigurasi MQTT
MQTT_BROKER = "vps.isi-net.org"
MQTT_PORT = 1883
MQTT_TOPIC = "Pumma/Sebesi_serial"
MQTT_USER = "unila"
MQTT_PASSWORD = "pwdMQTT@123"

# Konfigurasi GPIO untuk sensor ultrasonik
TRIG = 22
ECHO = 27
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def measure_distance():
    """Mengukur jarak menggunakan sensor ultrasonik JSN-SR04M."""
    GPIO.output(TRIG, False)
    time.sleep(0.05)
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    
    timeout_start = time.time()
    while GPIO.input(ECHO) == 0:
        if time.time() - timeout_start > 0.02:
            return None
    pulse_start = time.time()
    
    timeout_start = time.time()
    while GPIO.input(ECHO) == 1:
        if time.time() - timeout_start > 0.02:
            return None
    pulse_end = time.time()
    
    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    distance = round(distance, 2)
    
    if distance > 400 or distance < 2:
        return None
    
    return distance

# Global variables
ser = None
client = None
last_send_time = time.time()
lock = threading.Lock()
event_stop = threading.Event()

def init_serial():
    """Inisialisasi koneksi serial"""
    try:
        return serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    except serial.SerialException:
        print("Serial connection failed. Restarting service...")
        os.system("sudo systemctl restart ardunano.service")
        return None

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker")
    else:
        print(f"Failed to connect to MQTT, return code {rc}")

def mqtt_loop():
    global client
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

def process_data(data):
    global last_send_time
    try:
        ts_nano = data.get("TS_Nano", 0)
        maxbotic_1 = float(data.get("Maxbotic1", 0.0))
        maxbotic2 = round(4.0 - (maxbotic_1 / 100), 2)
        ts_current = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        jsn_distance = measure_distance()
        
        new_data = {
            "TS": ts_current,
            "TS_Nano": ts_nano,
            "maxbotic2": maxbotic2,
            "JSN_1": jsn_distance if jsn_distance is not None else -1
        }
        
        with lock:
            if time.time() - last_send_time >= 1:
                client.publish(MQTT_TOPIC, json.dumps(new_data), qos=1)
                last_send_time = time.time()
                print("Data sent:", new_data)
    except Exception as e:
        print(f"Error processing data: {e}")

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
                        buffer = ""
                    except json.JSONDecodeError:
                        print(f"JSON Decode Error: {buffer}")
                        buffer = ""
        except serial.SerialException:
            print("Serial read error. Reinitializing connection...")
            ser = init_serial()
        time.sleep(0.05)

if __name__ == "__main__":
    ser = init_serial()
    
    mqtt_thread = threading.Thread(target=mqtt_loop, daemon=True)
    serial_thread = threading.Thread(target=read_serial, daemon=True)
    
    mqtt_thread.start()
    serial_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
        event_stop.set()
        if ser:
            ser.close()
        client.disconnect()
        GPIO.cleanup()
