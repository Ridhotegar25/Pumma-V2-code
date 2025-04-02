#!/home/pi/code/envPumma/bin/python3

import serial
import smbus
import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu
import time
import numpy as np


class DFRobot_RainfallSensor(object):
  ## SEN0575 stores the address of the input register for PID in memory.
  SEN0575_INPUT_REG_PID                          = 0x0000
  ## The address of the input register for VID in memory.
  SEN0575_INPUT_REG_VID                          = 0x0001
  ## The address of the input register for device address in memory.
  SEN0575_INPUT_REG_ADDR                         = 0x0002
  ## The address of the input register for device baudrate in memory.
  SEN0575_INPUT_REG_BAUD                         = 0x0003
  ## The address of the input register for RS485 parity bit and stop bit in memory.
  SEN0575_INPUT_REG_VERIFYANDSTOP                = 0x0004
  ## The address of the input register for firmware version in memory.
  SEN0575_INPUT_REG_VERSION                      = 0x0005
  
  ## The address of the input register for low 16-bit cumulative rainfall in set time.
  SEN0575_INPUT_REG_TIME_RAIN_FALL_L             = 0x0006
  ## The address of the input register for high 16-bit cumulative rainfall in set time.
  SEN0575_INPUT_REG_TIME_RAIN_FALL_H             = 0x0007
  ## The address of the input register for low 16-bit cumulative rainfall since working started.
  SEN0575_INPUT_REG_CUMULATIVE_RAINFALL_L        = 0x0008  
  ## The address of the input register for high 16-bit cumulative rainfall since working started.
  SEN0575_INPUT_REG_CUMULATIVE_RAINFALL_H        = 0x0009  
  ## The address of the input register for raw data (low 16-bit) in memory.
  SEN0575_INPUT_REG_RAW_DATA_L                   = 0x000A  
  ## The address of the input register for raw data (high 16-bit) in memory.
  SEN0575_INPUT_REG_RAW_DATA_H                   = 0x000B  
  ## The address of the input register for system working time in memory.
  SEN0575_INPUT_REG_SYS_TIME                     = 0x000C
  ## Set the time to calculate cumulative rainfall.
  SEN0575_HOLDING_REG_RAW_RAIN_HOUR              = 0x0006
  ## Set the base rainfall value.
  SEN0575_HOLDING_REG_RAW_BASE_RAINFALL          = 0x0007
  
  ## The address of the input register for PID in memory.
  SEN0575_I2C_REG_PID                          = 0x00
  ## The address of the input register for VID in memory.
  SEN0575_I2C_REG_VID                          = 0x02
  ## The address of the input register for firmware version in memory.
  SEN0575_I2C_REG_VERSION                      = 0x0A
  ## SEN0575 Stores the cumulative rainfall within the set time
  SEN0575_I2C_REG_TIME_RAINFALL                = 0x0C
  ## SEN0575 Stores the cumulative rainfall since starting work
  SEN0575_I2C_REG_CUMULATIVE_RAINFALL          = 0x10
  ## SEN0575 Stores the low 16 bits of the raw data
  SEN0575_I2C_REG_RAW_DATA                     = 0x14
  ## SEN0575 Stores the system time
  SEN0575_I2C_REG_SYS_TIME                     = 0x18
  
  ## Sets the time for calculating the cumulative rainfall
  SEN0575_I2C_REG_RAW_RAIN_HOUR                = 0x26
  ## Sets the base value of accumulated rainfall
  SEN0575_I2C_REG_RAW_BASE_RAINFALL            = 0x28

  I2C_MODE  =0
  UART_MODE =1

  '''!
    @brief Define DFRobot_RainfallSensor basic class
    @details Drive the sensor
  '''
  def __init__(self, mode):
    self._mode = mode
    self.vid = 0
    self.pid = 0
  
  def begin(self):
    '''!
      @brief This function will attempt to communicate with a slave device and determine if the communication is successful based on the return value.
      @return Communication result
      @retval true  Succeed
      @retval false Failed
    '''
    return self.get_pid_vid()

  def get_firmware_version(self):
    '''!
      @brief  get firmware version
      @return  Return  firmware version
    '''
    if self._mode == self.I2C_MODE :
      list = self._read_register(self.SEN0575_I2C_REG_VERSION, 2)
      version = list[0] | ( list[1] << 8 )
    else:
      list = self._read_register(self.SEN0575_INPUT_REG_VERSION, 1)
      version = list[0]
    return str(version >> 12) + '.'+ str( ( (version >> 8) & 0x0F ) ) + '.' + str( ( (version >> 4) & 0x0F ) ) + '.' + str( (version & 0x0F) )

  def get_sensor_working_time(self):
    '''!
      @brief Obtain the sensor working time
      @return Working time of the sensor, in hours
    '''
    if self._mode == self.I2C_MODE:
      list = self._read_register(self.SEN0575_I2C_REG_SYS_TIME, 2)
      working_time = list[0] | (list[1] << 8)
    else:
      list = self._read_register(self.SEN0575_INPUT_REG_SYS_TIME, 1)
      working_time = list[0]
    return working_time / 60.0

  def get_pid_vid(self):
    '''!
      @brief  Get the PID and VID of the device.
      @return   Return true if the data is obtained correctly, false if failed or incorrect data.
    '''
    ret = False
    if self._mode == self.I2C_MODE:
      list = self._read_register(self.SEN0575_I2C_REG_PID, 4)
      self.pid = list[0] | ( list[1] << 8 ) | ( ( list[3] & 0xC0 ) << 10 )
      self.vid = list[2] | ( ( list[3] & 0x3F ) << 8 )
    else:
      list = self._read_register(self.SEN0575_INPUT_REG_PID, 2)
      self.pid = ( ( list[1] & 0xC000 ) << 2 ) | list[0]
      self.vid = list[1] & 0x3FFF
    if (self.vid == 0x3343) and (self.pid == 0x100C0):
      ret = True
    return ret

  def get_rainfall(self):
    '''!
      @brief  Get cumulative rainfall
      @return Cumulative rainfall value
    '''
    if self._mode == self.I2C_MODE:
      list = self._read_register(self.SEN0575_I2C_REG_CUMULATIVE_RAINFALL, 4)
      rainfall = list[0] | ( list[1] << 8 ) | ( list[2] << 16 ) | ( list[3] << 24 )
    else:
      list = self._read_register(self.SEN0575_INPUT_REG_CUMULATIVE_RAINFALL_L, 2)
      rainfall = list[0] | ( list[1] << 16 )
    return rainfall / 10000.0

  def get_rainfall_time(self,hour):
    '''!
      @brief  Get the cumulative rainfall within the specified time
      @param hour Specified time (valid range is 1-24 hours)
      @return Cumulative rainfall
    '''
    if hour>24:
      return 0
    list = [hour]
    if self._mode == self.I2C_MODE:
      self._write_register(self.SEN0575_I2C_REG_RAW_RAIN_HOUR, list)
      list = self._read_register(self.SEN0575_I2C_REG_TIME_RAINFALL, 4)
      rainfall = list[0] | ( list[1] << 8 ) | ( list[2] << 16 ) | ( list[3] << 24 )
    else:
      self._write_register(self.SEN0575_HOLDING_REG_RAW_RAIN_HOUR, list)
      list = self._read_register(self.SEN0575_INPUT_REG_TIME_RAIN_FALL_L, 2)
      rainfall = list[0] | ( list[1] << 16 )
    return rainfall / 10000.0

  def get_raw_data(self):
    '''!
      @brief Get raw data
      @return Number of tipping bucket counts, unit: count
    '''
    if self._mode == self.I2C_MODE:
      list = self._read_register(self.SEN0575_I2C_REG_RAW_DATA, 4)
      raw_data = list[0] | ( list[1] << 8 ) | ( list[2] << 16 ) | ( list[3] << 24 )
    else:
      list = self._read_register( self.SEN0575_INPUT_REG_RAW_DATA_L, 2 )
      raw_data = list[0] | ( list[1] << 16 )
    return raw_data

  def set_rain_accumulated_value(self, value):
    '''!
      @brief Set the rainfall accumulation value
      @param value Rainfall accumulation value, in millimeters
      @return Returns 0 if setting succeeded, other values if setting failed
    '''
    data = int(value * 10000)
    if self._mode == self.I2C_MODE:
      list=[data & 0xFF , data >> 8]
      ret=self._write_register(self.SEN0575_I2C_REG_RAW_BASE_RAINFALL, list)
    else:
      ret=self._write_register(self.SEN0575_HOLDING_REG_RAW_BASE_RAINFALL, [data])
    return ret

  def _write_reg(self, reg, data):
    '''!
      @brief writes data to a register
      @param reg register address
      @param data written data
    '''
    # Low level register writing, not implemented in base class
    raise NotImplementedError()

  def _read_reg(self, reg, length):
    '''!
      @brief read the data from the register
      @param reg register address
      @param length read data length
      @return read data list
    '''
    # Low level register writing, not implemented in base class
    raise NotImplementedError()

