import time
from smbus2 import SMBus

# Error codes
LPS28DFW_OK = 0
LPS28DFW_E_NOT_CONNECTED = -1
LPS28DFW_E_COM_FAIL = -2

# I2C addresses
LPS28DFW_I2C_ADDRESS_DEFAULT = 0x5C
LPS28DFW_I2C_ADDRESS_SECONDARY = 0x5D

# Sensor Constants
LPS28DFW_ID = 0xB4

# Operation modes and settings
LPS28DFW_ONE_SHOT = 0
LPS28DFW_10Hz = 3

class LPS28DFW:
    def __init__(self):
        #print("Initializing LPS28DFW...")
        self.i2c_address = LPS28DFW_I2C_ADDRESS_DEFAULT
        self.bus = None
        self.data = None
        self.mode_config = None

    def begin(self, address=LPS28DFW_I2C_ADDRESS_DEFAULT, bus_number=1):
        """Initialize the sensor with specified I2C address and bus number"""
        try:
            self.i2c_address = address
            self.bus = SMBus(bus_number)
            
            # Check if sensor is connected by reading WHO_AM_I register
            chip_id = self.read_register(0x0F)  # WHO_AM_I register address
            if chip_id != LPS28DFW_ID:
                return LPS28DFW_E_NOT_CONNECTED
            
            # Reset the sensor
            err = self.reset()
            if err != LPS28DFW_OK:
                return err
            
            # Initialize the sensor
            return self.init()
            
        except Exception as e:
            #print(f"Error initializing sensor: {e}")
            return LPS28DFW_E_COM_FAIL

    def init(self):
        """Initialize sensor with default settings"""
        try:
            # Enable BDU and IF_ADD_INC bits
            self.write_register(0x10, 0x02)  # CTRL_REG1 address
            return LPS28DFW_OK
        except Exception as e:
            #print(f"Error initializing sensor: {e}")
            return LPS28DFW_E_COM_FAIL

    def reset(self):
        """Reset the sensor"""
        try:
            # Set RESET bit
            self.write_register(0x11, 0x04)  # CTRL_REG2 address
            
            # Wait for reset to complete
            while True:
                status = self.get_status()
                if not status.get('sw_reset', True):
                    break
                time.sleep(0.01)
            
            return LPS28DFW_OK
        except Exception as e:
            #print(f"Error resetting sensor: {e}")
            return LPS28DFW_E_COM_FAIL

    def get_status(self):
        """Get sensor status"""
        try:
            status_reg = self.read_register(0x27)  # STATUS register
            return {
                'sw_reset': bool(status_reg & 0x04),
                'end_meas': bool(status_reg & 0x02),
                'data_ready': bool(status_reg & 0x01)
            }
        except Exception as e:
            #print(f"Error reading status: {e}")
            return {}

    def get_sensor_data(self):
        """Read pressure and temperature data from sensor"""
        try:
            # If in one-shot mode, trigger measurement
            if self.mode_config and self.mode_config.get('odr') == LPS28DFW_ONE_SHOT:
                self.write_register(0x11, 0x01)  # Trigger one-shot measurement
            
            # Wait for measurement to complete
            while True:
                status = self.get_status()
                if status.get('data_ready', False):
                    break
                time.sleep(0.001)
            
            # Read pressure (3 bytes) and temperature (2 bytes)
            press_xl = self.read_register(0x28)
            press_l = self.read_register(0x29)
            press_h = self.read_register(0x2A)
            temp_l = self.read_register(0x2B)
            temp_h = self.read_register(0x2C)
            
            # Debug: Print raw pressure bytes
            #print(f"Raw Pressure Bytes: {press_xl}, {press_l}, {press_h}")
            
            # Combine bytes into measurements
            pressure_raw = (press_h << 16) | (press_l << 8) | press_xl
            pressure = pressure_raw / 4096.0  # Convert to hPa (assuming 24-bit output)
            temperature_raw = (temp_h << 8) | temp_l
            temperature = temperature_raw / 100.0  # Convert to °C
            
            self.data = {
                'pressure': pressure,
                'temperature': temperature
            }
            
            return LPS28DFW_OK
        except Exception as e:
            #print(f"Error reading sensor data: {e}")
            return LPS28DFW_E_COM_FAIL

    def read_register(self, register_addr):
        """Read a single register"""
        try:
            return self.bus.read_byte_data(self.i2c_address, register_addr)
        except Exception as e:
            #print(f"Error reading register {register_addr}: {e}")
            return None

    def write_register(self, register_addr, data):
        """Write a single register"""
        try:
            self.bus.write_byte_data(self.i2c_address, register_addr, data)
            return True
        except Exception as e:
            #print(f"Error writing register {register_addr}: {e}")
            return False

    def set_mode_config(self, config):
        """Set sensor operation mode"""
        try:
            # Set ODR and mode in CTRL_REG1
            ctrl_reg1 = (config.get('odr', 0) << 3) | (config.get('avg', 0))
            self.write_register(0x10, ctrl_reg1)
            
            self.mode_config = config
            return LPS28DFW_OK
        except Exception as e:
            #print(f"Error setting mode config: {e}")
            return LPS28DFW_E_COM_FAIL
