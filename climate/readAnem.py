#!/home/pi/code/envPumma/bin/python3

import minimalmodbus  
import time  
  
# Konfigurasi komunikasi Modbus RTU  
try:  
    sensor = minimalmodbus.Instrument('/dev/Wind_Speed', 2)  # Port serial dan address slave  
    sensor.serial.baudrate = 9600  # Baudrate  
    sensor.serial.bytesize = 8  # Ukuran byte  
    sensor.serial.parity = minimalmodbus.serial.PARITY_NONE  # Paritas  
    sensor.serial.stopbits = 1  # Stop bit  
    sensor.serial.timeout = 1  # Timeout komunikasi  
    port_found = True  
except IOError as e:  
    print(f"Port tidak ditemukan: {e}")  
    sensor = None  
    port_found = False  
  
# Fungsi untuk membaca data dari register  
def read_sensor_data():  
#    if not port_found:  
#        print("Port tidak ditemukan, nilai diset menjadi None.")  
#        return {  
#            "anemometer_speed": None,  
#            "beaufort_scale": None,  
#        }  
    try:  
        # Membaca register  
        data = sensor.read_registers(0, 2, functioncode=3)  # Address 0, quantity 2  
        labeled_data = {  
            "anemometer_speed": data[0]/10 if len(data) > 0 else None,  
            "beaufort_scale": data[1] if len(data) > 1 else None,  
        }  
        return labeled_data  
    except Exception as e:  
        print(f"Kesalahan membaca sensor: {e}")  
#        return {  
#            "anemometer_speed": None,  
#            "beaufort_scale": None,  
#        }  # Jika ada error, kembalikan dictionary dengan None  
  
# Loop pembacaan data setiap 1 detik  
if __name__ == "__main__":  
    while True:  
        sensor_data = read_sensor_data()  
        if sensor_data:  
            print(sensor_data)  
        else:  
            print("Gagal membaca data sensor.")  
        time.sleep(1)  # Delay 1 detik  
