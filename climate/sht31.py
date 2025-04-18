#!/home/pi/code/envPumma/bin/python3
# -*- coding:utf-8 -*-

import sys
import smbus
import logging
import numpy as np
from ctypes import *
import spidev
import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

logger = logging.getLogger()
logger.setLevel(logging.INFO)  #?????????
#logger.setLevel(logging.FATAL)#??????????,?????,???????
ph = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - [%(filename)s %(funcName)s]:%(lineno)d - %(levelname)s: %(message)s")
ph.setFormatter(formatter)
logger.addHandler(ph)

SHT3X_CMD_READ_SERIAL_NUMBER             = 0x3780
SHT3X_CMD_GETDATA_H                      = 0x2400
SHT3X_CMD_GETDATA_M                      = 0x240B
SHT3X_CMD_GETDATA_L                      = 0x2416
SHT3X_CMD_SETMODE_H_FREQUENCY_HALF_HZ    = 0x2032
SHT3X_CMD_SETMODE_M_FREQUENCY_HALF_HZ    = 0x2024
SHT3X_CMD_SETMODE_L_FREQUENCY_HALF_HZ    = 0x202F
SHT3X_CMD_SETMODE_H_FREQUENCY_1_HZ       = 0x2130
SHT3X_CMD_SETMODE_M_FREQUENCY_1_HZ       = 0x2126
SHT3X_CMD_SETMODE_L_FREQUENCY_1_HZ       = 0x212D
SHT3X_CMD_SETMODE_H_FREQUENCY_2_HZ       = 0x2236
SHT3X_CMD_SETMODE_M_FREQUENCY_2_HZ       = 0x2220
SHT3X_CMD_SETMODE_L_FREQUENCY_2_HZ       = 0x222B
SHT3X_CMD_SETMODE_H_FREQUENCY_4_HZ       = 0x2334
SHT3X_CMD_SETMODE_M_FREQUENCY_4_HZ       = 0x2322
SHT3X_CMD_SETMODE_L_FREQUENCY_4_HZ       = 0x2329
SHT3X_CMD_SETMODE_H_FREQUENCY_10_HZ      = 0x2737
SHT3X_CMD_SETMODE_M_FREQUENCY_10_HZ      = 0x2721
SHT3X_CMD_SETMODE_L_FREQUENCY_10_HZ      = 0x272A
SHT3X_CMD_GETDATA                        = 0xE000

SHT3X_CMD_STOP_PERIODIC_ACQUISITION_MODE = 0x3093
SHT3X_CMD_SOFT_RESET                     = 0x30A2
SHT3X_CMD_HEATER_ENABLE                  = 0x306D
SHT3X_CMD_HEATER_DISABLE                 = 0x3066
SHT3X_CMD_READ_STATUS_REG                = 0xF32D
SHT3X_CMD_CLEAR_STATUS_REG               = 0x3041

SHT3X_CMD_READ_HIGH_ALERT_LIMIT_SET      = 0xE11F
SHT3X_CMD_READ_HIGH_ALERT_LIMIT_CLEAR    = 0xE114
SHT3X_CMD_READ_LOW_ALERT_LIMIT_CLEAR     = 0xE109
SHT3X_CMD_READ_LOW_ALERT_LIMIT_SET       = 0xE102
SHT3X_CMD_WRITE_HIGH_ALERT_LIMIT_SET     = 0x611D
SHT3X_CMD_WRITE_HIGH_ALERT_LIMIT_CLEAR   = 0x6116
SHT3X_CMD_WRITE_LOW_ALERT_LIMIT_CLEAR    = 0x610B
SHT3X_CMD_WRITE_LOW_ALERT_LIMIT_SET      = 0x6100

TEMP_RH_TEMP_C = 0
TEMP_RH_HUM    = 1
TEMP_RH_TEMP_F  = 2
TEMP_RH_ERR    = 3

HIGH_SET   = 0
HIGH_CLEAR = 1 
LOW_SET    = 2
LOW_CLEAR  = 3

