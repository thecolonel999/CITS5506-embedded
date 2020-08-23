# Main loop for CITS5506
# Written by D. Sanders

from functionlib import readBME280, readDS18B20

[temperature, humidity, pressure] = readBME280() # Get the temp, hum and pres values

soilTemperature = readDS18B20() # Get the soil temperature

print(temperature)
print(humidity)
print(pressure)
print(soilTemperature)