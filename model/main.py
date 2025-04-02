#!/home/pi/code/envPumma/bin/python3

import os
import json
import datetime
import time
import paho.mqtt.client as mqtt
from jsnA import measure_distance
from model import read_last_n_lines, read_last_line

# Konfigurasi MQTT
MQTT_BROKER = ""
MQTT_PORT = 1883
MQTT_TOPIC = ""
MQTT_USERNAME = ""
MQTT_PASSWORD = ""

def send_mqtt(client, payload):
    client.publish(MQTT_TOPIC, json.dumps(payload))
    print("Data dikirim ke MQTT:", payload)

def save_to_csv(file_path, data):
    file_exists = os.path.isfile(file_path)
    
    with open(file_path, 'a') as file:
        if not file_exists:
            file.write("TS,WP,MB_Original,MB_Adjusted,JSN_Adjustment,JSN_Distance\n")
        file.write(f"{data['TS']},{data['WP']},{data['MB_Original']},{data['MB_Adjusted']},{data['JSN_Ori']},{data['JSN_Adjustment']}\n")

def main():
    today = datetime.datetime.now().strftime('%d-%m-%Y')
    wp_file = f"/home/pi/Data/LogSeaWater/Log_WP {today}.txt"
    mb_file = f"/home/pi/Data/Log_maxbo/Log_MB{today}.txt"
    csv_file = f"/home/pi/Data/Adjusment/Data_{today}.csv"
    
    client = mqtt.Client()
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    
    while True:
        wp_data = read_last_n_lines(wp_file, 2)
        mb_data = read_last_line(mb_file)
        jsn_distance0 = measure_distance()
        jsn_distance1 = 2.198 - jsn_distance0/100
        jsn_distance = round((1 + jsn_distance1),2)

        if not wp_data or not mb_data:
            print("Data tidak ditemukan atau file kosong.")
        else:
            wp_values = [float(entry[1]) for entry in wp_data if len(entry) >= 2]
            wp_value = wp_values[-1] if wp_values else None

            mb_original_value = float(mb_data[1]) if len(mb_data) >= 1 else None

            total = 7.20
            total2 = 7.20
            adjustment = round(total - (mb_original_value + wp_value), 3) if wp_value is not None and mb_original_value is not None else 0
            mb_adjusted_value1 = mb_original_value + adjustment if mb_original_value is not None else None
            mb_adjusted_value = round(mb_adjusted_value1,3)

            adjustment2 = round(total2 - (jsn_distance + wp_value), 3) if jsn_distance is not None and wp_value is not None else 0
            jsn_adjusment1 = jsn_distance + adjustment2 if jsn_distance is not None else None
            jsn_adjusment = round(jsn_adjusment1,3)
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            payload = {
                "TS": timestamp,
                "WP": wp_value,
                "MB_Original": mb_original_value,
                "MB_Adjusted": mb_adjusted_value,
                "MB_Koreksi" : adjustment,
                "JSN_Ori": jsn_distance,
                "JSN_Adjustment": jsn_adjusment,
                "JSN_Koreksi" : adjustment2
            }

            save_to_csv(csv_file, payload)
            send_mqtt(client, payload)
        
        time.sleep(1)

if __name__ == "__main__":
    main()
