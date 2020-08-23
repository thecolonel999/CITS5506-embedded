# Main loop for CITS5506
# Written by D. Sanders

# IMPORTS
from functionlib import readBME280, readDS18B20
from machine import Pin, ADC, RTC, Timer, WDT
import time
import ntptime

[temperature, humidity, pressure] = readBME280() # Get the temp, hum and pres values

soilTemperature = readDS18B20() # Get the soil temperature

print(temperature)
print(humidity)
print(pressure)
print(soilTemperature)