# Library of functions for reading sensors and the like
# Makes main.py nice and tidy

# Class for storing our data, initialise all lists as empty
class Data:
    def __init__(self, empty_list = []):
        self.soil_temperature = empty_list
        self.soil_moisture = empty_list
        self.air_temperature = empty_list
        self.humidity = empty_list
        self.pressure = empty_list
        self.rain = empty_list
        self.time = empty_list
        self.station1_watering = empty_list
        self.station2_watering = empty_list
        self.station3_watering = empty_list
        self.station4_watering = empty_list

def load_config(CONFIG):
    import ujson as json
    
    try:
        with open('config.json') as f:
            config = json.loads(f.read())
    except (OSError, ValueError):
        print("Couldn't load config.json")
        save_config()
    else:
        CONFIG.update(config)
        print("Loaded config from config.json")

def save_config(CONFIG):
    import ujson as json
    
    try:
        with open('config.json', 'w') as f:
            f.write(json.dumps(CONFIG))
        print("Wrote config to config.json")
    except OSError:
        print("Couldn't save config.json")

def map_values(x, in_min, in_max, out_min, out_max):
    return (x - in_min)*(out_max - out_min)/(in_max - in_min) + out_min

def readBME280(CONFIG):
    import gc
    gc.collect()

    from machine import Pin, I2C
    
    i2c = I2C(scl=Pin(CONFIG['SCL_PIN']), sda=Pin(CONFIG['SDA_PIN']), freq=10000)
    
    try:
        import BME280
        bme = BME280.BME280(i2c=i2c)
    except:
        print("ERROR: BME280")
        temperature = -255 # Temperature in celcius
        humidity = -255 # Humidity in % relative humidity
        pressure = -255 # Pressure in Pa
    else:
        temperature = bme.temperature # Temperature in celcius
        humidity = bme.humidity # Humidity in % relative humidity
        pressure = bme.pressure # Pressure in Pa

    return [temperature, humidity, pressure]

def readDS18B20(CONFIG):
    import gc
    gc.collect()

    # Note this function assumes only 1 temp sensor is attached via one-wire
    import machine, onewire, ds18x20

    ds_sensor = ds18x20.DS18X20(onewire.OneWire(machine.Pin(CONFIG['ONEWIRE_PIN'])))
    rom = ds_sensor.scan() # Scan for the sensor attached via one-wire

    try:
        ds_sensor.convert_temp()
    except:
        print("ERROR: DS18B20 OneWire")
        soilTemperature = -255 # Temperature in celcius
    else:
        soilTemperature = ds_sensor.read_temp(rom)
    
    return soilTemperature

def readMoistureSensor(CONFIG):
    import gc
    gc.collect()

    from machine import ADC

    # Set up ADC conversion
    adc = ADC(CONFIG['MOISTURE_PIN'])

    # Read Sensor and return value as %
    moisture = map_values(adc.read(), CONFIG['MOISTURE_SENSOR_AIR_VALUE'], CONFIG['MOISTURE_SENSOR_WATER_VALUE'], 0, 100)
    if moisture > 100:
        moisture = 100
    elif moisture < 0:
        moisture = 0

    return moisture

def readRainSensor(CONFIG):
    import gc
    gc.collect()

    try:
        import mcp
        io = mcp.MCP23008(0x20, CONFIG['SCL_PIN'], CONFIG['SDA_PIN'])
    except:
        print("ERROR: MCP23008 (Rain Sensor)")
        rain = False
    else:
        io.setup(CONFIG['RAIN_SENSOR_IO_EXPANDER_PIN'], mcp.IN)
        rain = io.input(CONFIG['RAIN_SENSOR_IO_EXPANDER_PIN']) # Boolean true/false
    return rain

def set_NTP_Time():
    import gc
    gc.collect()

    import network, ntptime
    sta_if = network.WLAN(network.STA_IF)
    if sta_if.isconnected():
        from machine import RTC
        rtc = RTC()
        try:
            ntptime.settime()
        except OSError:
            print("ERROR: Unable to update RTC")
        else:
            print("RTC updated from NTP server.")

def get_time():
    from machine import RTC
    rtc = RTC()
    (year, month, day, _, hours, minutes, seconds, milliseconds) = rtc.datetime()
    # Time takes the form YYYY-MM-DD'T'HH:MM:SS.MSS
    timestring = "%04d" % year + "-" + "%02d" % month + "-" + "%02d" % day + "T" + "%02d" % hours + ":" + "%02d" % minutes + ":" + "%02d" % seconds + "." + "%03d" % milliseconds

    return timestring

def read_sensors(data, CONFIG):
    import gc
    gc.collect()

    samples = CONFIG['SAMPLES_TO_BE_AVERAGED']

    air_temperature = humidity = pressure = soil_temperature = moisture = 0

    # Read our sensors multiple times
    for i in range(0,samples):
        [t, h, p] = readBME280(CONFIG)
        air_temperature += t
        humidity += h
        pressure += p

        soil_temperature += readDS18B20(CONFIG)
        moisture += readMoistureSensor(CONFIG)
    
    # Now store the average value
    data.soil_temperature = soil_temperature/samples
    data.air_temperature = air_temperature/samples
    data.humidity = humidity/samples
    data.pressure = pressure/samples
    data.moisture = moisture/samples

    # Read boolean values
    data.rain = readRainSensor(CONFIG)

    # Get the current time and return in standard format
    data.time = get_time()

    print("Sensor Data Collected.")

def send_over_mqtt(data, CONFIG):
    from umqtt.simple import MQTTClient
    import gc
    gc.collect()

    client = MQTTClient(CONFIG['unique_id'], CONFIG['mqtt_server_ip'])
    try:
        client.connect()
    except:
        print("Could not connect to mqtt broker!")
    else:
        mqtt_client.publish(CONFIG['unique_id'] + "_soil_temperature", data.soil_temperature)
        mqtt_client.publish(CONFIG['unique_id'] + "_soil_moisture", data.soil_moisture)
        mqtt_client.publish(CONFIG['unique_id'] + "_air_temperature", data.air_temperature)
        mqtt_client.publish(CONFIG['unique_id'] + "_humidity", data.humidity)
        mqtt_client.publish(CONFIG['unique_id'] + "_pressure", data.pressure)
        mqtt_client.publish(CONFIG['unique_id'] + "_rain", int(data.rain == 'true')
        mqtt_client.publish(CONFIG['unique_id'] + "_time", data.time)
        mqtt_client.publish(CONFIG['unique_id'] + "_station1_watering", int(data.station1_watering == 'true'))
        mqtt_client.publish(CONFIG['unique_id'] + "_station2_watering", int(data.station2_watering == 'true'))
        mqtt_client.publish(CONFIG['unique_id'] + "_station3_watering", int(data.station3_watering == 'true'))
        mqtt_client.publish(CONFIG['unique_id'] + "_station4_watering", int(data.station4_watering == 'true'))

        client.disconnect()

def sensor_poll_and_transmit(data, CONFIG):
    read_sensors(data, CONFIG)
    send_over_mqtt(data, CONFIG)