#!/home/pi/code/envPumma/bin/python3
import paho.mqtt.client as mqtt
import os

# Fungsi callback saat berhasil terhubung ke broker MQTT
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker!")
        client.subscribe("Sebesi_reboot")  # Berlangganan ke topik Sebesi_ssh
    else:
        print(f"Failed to connect, return code {rc}")

# Fungsi callback saat pesan diterima
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        print(f"Message received: {payload} on topic {msg.topic}")

        # Jika pesan adalah '1', restart layanan ssh
        if payload == "1":
            print("Restarting reboot...")
            result = os.system("sudo reboot")
            if result == 0:
                print("reboot successfully.")
                client.publish("Sebesi_ssh_response", "success_reboot")  # Kirim pesan sukses ke broker
            else:
                print("Failed to restart SSH service.")
                client.publish("Sebesi_ssh_response", "failure")  # Kirim pesan gagal ke broker
    except Exception as e:
        print(f"Error processing message: {e}")

# Konfigurasi MQTT broker
MQTT_BROKER = ""  # Ganti dengan alamat broker MQTT Anda
MQTT_PORT = 1883                # Port default MQTT
MQTT_USERNAME = ""  # Ganti dengan username broker MQTT Anda
MQTT_PASSWORD = ""  # Ganti dengan password broker MQTT Anda

# Inisialisasi client MQTT
client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)  # Tambahkan autentikasi username dan password
client.on_connect = on_connect
client.on_message = on_message

try:
    # Hubungkan ke broker MQTT
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # Mulai loop untuk mendengarkan pesan
    client.loop_forever()
except KeyboardInterrupt:
    print("Exiting...")
except Exception as e:
    print(f"Error: {e}")
