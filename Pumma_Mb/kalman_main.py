#!/home/pi/code/envPumma/bin/python3

import json
import os
import time
from datetime import datetime
import paho.mqtt.client as mqtt

from alert import process_and_forecast, process_alert_log
from kalman_mb import connect_serial, read_sensor_once, save_sensor_data, KalmanFilter1D
# from jsnA import measure_distance  # Uncomment jika ingin pakai sensor JSN

# === MQTT Configuration ===
MQTT_BROKER = "c-greenproject.org"
MQTT_PORT = 1883
MQTT_TOPIC = "Pumma/Sebesi_Maxbotic"
MQTT_USERNAME = "unila"
MQTT_PASSWORD = "pwdMQTT@123"

# === Path penyimpanan data ===
DATA_LOGGER_PATH = "/home/pi/Data/Pumma_MB"
LOG_FOLDER = "/home/pi/Data/Log_maxbo"
os.makedirs(DATA_LOGGER_PATH, exist_ok=True)

# === Setup MQTT ===
client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

# === Fungsi pembacaan Maxbotic ===
def get_maxbo_value(ser, kalman_filter):
    result = read_sensor_once(ser, kalman_filter)
    if result:
        save_sensor_data(LOG_FOLDER, result["timestamp"], result["value"])
        return result
    return None

# === Fungsi simpan ke logger CSV ===
def write_to_logger(data_dict):
    now = datetime.now()
    filename = f"Pumma_{now.strftime('%d-%m-%Y')}.csv"
    file_path = os.path.join(DATA_LOGGER_PATH, filename)
    header = [
        "timestamp", "maxbo_value", "forecast_30", "forecast_300",
        "alert_signal", "rms_alert_signal", "threshold", "alert_level"
    ]
    is_new = not os.path.exists(file_path)

    with open(file_path, "a") as f:
        if is_new:
            f.write(",".join(header) + "\n")
        f.write(",".join([str(data_dict.get(h, "")) for h in header]) + "\n")

# === Main Loop ===
def main_loop():
    ser = connect_serial()
    kalman_filter = KalmanFilter1D()

    if not ser:
        print("Tidak bisa konek ke sensor. Keluar.")
        return

    while True:
        try:
            maxbo_data = get_maxbo_value(ser, kalman_filter)
            if maxbo_data is None:
                print("Gagal ambil data sensor.")
                time.sleep(1)
                continue

            # Jika ingin aktifkan sensor JSN, aktifkan kode berikut:
            # jsn_distance0 = measure_distance()
            # jsn_distance1 = 2.198 - jsn_distance0 / 100
            # jsn_distance = round((1 + jsn_distance1), 2)

            forecast_30, forecast_300, alert_signal = process_and_forecast()
            rms_alert_signal, threshold, alert_level = process_alert_log()

            payload = {
                "timestamp": maxbo_data["timestamp"],
                "Maxbotic": maxbo_data["value"],
                # "JSN_Data": jsn_distance,
                "forecast_30": forecast_30,
                "forecast_300": forecast_300,
                "alert_signal": alert_signal,
                "rms_alert_signal": rms_alert_signal,
                "threshold": threshold,
                "alert_level": alert_level
            }

            # Kirim data ke MQTT
            client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)

            # Simpan ke CSV logger
            write_to_logger(payload)

            print(f"Sent and logged: {payload}")

        except Exception as e:
            print("Main loop error:", e)

        time.sleep(1)

if __name__ == "__main__":
    main_loop()
