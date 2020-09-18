#-----------------------#
# Main CITS5506
# Written by D. Sanders
#-----------------------#

# Imports
import gc
gc.collect()
from functionlib import *
gc.collect()
import utime
gc.collect()
import machine
gc.collect()
from machine import Timer
gc.collect()
import wifimgr
gc.collect()
import network
gc.collect()
import ubinascii
gc.collect()
try:
    import usocket as socket
except:
    import socket
gc.collect()
from time import sleep
gc.collect()

# Config dictionary
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
    "SAMPLE_PERIOD_S": 30,
    "SAMPLES_TO_BE_AVERAGED": 10,
    "RAIN_LOOKBACK": 3,
    #"UNIQUE_ID": ubinascii.hexlify(machine.unique_id()),
    "UNIQUE_ID": 3,
    "CLIENT_NAME": b"SWSWTR_"+ubinascii.hexlify(machine.unique_id()).decode('utf-8'),
    "USERNAME": b"admin@sws.net.au",
    #"MQTT_SERVER_IP": b"192.168.1.83",
    "HTTP_SERVER_IP": b"192.168.1.83",
    "HTTP_PORT": 4000,
    "TEMP_AP_SSID": b"SWSWTR",
    #"SSID": b"SWSWTR-AP",
    #"PASSKEY": b"123456789"
    "SSID": b"Dave & Jess",
    "PASSKEY": b"January18",
    "TIMEZONE": 8
}

WATER_CONFIG = {
    "LAST_RAIN": 0,
    "RAIN_LOOKBACK": 3,
    "MON_START": 6,
    "MON_DURATION": 10,
    "MON_WATER": True,
    "TUE_START": 6,
    "TUE_DURATION": 10,
    "TUE_WATER": True,
    "WED_START": 6,
    "WED_DURATION": 10,
    "WED_WATER": True,
    "THU_START": 6,
    "THU_DURATION": 10,
    "THU_WATER": True,
    "FRI_START": 15.5,
    "FRI_DURATION": 10,
    "FRI_WATER": True,
    "SAT_START": 6,
    "SAT_DURATION": 10,
    "SAT_WATER": True,
    "SUN_START": 6,
    "SUN_DURATION": 10,
    "SUN_WATER": True,
}

save_config(CONFIG, 'config.json') # Save config for now
save_config(WATER_CONFIG, 'water_config.json') # Save config for now

load_config(CONFIG, 'config.json') # Load config, revert to default values if unable
load_config(WATER_CONFIG, 'water_config.json') # Save config for now

data = Data() # Create object data from class Data

# Set up output pins

# First try to connect to the previously stored WiFi network
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
if not sta_if.isconnected():
    print('Connecting to network...')
    try:
        sta_if.connect(CONFIG['SSID'],CONFIG['PASSKEY'])
    except:
        wlan = wifimgr.get_connection()
        if wlan is None:
            print("Could not initialise the network connection.")
            while True:
                pass # You shall not pass :D

        # If we can't connect to WiFi then set up an AP and listen at 192.168.4.1:80
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', 80))
            s.listen(5)
        except OSError as e:
            pass

# Once we get to here, we have connected to a network.
# Disable the AP interface
network.WLAN(network.AP_IF).active(False)

while network.WLAN(network.STA_IF).isconnected() == False:
    pass
if network.WLAN(network.STA_IF).isconnected():
    print("Connected to network!")

# Initial NTP Server stuff
set_NTP_Time()

# Initialise Timer(s)
tim1 = Timer(-1)
tim2 = Timer(-1)
tim3 = Timer(-1)

tim1.init(period=60000, mode=Timer.PERIODIC, callback=lambda t:set_NTP_Time()) # Periodic update of NTP server every minute
tim2.init(period=CONFIG['SAMPLE_PERIOD_S']*1000, mode=Timer.PERIODIC, callback=lambda t:sensor_poll_and_transmit(data, CONFIG, WATER_CONFIG)) # Periodic sensor reading and data transmission
tim3.init(period=1000, mode=Timer.PERIODIC, callback = lambda t:check_relays(CONFIG, WATER_CONFIG)) # Periodic checking of our relays