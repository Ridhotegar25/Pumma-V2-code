#!/home/pi/code/envPumma/bin/python3

import csv
import json
import time
import os
import threading
from queue import Queue
import paho.mqtt.client as mqtt
import numpy as np
from sht31 import SHT3X
from readAnem import read_sensor_data as read_anemometer
from readWindDir import read_sensor_data as read_wind_direction
from raingauge import sensor as rainfall_sensor
from suhuA import read_temp as read_water_temp_top
from suhuB import read_temp as read_water_temp_bottom
from pyrano import read_pyranometer
from lps28dfw import LPS28DFW, LPS28DFW_OK, LPS28DFW_10Hz

# MQTT Configuration
MQTT_BROKER = "vps.isi-net.org"
MQTT_PORT = 1883
MQTT_USER = "unila"
MQTT_PASSWORD = "pwdMQTT@123"
MQTT_TOPIC = "Pumma/Climate_sensor_telemetry"

# Initialize MQTT client
client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

# Initialize LPS28DFW pressure sensor
pressure_sensor = LPS28DFW()

def init_pressure_sensor():
    try:
        if pressure_sensor.begin() != LPS28DFW_OK:
            print("Failed to initialize pressure sensor!")
            return False
        config = {
            'odr': LPS28DFW_10Hz,
            'avg': 0x00
        }
        pressure_sensor.set_mode_config(config)
        return True
    except Exception as e:
        print(f"Error initializing pressure sensor: {e}")
        return False

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

def init_sht31():
    try:
        if SHT3X.begin(RST=4) != 0:
            print("SHT31 initialization failed")
            return False
        
        if not SHT3X.soft_reset():
            print("SHT31 reset failed")
            return False
            
        return True
    except Exception as e:
        print(f"Error initializing SHT31: {e}")
        return False

def save_to_csv(data):
    try:
        date_str = time.strftime("%d-%m-%Y")
        filename = f"/home/pi/data/Data_Climate/climate_{date_str}.csv"
        fieldnames = [
            "TS", "AnemometerSpeed", "Beaufort_scale", 
            "Angle", "Direction", "Rainfall", 
            "Suhu_Air_Atas", "Suhu_Air_Bawah", "Humidity", "Temperature",
            "SolarRadiation", "AirPressure"
        ]

        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, mode="a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()
            writer.writerow(data)
    except Exception as e:
        print(f"Failed to save to CSV: {e}")

def read_with_retry(read_func, max_attempts=10, retry_delay=0.1):
    """
    Generic retry function for sensor readings
    :param read_func: Function to read sensor
    :param max_attempts: Maximum number of retry attempts
    :param retry_delay: Delay between retries in seconds
    :return: Sensor data or None if all attempts fail
    """
    for attempt in range(max_attempts):
        try:
            result = read_func()
            if result is not None:
                return result
            time.sleep(retry_delay)
        except Exception as e:
            if attempt == max_attempts - 1:
                print(f"Failed after {max_attempts} attempts: {e}")
            time.sleep(retry_delay)
    return None

def read_pressure_safe():
    def read_attempt():
        if pressure_sensor.get_sensor_data() == LPS28DFW_OK:
            return round(pressure_sensor.data['pressure'], 2)
        return None
    return read_with_retry(read_attempt)

def read_anemometer_safe():
    def read_attempt():
        data = read_anemometer()
        if data is not None:
            return {
                "anemometer_speed": data.get("anemometer_speed"),
                "beaufort_scale": data.get("beaufort_scale")
            }
        return None
    result = read_with_retry(read_attempt)
    return result if result else {"anemometer_speed": None, "beaufort_scale": None}

def read_wind_direction_safe():
    def read_attempt():
        data = read_wind_direction()
        if data is not None:
            return {
                "angle": data.get("angle"),
                "direction": data.get("direction")
            }
        return None
    result = read_with_retry(read_attempt)
    return result if result else {"angle": None, "direction": None}

def read_rainfall_safe():
    def read_attempt():
        if rainfall_sensor is None:
            return None
        data = rainfall_sensor.get_raw_data()
        if data is not None:
            return {"rainfall": data * 0.3}
        return None
    result = read_with_retry(read_attempt)
    return result if result else {"rainfall": None}

