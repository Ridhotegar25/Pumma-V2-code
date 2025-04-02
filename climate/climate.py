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
from raingauge import DFRobot_RainfallSensor_I2C
from suhuA import read_temp as read_water_temp_top
from suhuB import read_temp as read_water_temp_bottom
from pyrano import read_pyranometer
from lps28dfw import LPS28DFW, LPS28DFW_OK, LPS28DFW_10Hz

# Sensor locks for thread safety
anemometer_lock = threading.Lock()
wind_direction_lock = threading.Lock()
rainfall_lock = threading.Lock()
sht31_lock = threading.Lock()
water_temp_top_lock = threading.Lock()
water_temp_bottom_lock = threading.Lock()
solar_lock = threading.Lock()
pressure_lock = threading.Lock()

# Rainfall sensor configuration
rain_per_tip = 0.3  # mm per tipping bucket
rain_count = 0
last_pulse_time = None
interval = 1  # Interval polling dalam detik
last_value = None  # Menyimpan nilai raw data terakhir
start_time = time.time()  # Waktu mulai

# MQTT Configuration
MQTT_BROKER = ""
MQTT_PORT = 1883
MQTT_USER = ""
MQTT_PASSWORD = ""
MQTT_TOPIC = ""

# Initialize sensors
rainfall_sensor = DFRobot_RainfallSensor_I2C()
pressure_sensor = LPS28DFW()

# Initialize MQTT client
client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

def init_rainfall_sensor():
    global last_value
    try:
        if not rainfall_sensor.begin():
            print("Rainfall sensor not detected")
            return False
        print("Rainfall sensor detected")
        last_value = None
        return True
    except Exception as e:
        print(f"Error initializing rainfall sensor: {e}")
        return False

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

def read_with_retry(read_func, lock, max_attempts=9, retry_delay=0.1):
    for attempt in range(max_attempts):
        try:
            with lock:
                result = read_func()
                if result is not None:
                    return result
            time.sleep(retry_delay)
        except Exception as e:
            if attempt == max_attempts - 1:
                print(f"Failed after {max_attempts} attempts: {e}")
            time.sleep(retry_delay)
    return None

def read_rainfall_safe():
    global last_value, rain_count, start_time, last_pulse_time

    def read_attempt():
        global last_value, rain_count, start_time, last_pulse_time
        
        try:
            rainfall_raw = rainfall_sensor.get_raw_data()
            
            # Menghitung perubahan data raw (tipping bucket)
            if last_value is not None:
                per_tip_rainfall = rainfall_raw - last_value
                rain_count += per_tip_rainfall

            last_value = rainfall_raw

            # Menghitung dan mencatat curah hujan dalam interval waktu tertentu
            if time.time() - start_time >= interval:
                mm = rain_count * rain_per_tip  # Konversi tipping bucket count ke mm
                mm_rounded = round(mm, 3)
                rain_count = 0  # Reset penghitung tipping bucket
                start_time = time.time()  # Reset waktu mulai

                # Menghitung intensitas hujan berbasis waktu antara tipping buckets
                if mm_rounded > 0:  # Jika ada rain detected
                    if last_pulse_time is not None:
                        # Menghitung waktu sejak tipping terakhir
                        time_since_last_pulse = time.time() - last_pulse_time
                        intensity = mm_rounded / time_since_last_pulse  # Intensitas per detik
                        print(f"{intensity:.2f}")
                    
                    # Update waktu terakhir pulse
                    last_pulse_time = time.time()
                    return {"rainfall": mm_rounded}

                # Menampilkan curah hujan jika tidak ada data tipping bucket baru dalam interval
                if mm_rounded == 0:
                    print(f"{mm_rounded}")
                    return {"rainfall": 0.0}
                    
            return {"rainfall": 0.0}
            
        except Exception as e:
            print(f"Error reading rainfall sensor: {e}")
            return None
            
    return read_with_retry(read_attempt, rainfall_lock)