class DFRobot_RainfallSensor_UART(DFRobot_RainfallSensor):
  '''!
    @brief Define DFRobot_RainfallSensor_UART class
    @details Drive the sensor
  '''
  def __init__(self,):
    '''!
      @brief Initialize the serial port
    '''
    self._baud = 9600
    self._addr = 0xC0
    self.master = modbus_rtu.RtuMaster( serial.Serial(port="/dev/ttyUSB1", baudrate=9600, bytesize=8, parity='N', stopbits=1) )
    self.master.set_timeout(5.0)
    super(DFRobot_RainfallSensor_UART, self).__init__(self.UART_MODE)

  def _write_register(self, reg, data):
    '''!
      @brief writes data to a register
      @param reg register address
      @param data written data
    '''
    ret=True
    list_write=list( self.master.execute(self._addr, cst.WRITE_MULTIPLE_REGISTERS, reg, output_value=data) )
    time.sleep(0.030)
    if list_write[1] != len(data):
      ret=False
    return ret

  def _read_register(self, reg, length):
    '''!
      @brief read the data from the register
      @param reg register address
      @param length read data length
      @return read data list
    '''
    return list( self.master.execute(self._addr, cst.READ_INPUT_REGISTERS, reg, length) )

class DFRobot_RainfallSensor_I2C(DFRobot_RainfallSensor):
  '''!
    @brief Define DFRobot_RainfallSensor_I2C class
    @details Drive the sensor
  '''
  def __init__(self,bus=1):
    '''!
      @brief Initialize I2C
    '''
    self._addr = 0x1D
    self.i2c = smbus.SMBus(bus)
    super(DFRobot_RainfallSensor_I2C, self).__init__(self.I2C_MODE)

  def _write_register(self, reg, data):
    '''!
      @brief writes data to a register
      @param reg register address
      @param data written data
    '''
    try:
      self.i2c.write_i2c_block_data(self._addr, reg, data)
      time.sleep(0.050)
    except:
      pass
    return True

  def _read_register(self, reg, length):
    '''!
      @brief read the data from the register
      @param reg register address
      @param length read data length
      @return read data list
    '''
    ret=[]
    ret = [0]*length
    try:
      ret=self.i2c.read_i2c_block_data(self._addr, reg, length)
    except:
      pass
    return ret

