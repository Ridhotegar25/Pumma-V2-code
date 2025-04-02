#!/home/pi/code/envPumma/bin/python3
import minimalmodbus
import time

# Konfigurasi komunikasi Modbus RTU
sensor = minimalmodbus.Instrument('/dev/MPPT', 1)  # Port serial dan address slave
sensor.serial.baudrate = 115200  # Baudrate
sensor.serial.bytesize = 8  # Ukuran byte
sensor.serial.parity = minimalmodbus.serial.PARITY_NONE  # Paritas
sensor.serial.stopbits = 1  # Stop bit
sensor.serial.timeout = 1  # Timeout komunikasi

# Fungsi untuk membaca data dari register
def read_sensor_data():
    try:
        # Membaca 9 register mulai dari address 0x0002
        data = sensor.read_registers(0x3100,11, functioncode=4)  # Address 2, quantity 9
        return data  # Mengembalikan data sebagai array
    except Exception as e:
        print(f"Kesalahan membaca sensor: {e}")
        return []  # Jika ada error, kembalikan array kosong

# Loop pembacaan data setiap 5 detik
if __name__ == "__main__":
    while True:
        sensor_data = read_sensor_data()
        if sensor_data:
            print(sensor_data)
        else:
            print("Gagal membaca data sensor.")
        time.sleep(120)  # Delay 5 detik
