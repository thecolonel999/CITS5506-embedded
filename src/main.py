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
import ssd1306
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
    "MON_START": 13.1666666,
    "MON_DURATION": 1,
    "MON_WATER": True,
    "TUE_START": 13.1666666,
    "TUE_DURATION": 1,
    "TUE_WATER": True,
    "WED_START": 13.1666666,
    "WED_DURATION": 1,
    "WED_WATER": True,
    "THU_START": 13.1666666,
    "THU_DURATION": 1,
    "THU_WATER": True,
    "FRI_START": 13.1666666,
    "FRI_DURATION": 1,
    "FRI_WATER": True,
    "SAT_START": 13.1666666,
    "SAT_DURATION": 1,
    "SAT_WATER": True,
    "SUN_START": 13.5333333,
    "SUN_DURATION": 1,
    "SUN_WATER": True,
}

save_config(CONFIG, 'config.json') # Save config for now
save_config(WATER_CONFIG, 'water_config.json') # Save config for now

load_config(CONFIG, 'config.json') # Load config, revert to default values if unable
load_config(WATER_CONFIG, 'water_config.json') # Save config for now

data = Data() # Create object data from class Data

# Set up OLED display
i2c = machine.I2C(scl=machine.Pin(CONFIG['SCL_PIN']), sda=machine.Pin(CONFIG['SDA_PIN']))
oled = ssd1306.SSD1306_I2C(128,64, i2c)
oled.fill(0) # Start with blank screen
oled.text('SWSWTR', 40, 0)
oled.show()

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
oled.text('CONNECTING TO:', 0, 16)
oled.text(CONFIG['SSID'], 0, 32)
oled.show()

while network.WLAN(network.STA_IF).isconnected() == False:
    pass
if network.WLAN(network.STA_IF).isconnected():
    print("Connected to network!")

# Initial NTP Server stuff
set_NTP_Time()

# Initial reading of sensors (consider this our 'initial conditions')
sensor_poll_and_transmit(data, CONFIG, WATER_CONFIG)

# Initialise Timer(s)
tim1 = Timer(-1) # for NTP server updating
gc.collect()
tim2 = Timer(-1) # for data collection
gc.collect()
tim3 = Timer(-1) # for data transmittal over MQTT
gc.collect()
tim4 = Timer(-1) # for updating our display
gc.collect()

# Periodic update of NTP server every minute
tim1.init(period=60000, mode=Timer.PERIODIC, callback=lambda t:set_NTP_Time())
gc.collect()

# Periodic sensor reading and data transmission
tim2.init(period=CONFIG['SAMPLE_PERIOD_S']*1000, mode=Timer.PERIODIC, callback=lambda t:sensor_poll_and_transmit(data, CONFIG, WATER_CONFIG))
gc.collect()

# Periodic checking of our relays
tim3.init(period=1000, mode=Timer.PERIODIC, callback = lambda t:check_relays(data, CONFIG, WATER_CONFIG))
gc.collect()

# Counter flag for cycling automatically through our various displays
# We have 4 displays that we want to cycle through:
# 1. Show Air Temp, Humidity, Pressure
# 2. Show Soil Temp, Soil Moisture and Rainfall
# 3. Show if a watering station is active
# 4. Show network SSID, IP Address and current date

# Periodic updating of our display
tim4.init(period=int(1000/(CONFIG['OLED_FPS'])), mode=Timer.PERIODIC, callback=lambda t:display_OLED(oled, data, CONFIG))
gc.collect()