class DFRobot_SHT3x:

  ERR_OK         =    0      #???
  ERR_DATA_BUS   =   -1      #??????
  ERR_IC_VERSION =   -2      #???????

  Periodic = 0 #<Cycle measurement mode
  One_Shot =1,  #<Single measurement mode

  repeatability_high = 0    #/**<In high repeatability mode, the humidity repeatability is 0.10%RH, the temperature repeatability is 0.06°C*/
  repeatability_medium = 1  #/**<In medium repeatability mode, the humidity repeatability is 0.15%RH, the temperature repeatability is 0.12°C*/
  repeatability_low = 2     #/**<In low repeatability mode, the humidity repeatability is0.25%RH, the temperature repeatability is 0.24°C*/
  repeatability_periodic = 3
  measureFreq_0_5Hz = 0
  measureFreq_1Hz = 1
  measureFreq_2Hz = 2
  measureFreq_4Hz = 3
  measureFreq_10Hz = 4

  def __init__(self, iic_addr = 0x45,bus = 1):
    self.i2cbus=smbus.SMBus(bus)
    self.i2c_addr = iic_addr
    self.tempRH= [0,0,0,0]
    self.limit_Data = [0,0,0,0]
    self._measure_freq = 0


  def begin(self,RST = 4):
    '''!
       @brief Initialize the function
       @return Return 0 indicates a successful initialization, while other values indicates failure and return to error code.
    '''
    self._RST = RST
    self.measurement_mode = self.One_Shot
    GPIO.setup(self._RST, GPIO.OUT)
    GPIO.output(self._RST, GPIO.HIGH)
    if(self.read_serial_number() == 0):
      logger.warning("bus data access error")
      return self.ERR_DATA_BUS
    return self.ERR_OK

  def read_serial_number(self):
    '''!
      @brief Read the serial number of the chip
      @return 32-digit serial number
    '''
    result = 0
    self.__write_reg(SHT3X_CMD_READ_SERIAL_NUMBER>>8,SHT3X_CMD_READ_SERIAL_NUMBER&0xFF)
    time.sleep(0.001)
    data0 = self.__read_reg(6)
    data1= [data0[0],data0[1],data0[2]]
    data2= [data0[3],data0[4],data0[5]]
    if((self.__check_crc(data1) == data0[2]) and (self.__check_crc(data2) == data0[5])):
      result = data0[0]
      result = (result << 8) | data0[1]
      result = (result << 8) | data0[3]
      result = (result << 8) | data0[4]
    return result


  def soft_reset(self):
    '''!
       @brief Send command resets via iiC, enter the chip's default mode single-measure mode, 
       turn off the heater, and clear the alert of the ALERT pin.
       @return Read the status register to determine whether the command was executed successfully, and returning true indicates success
    '''
    self.__write_reg(SHT3X_CMD_SOFT_RESET>>8,SHT3X_CMD_SOFT_RESET&0xFF)
    time.sleep(0.001)
    register_raw = self.__read_status_register()
    if((register_raw & 0x02) == 0):
      return True
    else:
      return False


  def pin_reset(self):
    '''!
       @brief Reset through the chip's reset pin, enter the chip's default mode single-measure mode, and clear the alert of the ALERT pin.
       @return The status register has a data bit that detects whether the chip has been reset, and returning true indicates success
    '''
    self.clear_status_register()
    GPIO.output(self._RST, GPIO.LOW)
    time.sleep(0.001)
    GPIO.output(self._RST, GPIO.HIGH)
    time.sleep(0.001)
    register_raw = self.__read_status_register()
    if((register_raw & 0x10) == 1):
      return True
    else:
      return False


  def stop_periodic_mode(self):
    '''!
       @brief Exit from cycle measurement mode
       @return Read the status of the register to determine whether the command was executed successfully, and returning true indicates success
    '''
    self.measurement_mode = self.One_Shot
    self.__write_reg(SHT3X_CMD_STOP_PERIODIC_ACQUISITION_MODE>>8,SHT3X_CMD_STOP_PERIODIC_ACQUISITION_MODE&0xFF)
    time.sleep(0.001)
    register_raw = self.__read_status_register()
    if((register_raw & 0x02) == 0):
      return True
    else:
      return False


  def heater_enable(self):
    '''!
       @brief Turn on the heater inside the chip
       @return Read the status of the register to determine whether the command was executed successfully, and returning true indicates success
       @note Heaters should be used in wet environments, and other cases of use will result in incorrect readings
    '''
    self.__write_reg(SHT3X_CMD_HEATER_ENABLE>>8,SHT3X_CMD_HEATER_ENABLE&0xFF)
    time.sleep(0.001)
    register_raw = self.__read_status_register()
    if((register_raw & 0x2000) == 1):
      return True
    else:
      return False



  def heater_disable(self):
    '''!
       @brief Turn off the heater inside the chip
       @return Read the status of the register to determine whether the command was executed successfully, and returning true indicates success
       @note Heaters should be used in wet environments, and other cases of use will result in incorrect readings
    '''
    self.__write_reg(SHT3X_CMD_HEATER_DISABLE>>8,SHT3X_CMD_HEATER_DISABLE&0xFF)
    time.sleep(0.001)
    register_raw = self.__read_status_register()
    if((register_raw & 0x2000) == 0):
      return True
    else:
      return False


  def clear_status_register(self):
    '''!
      @brief All flags (Bit 15, 11, 10, 4) in the status register can be cleared (set to zero)
      @n  Set bit:15 to 0 so that ALERT pin can work, otherwise it will keep high.
    '''
    self.__write_reg(SHT3X_CMD_CLEAR_STATUS_REG>>8,SHT3X_CMD_CLEAR_STATUS_REG&0xFF)
    time.sleep(0.01)


  def read_alert_state(self):
    '''!
       @brief Read the state of the pin ALERT.
       @return High returns 1, low returns 0.
    '''
    time.sleep(0.001)
    register_raw = self.__read_status_register()
    if(((register_raw & 0x0800) == 1)or((register_raw & 0x0400) == 1)):
      return True
    else:
      return False


  def read_temperature_and_humidity(self,repeatability = repeatability_periodic):
    self.tempRH[TEMP_RH_ERR] = 0
    if (repeatability == self.repeatability_high):
      self.__write_reg(SHT3X_CMD_GETDATA_H>>8,SHT3X_CMD_GETDATA_H&0xFF)
      time.sleep(0.015)
    elif(repeatability == self.repeatability_medium):
      self.__write_reg(SHT3X_CMD_GETDATA_M>>8,SHT3X_CMD_GETDATA_M&0xFF)
      time.sleep(0.015)
    elif(repeatability == self.repeatability_low):
      self.__write_reg(SHT3X_CMD_GETDATA_L>>8,SHT3X_CMD_GETDATA_L&0xFF)
      time.sleep(0.015)
    elif(repeatability == self.repeatability_periodic):
      self.__write_reg(SHT3X_CMD_GETDATA>>8,SHT3X_CMD_GETDATA&0xFF)
      time.sleep(0.015)
    data0 = self.__read_reg(6)
    data1= [data0[0],data0[1],data0[2]]
    data2= [data0[3],data0[4],data0[5]]
    if((self.__check_crc(data1) != data0[2]) or (self.__check_crc(data2) != data0[5])):
      self.tempRH[TEMP_RH_ERR] = -1
      return self.tempRH
    self.tempRH[TEMP_RH_TEMP_C] = self.__convert_temperature(data1)
    self.tempRH[TEMP_RH_TEMP_F] = (9.0/5)*self.tempRH[TEMP_RH_TEMP_C] + 32
    self.tempRH[TEMP_RH_HUM] = self.__convert_humidity(data2)
    return self.tempRH


  def get_temperature_C(self):
    '''!
       @brief Get the measured temperature (in degrees Celsius)
       @return Return the float temperature data 
    '''
    if(self.measurement_mode == self.One_Shot):
      self.read_temperature_and_humidity(self.repeatability_high)
    else:
      self.read_temperature_and_humidity()
    return self.tempRH[TEMP_RH_TEMP_C]


  def get_temperature_F(self):
    '''!
       @brief Get the measured temperature (in degrees Fahrenheit)
       @return Return the float temperature data 
    '''
    if(self.measurement_mode == self.One_Shot):
      self.read_temperature_and_humidity(self.repeatability_high)
    else:
      self.read_temperature_and_humidity()
    return self.tempRH[TEMP_RH_TEMP_F]


  def get_humidity_RH(self):
    '''!
       @brief Get measured humidity(%RH)
       @return Return the float humidity data
    '''
    if(self.measurement_mode == self.One_Shot):
      self.read_temperature_and_humidity(self.repeatability_high)
    else:
      self.read_temperature_and_humidity()
    return self.tempRH[TEMP_RH_HUM]


  def start_periodic_mode(self,measure_freq,repeatability = repeatability_high):
    cmd=[[SHT3X_CMD_SETMODE_H_FREQUENCY_HALF_HZ,SHT3X_CMD_SETMODE_M_FREQUENCY_HALF_HZ,SHT3X_CMD_SETMODE_L_FREQUENCY_HALF_HZ],\
         [SHT3X_CMD_SETMODE_H_FREQUENCY_1_HZ,SHT3X_CMD_SETMODE_M_FREQUENCY_1_HZ,SHT3X_CMD_SETMODE_L_FREQUENCY_1_HZ],\
         [SHT3X_CMD_SETMODE_H_FREQUENCY_2_HZ,SHT3X_CMD_SETMODE_M_FREQUENCY_2_HZ,SHT3X_CMD_SETMODE_L_FREQUENCY_2_HZ],\
         [SHT3X_CMD_SETMODE_H_FREQUENCY_4_HZ,SHT3X_CMD_SETMODE_M_FREQUENCY_4_HZ,SHT3X_CMD_SETMODE_L_FREQUENCY_4_HZ],\
         [SHT3X_CMD_SETMODE_H_FREQUENCY_10_HZ,SHT3X_CMD_SETMODE_M_FREQUENCY_10_HZ,SHT3X_CMD_SETMODE_L_FREQUENCY_10_HZ]\
        ]
    self.measurement_mode = self.Periodic
    self._measure_freq = measure_freq
    self.__write_reg(cmd[measure_freq][repeatability]>>8,cmd[measure_freq][repeatability]&0xFF)
    time.sleep(0.001)
    register_raw = self.__read_status_register()
    if((register_raw & 0x02) == 0):
      return True
    else:
      return False

  def __read_status_register(self):
    '''!
       @brief Read the data stored in the status register.
       @return Return to status like whether heater is ON or OFF, the status of the pin alert, reset status and the former cmd is executed or not.
    '''
    for i in range(0,10):
      self.__write_reg(SHT3X_CMD_READ_STATUS_REG>>8,SHT3X_CMD_READ_STATUS_REG&0xFF)
      time.sleep(0.001)
      register1 = self.__read_reg(3)
      if(self.__check_crc(register1) == register1[2]):
        break
    data = (register1[0]<<8) | register1[1]
    return data


  def environment_state(self):
    '''!
      @brief Determine if the temperature and humidity are out of the threshold range
      @return Return the status code, representing as follows
      @n 01 :Indicates that the humidity exceeds the lower threshold range
      @n 10 :Indicates that the temperature exceeds the lower threshold range
      @n 11 :Indicates that both the humidity and the temperature exceed the lower threshold range
      @n 02 :Indicates that the humidity exceeds the upper threshold range
      @n 20 :Indicates that the temperature exceeds the upper threshold range
      @n 22 :Indicates that both the humidity and the temperature exceed the upper threshold range
      @n 12 :Indicates that the temperature exceeds the lower threshold range,
              and the humidity exceeds the upper threshold range
      @n 21 :Indicates that the temperature exceeds the upper threshold range,
              and the humidity exceeds the lower threshold range
    '''
    ret = 0
    registerRaw = self.__read_status_register()
    data = self.read_temperature_and_humidity()
    if(self.measure_temperature_limit_C()):
      temp_high_set = self.get_temperature_high_set_C()
      temp_low_set = self.get_temperature_low_set_C()
    if(self.measure_humidity_limit_RH()):
      rh_high_set = self.get_humidity_high_set_RH()
      rh_low_set  = self.get_humidity_low_set_RH() 
    if(((registerRaw & 0x0800) == 1) and ((registerRaw & 0x0400) == 0)):
      if(data[TEMP_RH_HUM]>rh_high_set):
        ret = 2
      elif(data[TEMP_RH_HUM]<rh_low_set):
        ret = 1
    elif((((registerRaw & 0x0800) == 0) and ((registerRaw & 0x0400) == 1))):
      if(data[TEMP_RH_TEMP_C]>temp_high_set):
        ret = 20
      elif(data[TEMP_RH_TEMP_C]<temp_low_set):
        return 10
    elif((((registerRaw & 0x0800) == 1) and ((registerRaw & 0x0400) == 1))):
      if((data[TEMP_RH_TEMP_C]<temp_low_set) and (data[TEMP_RH_HUM]<rh_low_set)):
        ret = 11
      elif((data[TEMP_RH_TEMP_C]>temp_high_set) and (data[TEMP_RH_HUM]>rh_high_set)):
        ret = 22
      elif((data[TEMP_RH_TEMP_C]>temp_high_set) and (data[TEMP_RH_HUM]<rh_low_set)):
        ret = 21
      elif((data[TEMP_RH_TEMP_C]<temp_low_set) and  (data[TEMP_RH_HUM]>rh_high_set)):
        ret = 12
    return ret



  def set_temperature_limit_C(self,high_set,high_clear, low_set,low_clear):
    ret =0
    if((high_set > high_clear) and (high_clear > low_clear) and (low_clear > low_set)):
      
      _high_set = self.__convert_raw_temperature(high_set)
      self.__write_reg(SHT3X_CMD_READ_HIGH_ALERT_LIMIT_SET>>8,SHT3X_CMD_READ_HIGH_ALERT_LIMIT_SET&0xFF)
      time.sleep(0.001)
      buf = self.__read_reg(3)
      if(self.__check_crc(buf)!= buf[2]):
        return 1
      limit = buf[0]
      limit = limit<< 8 | buf[1]
      _high_set = (_high_set >> 7) | (limit & 0xfe00)
      self.__write_limit_data(SHT3X_CMD_WRITE_HIGH_ALERT_LIMIT_SET,_high_set)
      
      _high_clear= self.__convert_raw_temperature(high_clear)
      self.__write_reg(SHT3X_CMD_READ_HIGH_ALERT_LIMIT_CLEAR>>8,SHT3X_CMD_READ_HIGH_ALERT_LIMIT_CLEAR&0xFF)
      time.sleep(0.001)
      buf = self.__read_reg(3)
      if(self.__check_crc(buf)!= buf[2]):
        return 1
      limit = buf[0]
      limit = limit<< 8 | buf[1]
      _high_clear = (_high_clear >> 7) | (limit & 0xfe00)
      self.__write_limit_data(SHT3X_CMD_WRITE_HIGH_ALERT_LIMIT_CLEAR,_high_clear)
      
      _low_clear= self.__convert_raw_temperature(low_clear)
      self.__write_reg(SHT3X_CMD_READ_LOW_ALERT_LIMIT_CLEAR>>8,SHT3X_CMD_READ_LOW_ALERT_LIMIT_CLEAR&0xFF)
      time.sleep(0.001)
      buf = self.__read_reg(3)
      if(self.__check_crc(buf)!= buf[2]):
        return 1
      limit = buf[0]
      limit = limit<< 8 | buf[1]
      _low_clear = (_low_clear >> 7) | (limit & 0xfe00)
      self.__write_limit_data(SHT3X_CMD_WRITE_LOW_ALERT_LIMIT_CLEAR,_low_clear)

      _low_set= self.__convert_raw_temperature(low_set)
      self.__write_reg(SHT3X_CMD_READ_LOW_ALERT_LIMIT_SET>>8,SHT3X_CMD_READ_LOW_ALERT_LIMIT_SET&0xFF)
      time.sleep(0.001)
      buf = self.__read_reg(3)
      if(self.__check_crc(buf)!= buf[2]):
        return 1
      limit = buf[0]
      limit = limit<< 8 | buf[1]
      _low_set = (_low_set >> 7) | (limit & 0xfe00)
      self.__write_limit_data(SHT3X_CMD_WRITE_LOW_ALERT_LIMIT_SET,_low_set)
    else :
      ret =1 
    return ret


  def set_temperature_limit_F(self,high_set,high_clear, low_set,low_clear):
    _high_set = (high_set - 32) * 5.0 / 9.0
    _high_clear = (high_clear - 32) * 5.0 / 9.0
    _low_clear = (low_clear - 32) * 5.0 / 9.0
    _low_set = (low_set - 32) * 5.0 / 9.0
    ret =1
    if(self.set_temperature_limit_C(_high_set,_high_clear,_low_set,_low_clear) == 0):
      ret = 0
    return ret


  def set_humidity_limit_RH(self,high_set,high_clear, low_set,low_clear):
    '''!
       @brief Set the relative humidity threshold temperature and the alarm clear humidity(%RH)
       @param highset  High humidity alarm point, when the humidity is greater than this value, the ALERT pin generates an alarm signal.
       @param highClear  High humidity alarm clear point, alarming when the humidity higher than the highset, otherwise the alarm signal will be cleared.
       @param lowset  Low humidity alarm point, when the humidity is lower than this value, the ALERT pin generates an alarm signal.
       @param lowclear  Low humidity alarm clear point, alarming when the humidity lower than the highset, otherwise the alarm signal will be cleared.
       @note range  0 - 100 %RH, highset > highClear > lowclear > lowset 
       @return  A return to 0 indicates a successful setting.
    '''
    limit = 0
    if((high_set > high_clear) and (high_clear > low_clear) and (low_clear > low_set)):
      
      _high_set = self.__convert_raw_humidity(high_set)
      self.__write_reg(SHT3X_CMD_READ_HIGH_ALERT_LIMIT_SET>>8,SHT3X_CMD_READ_HIGH_ALERT_LIMIT_SET&0xFF)
      time.sleep(0.001)
      buf = self.__read_reg(3)
      if(self.__check_crc(buf)!= buf[2]):
        return 1
      limit = buf[0]
      limit = limit<< 8 | buf[1]
      _high_set = (_high_set & 0xfe00) | (limit & 0x1FF)
      self.__write_limit_data(SHT3X_CMD_WRITE_HIGH_ALERT_LIMIT_SET,_high_set)
      
      _high_clear= self.__convert_raw_humidity(high_clear)
      self.__write_reg(SHT3X_CMD_READ_HIGH_ALERT_LIMIT_CLEAR>>8,SHT3X_CMD_READ_HIGH_ALERT_LIMIT_CLEAR&0xFF)
      time.sleep(0.001)
      buf = self.__read_reg(3)
      if(self.__check_crc(buf)!= buf[2]):
        return 1
      limit = buf[0]
      limit = limit<< 8 | buf[1]
      _high_clear = (_high_clear & 0xfe00) | (limit & 0x1FF)
      self.__write_limit_data(SHT3X_CMD_WRITE_HIGH_ALERT_LIMIT_CLEAR,_high_clear)
      
      _low_clear= self.__convert_raw_humidity(low_clear)
      self.__write_reg(SHT3X_CMD_READ_LOW_ALERT_LIMIT_CLEAR>>8,SHT3X_CMD_READ_LOW_ALERT_LIMIT_CLEAR&0xFF)
      time.sleep(0.001)
      buf = self.__read_reg(3)
      if(self.__check_crc(buf)!= buf[2]):
        return 1
      limit = buf[0]
      limit = limit<< 8 | buf[1]
      _low_clear = (_low_clear & 0xfe00) | (limit & 0x1FF)
      self.__write_limit_data(SHT3X_CMD_WRITE_LOW_ALERT_LIMIT_CLEAR,_low_clear)

      _low_set= self.__convert_raw_humidity(low_set)
      self.__write_reg(SHT3X_CMD_READ_LOW_ALERT_LIMIT_SET>>8,SHT3X_CMD_READ_LOW_ALERT_LIMIT_SET&0xFF)
      time.sleep(0.001)
      buf = self.__read_reg(3)
      if(self.__check_crc(buf)!= buf[2]):
        return 1
      limit = buf[0]
      limit = limit<< 8 | buf[1]
      _low_set = (_low_set & 0xfe00) | (limit & 0x1FF)
      self.__write_limit_data(SHT3X_CMD_WRITE_LOW_ALERT_LIMIT_SET,_low_set)
    else :
      return 1 
    return 0


  def measure_temperature_limit_C(self):
    '''!
       @brief Measure temperature threshold temperature and alarm clear temperature
       @return Return true indicates successful data acquisition
    '''
    limit = 0
    self.__write_reg(SHT3X_CMD_READ_HIGH_ALERT_LIMIT_SET>>8,SHT3X_CMD_READ_HIGH_ALERT_LIMIT_SET&0xFF)
    time.sleep(0.001)
    buf = self.__read_reg(3)
    if(self.__check_crc(buf)!= buf[2]):
      return False
    limit = buf[0]
    limit = limit<< 8 | buf[1]
    data = self.__convert_temp_limit_data(limit)
    self.limit_Data[HIGH_SET] = round(data,2)

    self.__write_reg(SHT3X_CMD_READ_HIGH_ALERT_LIMIT_CLEAR>>8,SHT3X_CMD_READ_HIGH_ALERT_LIMIT_CLEAR&0xFF)
    time.sleep(0.001)
    buf = self.__read_reg(3)
    if(self.__check_crc(buf)!= buf[2]):
      return False
    limit = buf[0]
    limit = limit<< 8 | buf[1]
    data = self.__convert_temp_limit_data(limit)
    self.limit_Data[HIGH_CLEAR] = round(data,2)

    self.__write_reg(SHT3X_CMD_READ_LOW_ALERT_LIMIT_CLEAR>>8,SHT3X_CMD_READ_LOW_ALERT_LIMIT_CLEAR&0xFF)
    time.sleep(0.001)
    buf = self.__read_reg(3)
    if(self.__check_crc(buf)!= buf[2]):
      return False
    limit = buf[0]
    limit = limit<< 8 | buf[1]
    data = self.__convert_temp_limit_data(limit)
    self.limit_Data[LOW_CLEAR] = round(data,2)

    self.__write_reg(SHT3X_CMD_READ_LOW_ALERT_LIMIT_SET>>8,SHT3X_CMD_READ_LOW_ALERT_LIMIT_SET&0xFF)
    time.sleep(0.001)
    buf = self.__read_reg(3)
    if(self.__check_crc(buf)!= buf[2]):
      return False
    limit = buf[0]
    limit = limit<< 8 | buf[1]
    data = self.__convert_temp_limit_data(limit)
    self.limit_Data[LOW_SET] = round(data,2)
    return True


  def measure_temperature_limit_F(self):
    '''!
       @brief Measure the threshold temperature and alarm clear temperature
       @return Return true indicates successful data acquisition
    '''
    limit = 0
    self.__write_reg(SHT3X_CMD_READ_HIGH_ALERT_LIMIT_SET>>8,SHT3X_CMD_READ_HIGH_ALERT_LIMIT_SET&0xFF)
    time.sleep(0.001)
    buf = self.__read_reg(3)
    if(self.__check_crc(buf)!= buf[2]):
      return False
    limit = buf[0]
    limit = limit<< 8 | buf[1]
    data = self.__convert_temp_limit_data(limit)
    self.limit_Data[HIGH_SET] = round((data * 9 / 5.0 + 32),2)

    self.__write_reg(SHT3X_CMD_READ_HIGH_ALERT_LIMIT_CLEAR>>8,SHT3X_CMD_READ_HIGH_ALERT_LIMIT_CLEAR&0xFF)
    time.sleep(0.001)
    buf = self.__read_reg(3)
    if(self.__check_crc(buf)!= buf[2]):
      return False
    limit = buf[0]
    limit = limit<< 8 | buf[1]
    data = self.__convert_temp_limit_data(limit)
    self.limit_Data[HIGH_CLEAR] = round(d(data * 9 / 5.0 + 32),2)

    self.__write_reg(SHT3X_CMD_READ_LOW_ALERT_LIMIT_CLEAR>>8,SHT3X_CMD_READ_LOW_ALERT_LIMIT_CLEAR&0xFF)
    time.sleep(0.001)
    buf = self.__read_reg(3)
    if(self.__check_crc(buf)!= buf[2]):
      return False
    limit = buf[0]
    limit = limit<< 8 | buf[1]
    data = self.__convert_temp_limit_data(limit)
    self.limit_Data[LOW_CLEAR] = round((data * 9 / 5.0 + 32),2)

    self.__write_reg(SHT3X_CMD_READ_LOW_ALERT_LIMIT_SET>>8,SHT3X_CMD_READ_LOW_ALERT_LIMIT_SET&0xFF)
    time.sleep(0.001)
    buf = self.__read_reg(3)
    if(self.__check_crc(buf)!= buf[2]):
      return False
    limit = buf[0]
    limit = limit<< 8 | buf[1]
    data = self.__convert_temp_limit_data(limit)
    self.limit_Data[LOW_SET] = round((data * 9 / 5.0 + 32),2)
    return True


  def measure_humidity_limit_RH(self):
    '''!
       @brief Measure the threshold humidity of relative humidity and alarm clear humidity
       @return Return true indicates successful data acquisition
    '''
    limit = 0
    self.__write_reg(SHT3X_CMD_READ_HIGH_ALERT_LIMIT_SET>>8,SHT3X_CMD_READ_HIGH_ALERT_LIMIT_SET&0xFF)
    time.sleep(0.001)
    buf = self.__read_reg(3)
    if(self.__check_crc(buf)!= buf[2]):
      return False
    limit = buf[0]
    limit = limit<< 8 | buf[1]
    self.limit_Data[HIGH_SET] = self.__convert_humidity_limit_data(limit)

    self.__write_reg(SHT3X_CMD_READ_HIGH_ALERT_LIMIT_CLEAR>>8,SHT3X_CMD_READ_HIGH_ALERT_LIMIT_CLEAR&0xFF)
    time.sleep(0.001)
    buf = self.__read_reg(3)
    if(self.__check_crc(buf)!= buf[2]):
      return False
    limit = buf[0]
    limit = limit<< 8 | buf[1]
    self.limit_Data[HIGH_CLEAR] = self.__convert_humidity_limit_data(limit)

    self.__write_reg(SHT3X_CMD_READ_LOW_ALERT_LIMIT_CLEAR>>8,SHT3X_CMD_READ_LOW_ALERT_LIMIT_CLEAR&0xFF)
    time.sleep(0.001)
    buf = self.__read_reg(3)
    if(self.__check_crc(buf)!= buf[2]):
      return False
    limit = buf[0]
    limit = limit<< 8 | buf[1]
    self.limit_Data[LOW_CLEAR] = self.__convert_humidity_limit_data(limit)

    self.__write_reg(SHT3X_CMD_READ_LOW_ALERT_LIMIT_SET>>8,SHT3X_CMD_READ_LOW_ALERT_LIMIT_SET&0xFF)
    time.sleep(0.001)
    buf = self.__read_reg(3)
    if(self.__check_crc(buf)!= buf[2]):
      return False
    limit = buf[0]
    limit = limit<< 8 | buf[1]
    self.limit_Data[LOW_SET] = self.__convert_humidity_limit_data(limit)
    return True


  def get_temperature_high_set_F(self):
    return self.limit_Data[HIGH_SET] 


  def get_temperature_high_clear_F(self):
    return self.limit_Data[HIGH_CLEAR] 


  def get_temperature_low_clear_F(self):
    return self.limit_Data[LOW_CLEAR] 


  def get_temperature_low_set_F(self):
    return self.limit_Data[LOW_SET] 


  def get_temperature_high_set_C(self):
    '''!
       @brief Get high temperature alarm points(°C)
       @return Return high temperature alarm points(°C)
    '''
    return self.limit_Data[HIGH_SET] 


  def get_temperature_high_clear_C(self):
    '''!
       @brief Get high temperature alarm clear points(°C)
       @return Return high temperature alarm clear points(°C)
    '''
    return self.limit_Data[HIGH_CLEAR] 


  def get_temperature_low_clear_C(self):
    '''!
       @brief Get low temperature alarm clear points(°C)
       @return Return low temperature alarm clear points(°C)
    '''
    return self.limit_Data[LOW_CLEAR] 


  def get_temperature_low_set_C(self):
    '''!
       @brief Get low temperature alarm points(°C)
       @return Return low temperature alarm points
    '''
    return self.limit_Data[LOW_SET] 


  def get_humidity_high_set_RH(self):
    '''!
       @brief Get the high humidity alarm point(%RH)
       @return Return the high humidity alarm point
    '''
    return self.limit_Data[HIGH_SET] 


  def get_humidity_high_clear_RH(self):
    '''!
       @brief Get the high humidity alarm clear point(%RH)
       @return Return the high humidity alarm clear point
    '''
    return self.limit_Data[HIGH_CLEAR] 


  def get_humidity_low_clear_RH(self):
    '''!
       @brief Get the low humidity alarm clear point(%RH)
       @return Return the low humidity alarm clear point
    '''
    return self.limit_Data[LOW_CLEAR] 


  def get_humidity_low_set_RH(self):
    '''!
       @brief Get the low humidity alarm point
       @return Return the low humidity alarm point
    '''
    return self.limit_Data[LOW_SET] 


  def __convert_temperature(self,raw_temperature):
    '''!
       @brief Convert the data returned from the sensor to temperature(°C).
       @param raw_temperature Data obtained from the sensor
       @return Celsius temperature.
    '''
    raw_value = raw_temperature[0]
    raw_value = (raw_value << 8) | raw_temperature[1]
    return 175.0 * raw_value / 65535 - 45


  def __convert_humidity(self,raw_humidity):
    '''!
       @brief Convert the data returned from the sensor to relative humidity.
       @param raw_humidity Data obtained from the sensor.
       @return Relative humidity.
    '''
    raw_value = raw_humidity[0]
    raw_value = (raw_value << 8) | raw_humidity[1]
    return 100.0 * raw_value / 65535


  def __convert_raw_temperature(self,value):
    '''!
       @brief The temperature data to be written is converted into the data needed by the chip.
       @param value The temperature need to be written.
       @return Data write to sensor.
    '''
    return np.uint16((value + 45) / 175 * 65535)


  def __convert_raw_humidity(self,value):
    '''!
       @brief The relative humidity data to be written is converted into the data needed by the chip.
       @param value The relative humidity data to be written
       @return Data write to sensor.
    '''
    return np.uint16(value / 100 * 65535)


  def __convert_temp_limit_data(self,limit):
    '''!
       @brief Convert the data returned from the sensor to temperature limited data
       @param limit Temperature limited data from sensor
       @return Temperature limited data
    '''
    limit = limit << 7
    limit = limit & 0xFF80
    limit = limit | 0x1A
    return 175.0 * limit / 65535 - 45


  def __convert_humidity_limit_data(self,limit):
    '''!
       @brief Convert the data returned from the sensor to humidity limited data
       @param limit Humidity limited data from sensor
       @return Humidity limited data
    '''
    limit = limit & 0xFE00
    limit = limit | 0xCD
    return round((100.0 * limit / 65535),2)


  def __check_crc(self,data):
    '''!
     * @brief CRC calibration.
     * @param data  Checksum data list
     * @return Obtained calibration code.
    '''
    crc = 0xFF
    for i in range(0,2):
      crc = crc^data[i]
      for bit in range(0,8):
        if(crc&0x80):
          crc = ((crc <<1)^0x31)
        else:
          crc = (crc<<1)
      crc = crc&0xFF
    return crc


  def __write_limit_data(self,cmd,limit_data):
    '''!
       @brief Write threshold data.
       @param cmd  Send threshold data of chip command.
       @param limitData Raw data on temperature and humidity need to be sent (humidity is 7 bits and temperatures are 11 bits).
       @return Return 0 indicates that the command was sent successfully, other return values suggest unsuccessful send.
    '''
    reg = cmd >> 8
    command = [0,0,0,0]
    command[0] =  int(cmd & 0xFF)
    command[1]= int(limit_data >> 8)
    command[2] = int(limit_data & 0xFF)
    buf=[command[1],command[2]]
    command[3] = int(self.__check_crc(buf))
    self.i2cbus.write_i2c_block_data(self.i2c_addr, reg, command)


  def __write_reg(self, reg, value):
    '''!
      @brief   ?????????
      @param reg ?????
      @param value ?????
    '''
    self.i2cbus.write_byte_data(self.i2c_addr, reg, value)
  

  def __read_reg(self, len):
    '''!
      @brief   ?????????
      @param reg ?????
      @return ?????,list??
    '''
    rslt = self.i2cbus.read_i2c_block_data(self.i2c_addr,0x00,len)
    if(self.measurement_mode == self.Periodic):
      if(self._measure_freq == self.measureFreq_0_5Hz):
        time.sleep(2)
      elif(self._measure_freq == self.measureFreq_1Hz):
        time.sleep(1)
      elif(self._measure_freq == self.measureFreq_2Hz):
        time.sleep(0.5)
      elif(self._measure_freq == self.measureFreq_4Hz):
        time.sleep(0.25)
      elif(self._measure_freq == self.measureFreq_10Hz):
        time.sleep(0.1)
    return rslt

# Inisialisasi sensor SHT3X
SHT3X = DFRobot_SHT3x(iic_addr=0x44, bus=1)

def setup():
    while SHT3X.begin(RST=4) != 0:
        print("The initialization of the chip is failed, please confirm whether the chip connection is correct")
        time.sleep(1)

    if SHT3X.soft_reset() == False:
        print("Failed to reset the chip")

def loop():
    # Membaca suhu dan kelembapan sekali
    print(f"{SHT3X.get_temperature_C():.2f} {SHT3X.get_humidity_RH():.2f}")

if __name__ == "__main__":
    setup()
    loop()  # Hanya baca sekali saja
