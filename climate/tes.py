#!/home/pi/code/envPumma/bin/python3

import csv
import json
import time
import os
import threading
from queue import Queue
import paho.mqtt.client as mqtt
import numpy as np
import minimalmodbus
from sht31 import SHT3X
from readWindDir import read_sensor_data as read_wind_direction
from raingauge import sensor as rainfall_sensor
from suhuA import read_temp as read_water_temp_top
from suhuB import read_temp as read_water_temp_bottom
from pyrano import read_pyranometer
from lps28dfw import LPS28DFW, LPS28DFW_OK, LPS28DFW_10Hz

# Initialize anemometer
try:
    anemometer = minimalmodbus.Instrument('/dev/Wind_Speed', 2)
    anemometer.serial.baudrate = 9600
    anemometer.serial.bytesize = 8
    anemometer.serial.parity = minimalmodbus.serial.PARITY_NONE
    anemometer.serial.stopbits = 1
    anemometer.serial.timeout = 1
    anemometer_port_found = True
except IOError as e:
    print(f"Anemometer port tidak ditemukan: {e}")
    anemometer = None
    anemometer_port_found = False

# Sensor locks
anemometer_lock = threading.Lock()
wind_direction_lock = threading.Lock()
rainfall_lock = threading.Lock()
sht31_lock = threading.Lock()
water_temp_top_lock = threading.Lock()
water_temp_bottom_lock = threading.Lock()
solar_lock = threading.Lock()
pressure_lock = threading.Lock()

# MQTT Configuration
MQTT_BROKER = "vps.isi-net.org"
MQTT_PORT = 1883
MQTT_USER = "unila"
MQTT_PASSWORD = "pwdMQTT@123"
MQTT_TOPIC = "Pumma/Climate_sensor_telemetry"

# Initialize MQTT client
client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

# MQTT Handlers
def on_connect(client, userdata, flags, rc):
    if rc != 0:
        print(f"Failed to connect to MQTT broker with code: {rc}")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("MQTT connection lost. Attempting to reconnect...")
        while not client.is_connected():
            try:
                client.reconnect()
                break
            except:
                time.sleep(1)

client.on_connect = on_connect
client.on_disconnect = on_disconnect

try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
except Exception as e:
    print(f"Failed to connect to MQTT broker: {e}")

# Safe Read Function
def read_with_retry(read_func, lock, max_attempts=10, retry_delay=0.1):
    for attempt in range(max_attempts):
        try:
            with lock:
                result = read_func()
                if isinstance(result, (int, float)):
                    return result
                elif isinstance(result, dict):
                    return result
            time.sleep(retry_delay)
        except Exception as e:
            if attempt == max_attempts - 1:
                print(f"Failed after {max_attempts} attempts: {e}")
            time.sleep(retry_delay)
    return None

def main():
    print("Starting sensor monitoring...")
    next_reading_time = time.time()

    while True:
        try:
            start_time = time.time()
            next_reading_time += 1.0

            result_queue = Queue()
            threads = [
                threading.Thread(target=lambda: result_queue.put(("anemometer", read_with_retry(read_anemometer, anemometer_lock)))),
                threading.Thread(target=lambda: result_queue.put(("wind", read_with_retry(read_wind_direction, wind_direction_lock)))),
                threading.Thread(target=lambda: result_queue.put(("rainfall", read_with_retry(read_rainfall_safe, rainfall_lock)))),
                threading.Thread(target=lambda: result_queue.put(("sht31", read_with_retry(read_sht31_safe, sht31_lock)))),
                threading.Thread(target=lambda: result_queue.put(("water_temp_top", {"suhu_air_atas": read_with_retry(read_water_temp_top, water_temp_top_lock)}))),
                threading.Thread(target=lambda: result_queue.put(("water_temp_bottom", {"suhu_air_bawah": read_with_retry(read_water_temp_bottom, water_temp_bottom_lock)}))),
                threading.Thread(target=lambda: result_queue.put(("solar", {"solar": read_with_retry(read_pyranometer, solar_lock)}))),
                threading.Thread(target=lambda: result_queue.put(("pressure", {"pressure": read_with_retry(read_pressure_safe, pressure_lock)})))
            ]

            for thread in threads:
                thread.daemon = True
                thread.start()

            for thread in threads:
                thread.join(timeout=0.8)

            result = {}
            while not result_queue.empty():
                key, data = result_queue.get()
                if isinstance(data, dict):
                    result.update(data)
                else:
                    result[key] = data

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            combined_data = {
                "TS": timestamp,
                "AnemometerSpeed": result.get("anemometer_speed"),
                "Beaufort_scale": result.get("beaufort_scale"),
                "Angle": result.get("angle"),
                "Direction": result.get("direction"),
                "Rainfall": result.get("rainfall"),
                "Suhu_Air_Atas": result.get("suhu_air_atas"),
                "Suhu_Air_Bawah": result.get("suhu_air_bawah"),
                "Humidity": result.get("humidity"),
                "Temperature": result.get("temperature"),
                "SolarRadiation": result.get("solar"),
                "AirPressure": result.get("pressure")
            }

            print(json.dumps(combined_data, indent=2))

            if client.is_connected():
                client.publish(MQTT_TOPIC, json.dumps(combined_data))
                print("Data successfully sent to MQTT broker")

            elapsed_time = time.time() - start_time
            time.sleep(max(0, 5.0 - elapsed_time))

        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        print(f"Program stopped due to error: {e}")
        client.loop_stop()
        client.disconnect()
