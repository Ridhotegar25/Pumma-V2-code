#!/home/pi/code/envPumma/bin/python3

import os
import numpy as np
import logging
from datetime import datetime, timedelta
from collections import deque

import time

# Konfigurasi logging
LOG_FILE = "/home/pi/Data/error_log.txt"
logging.basicConfig(filename=LOG_FILE, level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

# Direktori untuk file log
LOG_DIR = "/home/pi/Data/Log_maxbo"
ALERT_LOG_DIR = "/home/pi/Data/maxbo_LogAlert"
os.makedirs(ALERT_LOG_DIR, exist_ok=True)  # Pastikan folder log alert ada

def get_log_filename():
    return os.path.join(LOG_DIR, f"Log_MB{datetime.now().strftime('%d-%m-%Y')}.txt")

def get_alert_log_filename():
    return os.path.join(ALERT_LOG_DIR, f"Log_AS{datetime.now().strftime('%d-%m-%Y')}.txt")

def read_log_file(filepath, max_lines=300):
    if not os.path.exists(filepath):
        logging.warning(f"File log tidak ditemukan: {filepath}")
        return deque(maxlen=max_lines)

    data = deque(maxlen=max_lines)
    try:
        with open(filepath, "r") as file:
            lines = file.readlines()[-max_lines:]

        for line in lines:
            try:
                parts = line.strip().split(",")
                if len(parts) < 3:
                    continue  # Lewati jika tidak ada cukup kolom
                dt_str = parts[0].strip()
                value_str = parts[2].strip()  # Ambil data ke-3 (indeks ke-2)
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                value = float(value_str)
                data.append((dt, value))
            except ValueError:
                continue
    except Exception as e:
        logging.error(f"Error membaca file log {filepath}: {e}")

    return data

def polynomial_forecast(data):
    if len(data) < 3:
        return 1.62

    x = np.arange(len(data))
    y = np.array(data, dtype=np.float64)

    try:
        coeffs = np.polyfit(x, y, 2)
        return round(np.polyval(coeffs, len(data)), 3)
    except Exception as e:
        logging.error(f"Error dalam forecasting: {e}")
        return 1.62

def log_alert_signal(alert_signal):
    try:
        with open(get_alert_log_filename(), "a", buffering=1) as log_file:
            log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, {alert_signal}\n")
    except Exception as e:
        logging.error(f"Error menulis log alert: {e}")

def process_and_forecast():
    filepath = get_log_filename()
    data = read_log_file(filepath, max_lines=300)

    if not data:
        return 1.62, 1.62, 1.62

    now = datetime.now()
    last_15_minutes = now - timedelta(minutes=15)
    last_1_hour = now - timedelta(hours=2)

    recent_30_data = [v for d, v in data if d >= last_15_minutes][-30:]
    recent_300_data = [v for d, v in data if d >= last_1_hour][-300:]

    forecast_30 = polynomial_forecast(recent_30_data) if len(recent_30_data) >= 3 else 1.62
    forecast_300 = polynomial_forecast(recent_300_data) if len(recent_300_data) >= 3 else 1.62

    alert_signal = round(abs(forecast_30 - forecast_300), 3)

    log_alert_signal(alert_signal)

    return forecast_30, forecast_300, alert_signal

def calculate_rms(data):
    if not data:
        return 1.62
    return round(np.sqrt(np.mean(np.square(np.array(data, dtype=np.float64)))), 3)

def process_alert_log():
    alert_log_filepath = get_alert_log_filename()
    if not os.path.exists(alert_log_filepath):
        return 1.62, 1.62, 1.62

    alert_data = deque(maxlen=90)
    now = datetime.now()
    last_1_hour = now - timedelta(hours=1)

    try:
        with open(alert_log_filepath, "r") as file:
            lines = file.readlines()[-90:]

        for line in lines:
            try:
                dt_str, value_str = line.strip().split(",")
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                value = float(value_str)
                if dt >= last_1_hour:
                    alert_data.append(value)
            except ValueError:
                continue
    except Exception as e:
        logging.error(f"Error membaca log alert: {e}")
        return 1.62, 1.62, 1.62

    if not alert_data:
        return 1.62, 1.62, 1.62

    rms_alert_signal = calculate_rms(alert_data)
    threshold = round(rms_alert_signal * 2 + 0.1, 3)

    # Perhitungan alert level sesuai logika awal
    alert_level = 0
    for alert_signal in alert_data:
        if threshold is not None and alert_signal > threshold and alert_signal > 0.4:
            if alert_level < 10:
                alert_level += 1
        else:
            alert_level -= 1
        alert_level = max(alert_level, 0)

    return rms_alert_signal, threshold, alert_level

if __name__ == "__main__":
    start_time = time.perf_counter()
    forecast_30, forecast_300, alert_signal = process_and_forecast()
    rms_alert_signal, threshold, alert_level = process_alert_log()

    end_time = time.perf_counter()

    execution_time = end_time - start_time
    print(f"Execution Time: {execution_time:.6f} seconds")

    print(f"Forecast 30: {forecast_30}")
    print(f"Forecast 300: {forecast_300}")
    print(f"Alert Signal: {alert_signal}")
    print(f"RMS Alert Signal: {rms_alert_signal}")
    print(f"Threshold: {threshold}")
    print(f"Alert Level: {alert_level}")
