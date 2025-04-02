#!/home/pi/code/envPumma/bin/python3

import minimalmodbus  
import time  

# Konfigurasi komunikasi Modbus RTU  
try:  
    sensor = minimalmodbus.Instrument('/dev/Wind_Direct', 2)  # Port serial dan address slave  
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

# Tabel arah angin berdasarkan nilai register 0x0001  
def get_direction_from_value(direction):  
    directions = [  
        "Utara", "Utara Timur Laut", "Timur Laut", "Timur Timur Laut",
        "Timur", "Timur Tenggara", "Tenggara", "Selatan", 
        "Selatan Barat Daya", "Barat Daya", "Barat Barat Daya", "Barat", 
        "Barat Barat Laut", "Barat Laut", "Utara Barat Laut", "Utara"
    ]  
    if 0 <= direction < len(directions):  
        return directions[direction]  
    else:  
        return "Invalid direction"  

# Fungsi membaca data sensor  
def read_sensor_data():  
    if not port_found:  
        print("Port tidak ditemukan, nilai diset menjadi None.")  
        return {"angle": None, "direction": "None"}  

    try:  
        # Membaca register sudut angin (0x0000)  
        angle_raw = sensor.read_register(0, functioncode=3)  # INT16  
        angle = angle_raw / 10  # Konversi ke derajat  

        # Membaca register arah angin (0x0001)  
        direction_raw = sensor.read_register(1, functioncode=3)  # INT16  
        direction_value = direction_raw & 0x0F  # Ambil hanya 4 bit terakhir  

        # Debug: Cetak nilai mentah dari register  
#        print(f"Raw register values -> angle: {angle_raw}, direction: {direction_raw} (masked: {direction_value})")  

        direction = get_direction_from_value(direction_value)  

        return {"angle": angle, "direction": direction}  

    except Exception as e:  
        print(f"Kesalahan membaca sensor: {e}")  
        return {"angle": None, "direction": "None"}  

# Loop pembacaan data setiap 1 detik  
if __name__ == "__main__":  
    while True:  
        sensor_data = read_sensor_data()  
        if sensor_data:  
            print(sensor_data)  
        else:  
            print("Gagal membaca data sensor.")  
        time.sleep(1)  # Delay 1 detik