def read_sht31_safe():
    def read_attempt():
        temp = SHT3X.get_temperature_C()
        hum = SHT3X.get_humidity_RH()
        
        if temp is not None and hum is not None and -40 <= temp <= 125 and 0 <= hum <= 100:
            return {
                "temperature": round(temp, 2),
                "humidity": round(hum, 2)
            }
        return None
    result = read_with_retry(read_attempt)
    return result if result else {"temperature": None, "humidity": None}

def read_water_temp_safe(read_func):
    def read_attempt():
        temp = read_func()
        return float(temp) if temp is not None else None
    return read_with_retry(read_attempt)

def read_pyranometer_safe():
    def read_attempt():
        return read_pyranometer()
    return read_with_retry(read_attempt)

# Modify thread timeout in main function to account for retries
def main():
    print("Initializing climate monitoring system...")
    
    if not init_sht31():
        print("Warning: SHT31 sensor initialization failed")
    
    if not init_pressure_sensor():
        print("Warning: Pressure sensor initialization failed")
    
    print("Starting sensor readings...")
    
    while True:
        start_time = time.time()
        
        try:
            result_queue = Queue()

            threads = [
                threading.Thread(target=lambda: result_queue.put(("anemometer", read_anemometer_safe()))),
                threading.Thread(target=lambda: result_queue.put(("wind", read_wind_direction_safe()))),
                threading.Thread(target=lambda: result_queue.put(("rainfall", read_rainfall_safe()))),
                threading.Thread(target=lambda: result_queue.put(("sht31", read_sht31_safe()))),
                threading.Thread(target=lambda: result_queue.put(("water_temp_top", 
                    {"suhu_air_atas": read_water_temp_safe(read_water_temp_top)}))),
                threading.Thread(target=lambda: result_queue.put(("water_temp_bottom", 
                    {"suhu_air_bawah": read_water_temp_safe(read_water_temp_bottom)}))),
                threading.Thread(target=lambda: result_queue.put(("solar", 
                    {"solar": read_pyranometer_safe()}))),
                threading.Thread(target=lambda: result_queue.put(("pressure",
                    {"pressure": read_pressure_safe()})))
            ]
            
            for thread in threads:
                thread.daemon = True
                thread.start()

            # Allow more time for retries while ensuring we don't exceed our 1-second window
            for thread in threads:
                thread.join(timeout=0.8)  # Increased timeout to accommodate retries

            result = {}
            while not result_queue.empty():
                key, data = result_queue.get()
                result[key] = data

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            combined_data = {
                "TS": timestamp,
                "AnemometerSpeed": result.get("anemometer", {}).get("anemometer_speed", None),
                "Beaufort_scale": result.get("anemometer", {}).get("beaufort_scale", None),
                "Angle": result.get("wind", {}).get("angle", None),
                "Direction": result.get("wind", {}).get("direction", None),
                "Rainfall": result.get("rainfall", {}).get("rainfall", None),
                "Suhu_Air_Atas": result.get("water_temp_top", {}).get("suhu_air_atas", None),
                "Suhu_Air_Bawah": result.get("water_temp_bottom", {}).get("suhu_air_bawah", None),
                "Humidity": result.get("sht31", {}).get("humidity", None),
                "Temperature": result.get("sht31", {}).get("temperature", None),
                "SolarRadiation": result.get("solar", {}).get("solar", None),
                "AirPressure": result.get("pressure", {}).get("pressure", None)
            }

            print("\nCollected Sensor Data:")
            print(json.dumps(combined_data, indent=2))
            
            save_to_csv(combined_data)

            if client.is_connected():
                client.publish(MQTT_TOPIC, json.dumps(combined_data))
                print("Data successfully sent to MQTT broker")
            else:
                print("MQTT connection lost - Data not sent")

        except Exception as e:
            print(f"Critical error in main loop: {e}")

        # Calculate sleep time to maintain exact 1-second intervals
        elapsed_time = time.time() - start_time
        sleep_time = max(0, 1.0 - elapsed_time)
        time.sleep(sleep_time)

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
