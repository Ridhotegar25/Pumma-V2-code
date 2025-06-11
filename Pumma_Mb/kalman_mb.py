#!/home/pi/code/envPumma/bin/python3

import serial
import os
from datetime import datetime

# === Konfigurasi serial port ===
port = '/dev/Nano'
BAUDRATE = 9600

# === Kalman Filter 1D untuk meredam noise ombak besar ===
class KalmanFilter1D:
    def __init__(self, process_variance=1e-4, measurement_variance=0.05**2, initial_estimate=1.0):
        self.Q = process_variance          # Dunia nyata berubah lambat
        self.R = measurement_variance      # Sensor penuh noise (ombak)
        self.x = initial_estimate          # Estimasi awal
        self.P = 1.0                       # Ketidakpastian awal

    def update(self, measurement):
        self.P += self.Q
        K = self.P / (self.P + self.R)
        self.x += K * (measurement - self.x)
        self.P = (1 - K) * self.P
        return round(self.x, 2)

# === Fungsi koneksi ke serial ===
def connect_serial():
    try:
        ser = serial.Serial(port, BAUDRATE, timeout=1)
        ser.flush()
        return ser
    except serial.SerialException as e:
        print("Gagal konek ke serial:", e)
        return None

# === Fungsi membaca sensor dan menerapkan Kalman Filter ===
def read_sensor_once(ser, kalman_filter):
    try:
        ser.flushInput()
        line = ser.readline().decode('utf-8').strip().rstrip(',')
        if not line:
            return None
        try:
            data_measur_real = round(float(line) / 100, 2)
            data_measure = round(2.198 - data_measur_real, 2)
            raw_data = round(1 + data_measure, 2)

            # Terapkan Kalman Filter
            filtered_value = kalman_filter.update(raw_data)

            return {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "value": filtered_value
            }
        except ValueError:
            print(f"Data tidak valid: {line}")
            return None
    except Exception as e:
        print("Error membaca data sensor:", e)
        return None

# === Simpan data sensor ke log file ===
def save_sensor_data(log_folder, timestamp, value):
    os.makedirs(log_folder, exist_ok=True)
    filename = f"Log_MB{datetime.now().strftime('%d-%m-%Y')}.txt"
    path = os.path.join(log_folder, filename)
    with open(path, 'a') as f:
        f.write(f"{timestamp} ,{value}\n")

# === Contoh penggunaan utama ===
if __name__ == "__main__":
    ser = connect_serial()
    kalman_filter = KalmanFilter1D()

    if ser:
        while True:
            data = read_sensor_once(ser, kalman_filter)
            if data:
                print(f"{data['timestamp']} | Filtered: {data['value']} m")
                save_sensor_data("/home/pi/logging/MB", data["timestamp"], data["value"])
