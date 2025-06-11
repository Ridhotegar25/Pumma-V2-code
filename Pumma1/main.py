#!/home/pi/code/envPumma/bin/python3

import time
import json
import os
import requests
import multiprocessing
from datetime import datetime
import paho.mqtt.client as mqtt
from alert import process_and_forecast, process_alert_log
from readWP import get_sensor_data

# MQTT Configuration
MQTT_BROKER = ""
MQTT_PORT = 1883
MQTT_TOPIC = "" # Topic Data Sensor yg sudah diolah dan Algoritma deteksi Tsunami 
MQTT_TOPIC2 = "" #Topic Data Raw Mentah Sensor 
MQTT_USERNAME = ""
MQTT_PASSWORD = ""

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "" # Ganti dengan Bot Token Yang sudah dibuat 
TELEGRAM_CHAT_ID = "-1002374272293"

# Log directory configuration
LOG_DIR = "/home/pi/Data/Pumma"
os.makedirs(LOG_DIR, exist_ok=True)

def get_log_filename():
    date_str = datetime.now().strftime("%d-%m-%Y")
    return os.path.join(LOG_DIR, f"Pumma_{date_str}.csv")

def write_to_file(data):
    filepath = get_log_filename()
    header = "TS,water_level_pressure,forecast_30,forecast_300,alert_signal,rms_alert_signal,threshold,alert_level,JSN_Distance\n"
    try:
        if not os.path.exists(filepath):
            with open(filepath, "w") as file:
                file.write(header)
        with open(filepath, "a") as file:
            row = f"{data['TS']},{data['Water_level_Pressure']},{data['For30']},{data['For300']},{data['Alert_Signal']},{data['rms']},{data['Threshold']},{data['Alert_Level']},{data['JSN_Distance']}\n"
            file.write(row)
    except Exception as e:
        print(f"Failed to write data to file: {e}")

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Telegram alert sent successfully")
        else:
            print(f"Failed to send Telegram alert: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")

def mqtt_publisher(queue):
    client = mqtt.Client()
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT)
            client.loop_start()
            print("Connected to MQTT broker")
            break
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}. Retrying in 5 seconds...")
            time.sleep(5)

    while True:
        try:
            item = queue.get()
            if item is None:
                break

            topic = item.get("topic")
            data = item.get("data")

            if topic and data:
                client.publish(topic, json.dumps(data), qos=1)
                print(f"Data sent to MQTT (Topic: {topic}): {data}")
        except Exception as e:
            print(f"Error in MQTT publishing: {e}")

    client.loop_stop()

# Fungsi Mengolah data
def data_processor(queue):
    while True:
        start_time = time.time()
        try:
            Water_level_pressure = get_sensor_data()
            forecast_30, forecast_300, alert_signal = process_and_forecast()
            rms_alert_signal, threshold, alert_level = process_alert_log()

            # Dekonstruksi data sensor
            MPa, kPa, Pa, water_level_pressure, bar, mbar, kg_cm2, psi, mH2O, mmH2O, celcius = Water_level_pressure

            data = {
                "TS": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Water_level_Pressure": water_level_pressure,
                "For30": forecast_30,
                "For300": forecast_300,
                "Alert_Signal": alert_signal,
                "rms": rms_alert_signal,
                "Threshold": threshold,
                "Alert_Level": alert_level
            }

            raw = {
                "TS": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Mpa": MPa,
                "Kpa": kPa,
                "Pa": Pa,
                "Bar": bar,
                "Mbar": mbar,
                "Kg_cm2": kg_cm2,
                "Psi": psi,
                "Mh2o": mH2O,
                "MmH2O": mmH2O,
                "Celcius": celcius
            }

            # Save data to logger
            write_to_file(data)

            # Send alert if necessary
            if alert_level > 0:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = (
                    f"⚠️ PUMMA SEBESI ⚠️ \n" #Ganti dengan Nama yang sesuai 
                    f"Timestamp: {timestamp}\n"
                    f"Alert Signal: {data['Alert_Signal']}\n"
                    f"RMS: {data['rms']}\n"
                    f"Threshold: {data['Threshold']}\n"
                    f"Alert Level: {data['Alert_Level']}"
                )
                send_telegram_alert(message)

            # Add data to queue for MQTT publishing
            queue.put({"topic": MQTT_TOPIC, "data": data})
            queue.put({"topic": MQTT_TOPIC2, "data": raw})

        except Exception as e:
            print(f"Error in data processing: {e}")

        elapsed_time = time.time() - start_time
        sleep_time = max(0, 1 - elapsed_time)
        time.sleep(sleep_time)

def main():
    queue = multiprocessing.Queue()

    producer_process = multiprocessing.Process(target=data_processor, args=(queue,))
    consumer_process = multiprocessing.Process(target=mqtt_publisher, args=(queue,))

    producer_process.start()
    consumer_process.start()

    try:
        producer_process.join()
        consumer_process.join()
    except KeyboardInterrupt:
        print("Program terminated.")
        queue.put(None)
        producer_process.terminate()
        consumer_process.terminate()

if __name__ == "__main__":
    main()
