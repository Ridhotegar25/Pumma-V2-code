import minimalmodbus

# Konfigurasi ulang perangkat
PORT = "/dev/Pyrano"  # Sesuaikan dengan port yang digunakan
SLAVE_ADDRESS = 0x05  # Alamat default perangkat
BAUDRATE_NEW = 4800

# Register address untuk membaca nilai radiasi matahari
SOLAR_RADIATION_REGISTER = 0x0000

# Inisialisasi komunikasi Modbus dengan baud rate baru
instrument = minimalmodbus.Instrument(PORT, SLAVE_ADDRESS)
instrument.serial.baudrate = BAUDRATE_NEW
instrument.serial.bytesize = 8
instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
instrument.serial.stopbits = 1
instrument.serial.timeout = 1

# Membaca data dari sensor
try:
    print(f"Membaca data dari sensor dengan baud rate {BAUDRATE_NEW}...")
    solar_radiation = instrument.read_register(SOLAR_RADIATION_REGISTER, functioncode=3)
    print(f"Nilai radiasi matahari: {solar_radiation} W/m2")
except Exception as e:
    print(f"Terjadi kesalahan saat membaca data: {e}")

