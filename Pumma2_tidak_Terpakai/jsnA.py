#!/home/pi/code/envPumma/bin/python3

import RPi.GPIO as GPIO
import time

# Konfigurasi GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pin untuk TRIG dan ECHO
TRIG = 24
ECHO = 23

# Setup TRIG dan ECHO
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def measure_distance():
    """
    Mengukur jarak menggunakan sensor ultrasonik SR04M.
    """
    # Pastikan TRIG rendah terlebih dahulu
    GPIO.output(TRIG, False)
    time.sleep(0.5)

    # Kirim sinyal TRIG
    GPIO.output(TRIG, True)
    time.sleep(0.00001)  # Pulsa 10µs
    GPIO.output(TRIG, False)

    # Tunggu hingga ECHO naik
    pulse_start = time.time()
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()

    # Tunggu hingga ECHO turun
    pulse_end = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    # Hitung durasi pulsa
    pulse_duration = pulse_end - pulse_start

    # Hitung jarak (kecepatan suara 34300 cm/s)
    distance = pulse_duration * 17150
    distance = round(distance, 2)

    # Validasi jarak
    if distance > 8000 or distance < 2:  # Sensor SR04 memiliki jangkauan 2-400 cm
        return None

    return distance

try:
    while True:
        distance = measure_distance()
        if distance is not None:
            print(f"JSN_1: {distance} cm")
        else:
            print("Jarak di luar jangkauan sensor.")
        time.sleep(0.9)  # Delay 1 detik antar pembacaan
except KeyboardInterrupt:
    print("\nProgram dihentikan oleh pengguna.")
finally:
    GPIO.cleanup()
    print("GPIO dibersihkan.")

