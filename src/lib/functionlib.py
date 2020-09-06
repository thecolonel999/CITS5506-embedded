# Library of functions for reading sensors and the like
# Makes main.py nice and tidy

def readBME280():
    from machine import Pin, I2C
    import BME280

    i2c = I2C(scl=Pin(5), sda=Pin(4), freq=10000)

    bme = BME280.BME280(i2c=i2c)
    temperature = bme.temperature # Temperature in celcius
    humidity = bme.humidity # Humidity in % relative humidity
    pressure = bme.pressure # Pressure in Pa

    temperature = 30 # Temperature in celcius
    humidity = 60 # Humidity in % relative humidity
    pressure = 100000 # Pressure in Pa

    return temperature, humidity, pressure

def readDS18B20():
    # Note this function assumes only 1 temp sensor is attached via one-wire
    import machine, onewire, ds18x20
    ds_pin = machine.Pin(4)
    #ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))

    #rom = ds_sensor.scan() # Scan for the sensor attached via one-wire

    #ds_sensor.convert_temp()
    #soilTemperature = ds_sensor.read_temp(rom)
    soilTemperature = 40
    
    return soilTemperature