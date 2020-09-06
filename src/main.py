#-----------------------#
# Main CITS5506
# Written by D. Sanders
#-----------------------#

# Imports
from functionlib import *
import machine
from machine import Timer
import wifimgr
import ubinascii
#import umqttsimple
try:
    import usocket as socket
except:
    import socket

# Config stuff
# These defaults are overwritten with the contents of config.json by load_config()
CONFIG = {
    "LED_BUILTIN": 2,
    "SDA_PIN": 5,
    "SCL_PIN": 4,
    "ONEWIRE_PIN": 0,
    "MOISTURE_PIN": 0,
    "MOISTURE_SENSOR_AIR_VALUE": 620,
    "MOISTURE_SENSOR_WATER_VALUE": 310,
    "RAIN_SENSOR_IO_EXPANDER_PIN": 0,
    "RELAY_1_IO_EXPANDER_PIN": 1,
    "RELAY_2_IO_EXPANDER_PIN": 2,
    "RELAY_3_IO_EXPANDER_PIN": 3,
    "RELAY_4_IO_EXPANDER_PIN": 4,
    "SAMPLE_PERIOD_S": 10,
    "SAMPLES_TO_BE_AVERAGED": 10,
    "unique_id": ubinascii.hexlify(machine.unique_id()),
    "client_name": b"SWSWTR_"+ubinascii.hexlify(machine.unique_id()).decode('utf-8'),
    "topic": b"home"
}

save_config(CONFIG) # Save config for now

load_config(CONFIG) # Load config, revert to default values if unable

data = Data() # Create object data from class Data

wlan = wifimgr.get_connection()
if wlan is None:
      print("Could not initialise the network connection.")
      while True:
        pass # You shall not pass :D

try:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      s.bind(('', 80))
      s.listen(5)
except OSError as e:
      machine.reset()

# Initial NTP Server stuff
set_NTP_Time()

# Initialise Timer(s)
tim1 = Timer(-1)
tim2 = Timer(-1)

tim1.init(period=60000, mode=Timer.PERIODIC, callback=lambda t:set_NTP_Time()) # Periodic update of NTP server every minute
tim2.init(period=CONFIG['SAMPLE_PERIOD_S']*1000, mode=Timer.PERIODIC, callback=lambda t:sensor_poll_and_transmit(data, CONFIG)) # Periodic sensor reading and data transmission