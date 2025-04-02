#!/home/pi/code/envPumma/bin/python3

import serial
import json
import paho.mqtt.client as mqtt
import time
from datetime import datetime
import threading
from queue import Queue, Empty

# Konfigurasi Serial
SERIAL_PORT = '/dev/Nano'
BAUD_RATE = 115200
MAX_RETRIES = 5

# Konfigurasi MQTT
MQTT_BROKER = "vps.isi-net.org"
MQTT_PORT = 1883
MQTT_TOPIC = "Pumma/Sebesi_serial"
MQTT_USER = "unila"
MQTT_PASSWORD = "pwdMQTT@123"

# Global variables
ser = None
client = None
data_queue = Queue()
event_stop = threading.Event()


def init_serial():
    """Inisialisasi koneksi serial."""
    global ser
    retries = MAX_RETRIES
    while retries:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print("Serial connected")
            return ser
        except serial.SerialException:
            print("Failed to connect to serial, retrying...")
            retries -= 1
            time.sleep(5)
    print("Serial connection failed after retries. Exiting...")
    return None


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
        except Exception as e:
            print(f"Reconnection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)


def mqtt_loop():
    """Loop untuk koneksi MQTT."""
    global client
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()


def save_log(ts_current, ts_human, maxbotic1):
    """Simpan hanya data tertentu ke file log."""
    date_str = datetime.now().strftime("%d-%m-%Y")
    file_path = f"/home/pi/Data/Log_maxbo/Log_MB{date_str}.txt"
    try:
        with open(file_path, "a") as file:
            file.write(f"{ts_current},{ts_human},{maxbotic1}\n")
        print(f"Logged data: {ts_current}, {ts_human}, {maxbotic1}")
    except IOError as e:
        print(f"Error writing to log file: {e}")


def process_data(data):
    """Proses data yang diterima dari serial."""
    try:
        ts_nano = data.get("TS_Nano", 0)
        maxbotic_1 = float(data.get("Maxbotic1", 0.0))
        maxbotic1 = round(4.23 - (maxbotic_1 / 100), 2)

        ts_human = datetime.utcfromtimestamp(ts_nano).strftime('%Y-%m-%d %H:%M:%S')
        ts_current = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        new_data = {
            "TS": ts_current,
            "TS_Nano": ts_human,
            "maxbotic1": maxbotic1,
        }

        # Masukkan data ke queue untuk dikirim atau disimpan
        data_queue.put(new_data)
        print(f"Data processed: {new_data}")

    except (ValueError, TypeError, KeyError) as e:
        print(f"Error processing data: {e}")


def handle_data_queue():
    """Kirim data dari queue ke MQTT atau simpan ke log jika gagal."""
    global client
    while not event_stop.is_set():
        try:
            # Coba ambil data dari queue dengan timeout untuk menghindari blocking.
            data = data_queue.get(timeout=1)

            # Validasi data yang diambil dari queue.
            if not isinstance(data, dict) or "TS" not in data or "TS_Nano" not in data or "maxbotic1" not in data:
                print("Invalid data format in queue:", data)
                continue

            # Publikasi data ke MQTT.
            result = client.publish(MQTT_TOPIC, json.dumps(data), qos=0)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                print("Failed to send data to MQTT, saving to log...")
                save_log(data["TS"], data["TS_Nano"], data["maxbotic1"])
            else:
                print("Data sent to MQTT:", data)

        except Empty:
            # Tidak ada data di queue; lanjutkan loop tanpa error.
            continue

        except Exception as e:
            print(f"Error handling data queue: {e}")
            time.sleep(1)  # Hindari loop terlalu cepat pada error.


def read_serial():
    """Baca data dari serial."""
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
                elif len(buffer) > 500:
                    print("Buffer too long, resetting...")
                    buffer = ""
        except serial.SerialException:
            print("Serial read error. Reinitializing connection...")
            ser.close()
            ser = init_serial()
        time.sleep(0.01)


if __name__ == "__main__":
    ser = init_serial()
    if ser:
        mqtt_thread = threading.Thread(target=mqtt_loop, daemon=True)
        serial_thread = threading.Thread(target=read_serial, daemon=True)
        queue_thread = threading.Thread(target=handle_data_queue, daemon=True)

        mqtt_thread.start()
        serial_thread.start()
        queue_thread.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Program interrupted. Exiting...")
            event_stop.set()
            if ser:
                ser.close()
            if client:
                client.disconnect()
    else:
        print("Failed to initialize serial connection. Exiting...")