sensor = DFRobot_RainfallSensor_I2C()
rain_per_tip = 0.3  # mm per tipping bucket
rain_accumulated = 0.0  # mm total
rain_count = 0
last_pulse_time = None  # Timestamp dari sinyal terakhir
interval = 1  # Interval polling dalam detik
last_value = None  # Menyimpan nilai raw data terakhir
start_time = time.time()  # Waktu mulai

def rain_event_detected():
    global rain_accumulated, last_pulse_time

    current_time = time.time()
    if last_pulse_time is not None:
        interval = current_time - last_pulse_time
        intensity = rain_per_tip / interval  # Intensitas dalam mm per detik
        print(f"Intensitas: {intensity:.3f} mm/detik")

    rain_accumulated += rain_per_tip
    last_pulse_time = current_time

    print(f"Curah hujan terkini: {rain_accumulated:.3f} mm")

def setup():
    while sensor.begin() == False:
        print("Sensor tidak terdeteksi.")
        time.sleep(1)
    print("Sensor terdeteksi.")
    global last_value
    last_value = None

def loop():
    global last_value
    global rain_count
    global rain_accumulated
    global start_time
    global last_pulse_time  # Deklarasikan variabel global di sini

    # Mendapatkan data mentah dari sensor (tipping bucket count)
    rainfall_raw = sensor.get_raw_data()

    # Menghitung perubahan data raw (tipping bucket)
    if last_value is not None:
        per_tip_rainfall = rainfall_raw - last_value
        rain_count += per_tip_rainfall

    last_value = rainfall_raw

    # Menghitung dan mencatat curah hujan dalam interval waktu tertentu
    if time.time() - start_time >= interval:
        mm = rain_count * rain_per_tip  # Konversi tipping bucket count ke mm
        mm_rounded = round(mm, 3)
        rain_accumulated += mm_rounded
        rain_count = 0  # Reset penghitung tipping bucket
        start_time = time.time()  # Reset waktu mulai

        # Menghitung intensitas hujan berbasis waktu antara tipping buckets
        if mm_rounded > 0:  # Jika ada rain detected
            if last_pulse_time is not None:
                # Menghitung waktu sejak tipping terakhir
                time_since_last_pulse = time.time() - last_pulse_time
                intensity = mm_rounded / time_since_last_pulse  # Intensitas per detik
                print(f"{intensity:.2f}")
            
            # Update waktu terakhir pulse
            last_pulse_time = time.time()

        # Menampilkan curah hujan jika tidak ada data tipping bucket baru dalam interval
        if mm_rounded == 0:
            print(f"{mm_rounded}")

if __name__ == "__main__":
    setup()
    try:
        while True:
            loop()
            time.sleep(0.1)  # Interval polling sensor
    except KeyboardInterrupt:
        print("Program dihentikan.")
