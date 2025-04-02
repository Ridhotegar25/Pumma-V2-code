#!/home/pi/code/envPumma/bin/python3

import requests
import time
import base64
import paho.mqtt.client as mqtt
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from requests.auth import HTTPDigestAuth
import os
import json
import logging

# Konfigurasi Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# Konfigurasi kamera IP Hikvision
CAMERA_IP = "-"  # Ganti dengan alamat IP kamera
USERNAME = "-"           # Ganti dengan username kamera
PASSWORD = "-"        # Ganti dengan password kamera
SNAPSHOT_URL = f"http://{CAMERA_IP}/ISAPI/Streaming/channels/1/picture"

# Folder untuk menyimpan gambar
SAVE_FOLDER = "/home/pi/Data/snapshots"

# Interval dalam detik (2 menit = 120 detik)
INTERVAL = 120

# Path ke file logo
LOGO_PATHS = [
    "/home/pi/code/capture/logo_brin.png",
    "/home/pi/code/capture/logo_krc.png",
    "/home/pi/code/capture/logo_dronila.png",
    "/home/pi/code/capture/Logo_bmkg.png"
]  # Ganti dengan path file logo Anda
LOGO_SIZE = (50, 50)  # Ukuran logo dalam piksel
LOGO_SPACING = 20     # Jarak antar logo dalam piksel

# Konfigurasi MQTT
MQTT_BROKER = "-"  # Ganti dengan alamat broker MQTT
MQTT_PORT = 1883                  # Ganti dengan port broker MQTT jika berbeda
MQTT_TOPIC = ""  # Ganti dengan topik MQTT
MQTT_USERNAME = ""       # Ganti dengan username MQTT jika diperlukan
MQTT_PASSWORD = ""    

def add_overlay(image_path):
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

        # Tambahkan teks datetime di pojok kanan bawah
        timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        text = f"PUMMA Sebesi: {timestamp} (UTC+7)"

        # Hitung posisi teks menggunakan textbbox
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x_text = img.width - text_width - 10
        y_text = img.height - text_height - 10

        draw.text((x_text, y_text), text, fill="red", font=font)

        # Tambahkan logo di pojok kanan atas secara berjajar
        x_logo_start = img.width - (LOGO_SIZE[0] * len(LOGO_PATHS)) - (LOGO_SPACING * (len(LOGO_PATHS) - 1)) - 10
        y_logo = 10

        for i, logo_path in enumerate(LOGO_PATHS):
            logo = Image.open(logo_path).resize(LOGO_SIZE)
            x_logo = x_logo_start + i * (LOGO_SIZE[0] + LOGO_SPACING)
            img.paste(logo, (x_logo, y_logo), logo.convert("RGBA"))

        img.save(image_path)
        logging.info(f"Overlay berhasil ditambahkan pada: {image_path}")
    except Exception as e:
        logging.error(f"Kesalahan saat menambahkan overlay: {e}")

def image_to_base64(image_path):
    try:
        with open(image_path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode("utf-8")
            return encoded
    except Exception as e:
        logging.error(f"Kesalahan saat mengubah gambar ke Base64: {e}")
        return None

def send_to_mqtt(base64_data):
    try:
        client = mqtt.Client(protocol=mqtt.MQTTv311)
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)

        payload = base64_data

        client.loop_start()
        result = client.publish(MQTT_TOPIC, payload, qos=1)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logging.info("Data berhasil dikirim ke MQTT.")
        else:
            logging.error(f"Gagal mengirim data ke MQTT. Kode error: {result.rc}")

        client.loop_stop()
        client.disconnect()
    except Exception as e:
        logging.error(f"Kesalahan saat mengirim data ke MQTT: {e}")

def capture_image():
    try:
        response = requests.get(SNAPSHOT_URL, auth=HTTPDigestAuth(USERNAME, PASSWORD), stream=True)
        if response.status_code == 200:
            timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
            file_path = f"{SAVE_FOLDER}/snapshot_{timestamp}.jpg"
            with open(file_path, 'wb') as file:
                file.write(response.content)
            logging.info(f"Gambar berhasil disimpan: {file_path}")

            add_overlay(file_path)
            base64_data = image_to_base64(file_path)
            if base64_data:
                send_to_mqtt(base64_data)
        else:
            logging.error(f"Gagal mengambil gambar. Kode status: {response.status_code}. Pesan: {response.text}")
    except Exception as e:
        logging.error(f"Kesalahan saat mengambil gambar: {e}")

if __name__ == "__main__":
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    logging.info("Memulai pengambilan gambar...")
    while True:
        capture_image()
        time.sleep(INTERVAL)