def read_pressure_safe():
    def read_attempt():
        if pressure_sensor.get_sensor_data() == LPS28DFW_OK:
            return round(pressure_sensor.data['pressure'], 2)
        return None
    return read_with_retry(read_attempt, pressure_lock)

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
    result = read_with_retry(read_attempt, sht31_lock)
    return result if result else {"temperature": None, "humidity": None}

def read_anemometer_safe():
    def read_attempt():
        data = read_anemometer()
        if data is not None:
            return {
                "anemometer_speed": data.get("anemometer_speed"),
                "beaufort_scale": data.get("beaufort_scale")
            }
        return None
    result = read_with_retry(read_attempt, anemometer_lock)
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
    result = read_with_retry(read_attempt, wind_direction_lock)
    return result if result else {"angle": None, "direction": None}

def read_water_temp_top_safe():
    def read_attempt():
        try:
            result = read_water_temp_top()
            return result if result is not None else None
        except Exception as e:
            print(f"Error reading top water temperature: {e}")
            return None
    return read_with_retry(read_attempt, water_temp_top_lock)

def read_water_temp_bottom_safe():
    def read_attempt():
        try:
            result = read_water_temp_bottom()
            return result if result is not None else None
        except Exception as e:
            print(f"Error reading bottom water temperature: {e}")
            return None
    return read_with_retry(read_attempt, water_temp_bottom_lock)

def read_pyranometer_safe():
    def read_attempt():
        try:
            result = read_pyranometer()
            return result if result is not None else None
        except Exception as e:
            print(f"Error reading pyranometer: {e}")
            return None
    return read_with_retry(read_attempt, solar_lock)

def main():
    print("Initializing climate monitoring system...")
    
    # Initialize MQTT
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
    
    # Initialize sensors
    if not init_sht31():
        print("Warning: SHT31 sensor initialization failed")
    
    if not init_pressure_sensor():
        print("Warning: Pressure sensor initialization failed")
        
    if not init_rainfall_sensor():
        print("Warning: Rainfall sensor initialization failed")
    
    print("Starting sensor readings...")
    
    next_reading_time = time.time()
    
    while True:
        try:
            current_time = time.time()
            next_reading_time += 1.0  # Update timestamp every 1 second
            
            # Get timestamp at the start
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            
            result_queue = Queue()
            threads = [
                threading.Thread(target=lambda: result_queue.put(("anemometer", read_anemometer_safe()))),
                threading.Thread(target=lambda: result_queue.put(("wind", read_wind_direction_safe()))),
                threading.Thread(target=lambda: result_queue.put(("rainfall", read_rainfall_safe()))),
                threading.Thread(target=lambda: result_queue.put(("sht31", read_sht31_safe()))),
                threading.Thread(target=lambda: result_queue.put(("water_temp_top", 
                    {"suhu_air_atas": read_water_temp_top_safe()}))),
                threading.Thread(target=lambda: result_queue.put(("water_temp_bottom", 
                    {"suhu_air_bawah": read_water_temp_bottom_safe()}))),
                threading.Thread(target=lambda: result_queue.put(("solar", 
                    {"solar": read_pyranometer_safe()}))),
                threading.Thread(target=lambda: result_queue.put(("pressure",
                    {"pressure": read_pressure_safe()})))
            ]
            
            for thread in threads:
                thread.daemon = True
                thread.start()

            # Wait maximum 0.9 seconds for sensor readings
            deadline = time.time() + 0.9
            for thread in threads:
                thread.join(timeout=max(0, deadline - time.time()))

            result = {}
            while not result_queue.empty():
                key, data = result_queue.get()
                result[key] = data

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

            # Calculate sleep time to maintain 1-second interval
            sleep_time = next_reading_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                next_reading_time = time.time() + 1.0

        except Exception as e:
            print(f"Critical error in main loop: {e}")
            next_reading_time = time.time() + 1.0

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