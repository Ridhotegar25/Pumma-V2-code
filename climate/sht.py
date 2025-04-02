import smbus2
import time

bus = smbus2.SMBus(1)  # Gunakan I2C bus 1
addr = 0x44            # Alamat sensor

try:
    print("Mengirim perintah reset ke sensor...")
    bus.write_byte_data(addr, 0x30, 0xA2)  # Perintah Soft Reset
    time.sleep(0.5)
    print("Membaca status sensor...")
    data = bus.read_i2c_block_data(addr, 0xF3, 3)  # Coba baca status register
    print("Data dari sensor:", data)
except OSError as e:
    print("I2C Error:", e)
