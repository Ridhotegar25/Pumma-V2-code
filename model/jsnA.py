#!/home/pi/code/envPumma/bin/python3

import RPi.GPIO as GPIO
import time

# Konfigurasi GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pin untuk TRIG dan ECHO
TRIG = 27
ECHO = 17

# Setup TRIG dan ECHO
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def measure_distance():
    """
    Mengukur jarak menggunakan sensor ultrasonik JSN-SR04M.
    """
    # Pastikan TRIG rendah terlebih dahulu
    GPIO.output(TRIG, False)
    time.sleep(0.05)  # Beri waktu stabilisasi

    # Kirim sinyal TRIG
    GPIO.output(TRIG, True)
    time.sleep(0.00001)  # Pulsa 10Âµs
    GPIO.output(TRIG, False)

    # Tunggu hingga ECHO naik dengan timeout
    timeout_start = time.time()
    while GPIO.input(ECHO) == 0:
        if time.time() - timeout_start > 0.02:  # Timeout 20ms
            return None

    pulse_start = time.time()
    
    # Tunggu hingga ECHO turun dengan timeout
    timeout_start = time.time()
    while GPIO.input(ECHO) == 1:
        if time.time() - timeout_start > 0.02:  # Timeout 20ms
            return None
    
    pulse_end = time.time()

    # Hitung durasi pulsa
    pulse_duration = pulse_end - pulse_start

    # Hitung jarak (kecepatan suara 34300 cm/s)
    distance = pulse_duration * 17150
    distance = round(distance, 2)

    # Validasi jarak
    if distance > 400 or distance < 2:  # Sensor SR04M memiliki jangkauan 2-400 cm
        return None

    return distance

if __name__ == "__main__":
    try:
        while True:
            distance1 = measure_distance()
            distance = round(distance1/100,2)
            if distance is not None:
                print(f"JSN_2: {distance} m")
            else:
                print("Jarak di luar jangkauan sensor atau timeout.")
            time.sleep(0.9)  # Delay 1 detik antar pembacaan
    except KeyboardInterrupt:
        print("\nProgram dihentikan oleh pengguna.")
    finally:
        GPIO.cleanup()
        print("GPIO dibersihkan.")
