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

def load_config(CONFIG, FILENAME):
    import gc
    gc.collect()
    import ujson as json
    gc.collect()

    try:
        with open(FILENAME) as f:
            config = json.loads(f.read())
    except (OSError, ValueError):
        print("Couldn't load " + FILENAME)
        save_config()
    else:
        CONFIG.update(config)
        print("Loaded config from " + FILENAME)

def save_config(CONFIG, FILENAME):
    import ujson as json
    
    try:
        with open(FILENAME, 'w') as f:
            f.write(json.dumps(CONFIG))
        print("Wrote config to " + FILENAME)
    except OSError:
        print("Couldn't save " + FILENAME)

def map_values(x, in_min, in_max, out_min, out_max):
    return (x - in_min)*(out_max - out_min)/(in_max - in_min) + out_min

def readBME280(CONFIG):
    import gc
    gc.collect()

    from machine import Pin, I2C
    gc.collect()
    
    # Configure i2c
    i2c = I2C(scl=Pin(CONFIG['SCL_PIN']), sda=Pin(CONFIG['SDA_PIN']), freq=10000)
    
    try:
        import BME280
        gc.collect()
        bme = BME280.BME280(i2c=i2c)
    except:
        print("ERROR: BME280")
        temperature = -255 # Temperature in celcius
        humidity = -255 # Humidity in % relative humidity
        pressure = -255 # Pressure in Pa
    else:
        [temperature, pressure, humidity] = bme.read_compensated_data()
        temperature /= 100 # Temperature in Celcius
        pressure /= 25600 # Pressure in hPa
        humidity /= 1024 # Humidity in %

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
    gc.collect()

    # Set up ADC conversion
    adc = ADC(CONFIG['MOISTURE_PIN'])

    # Read Sensor and return value as %
    moisture = map_values(adc.read(), CONFIG['MOISTURE_SENSOR_AIR_VALUE'], CONFIG['MOISTURE_SENSOR_WATER_VALUE'], 0, 100)
    if moisture > 100:
        moisture = 100
    elif moisture < 0:
        moisture = 0

    return moisture

def readRainSensor(CONFIG, WATER_CONFIG):
    import gc
    gc.collect()

    #try:
    #    import mcp
    #    io = mcp.MCP23008(0x20, CONFIG['SCL_PIN'], CONFIG['SDA_PIN'])
    #except:
    #    print("ERROR: MCP23008 (Rain Sensor)")
    #    rain = False
    #else:
    #    io.setup(CONFIG['RAIN_SENSOR_IO_EXPANDER_PIN'], mcp.IN)
    #    rain = io.input(CONFIG['RAIN_SENSOR_IO_EXPANDER_PIN']) # Boolean true/false

    from machine import Pin
    gc.collect()
    rainPin = Pin(13, Pin.IN)
    rain = rainPin.value()

    # If it is raining, then store to water_config.json and our variable for smart water sensing
    if rain:
        import utime
        gc.collect()
        WATER_CONFIG['LAST_RAIN'] = utime.mktime(utime.localtime())
        save_config(WATER_CONFIG, 'water_config.json')

    return rain

def set_NTP_Time():
    import gc
    gc.collect()
    import network
    gc.collect()
    import ntptime
    gc.collect()

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
    import gc
    gc.collect()
    from machine import RTC
    gc.collect()
    rtc = RTC()
    (year, month, day, _, hours, minutes, seconds, milliseconds) = rtc.datetime()
    # Time takes the form YYYY-MM-DD'T'HH:MM:SS.MSS
    timestring = "%04d" % year + "-" + "%02d" % month + "-" + "%02d" % day + "T" + "%02d" % hours + ":" + "%02d" % minutes + ":" + "%02d" % seconds + "." + "%03d" % milliseconds

    return timestring

def read_sensors(data, CONFIG, WATER_CONFIG):
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

    print("") # Blank line for neatness
    print("Air Temperature: " + str(data.air_temperature) + "C")
    print("Humidity: " + str(data.humidity) + "%")
    print("Atmospheric Pressure: " + str(data.pressure) + "hPa")
    print("Soil Temperature: " + str(data.soil_temperature) + "C")
    print("Soil Moisture Level: " + str(data.moisture) + "%")

    # Read boolean values
    data.rain = readRainSensor(CONFIG, WATER_CONFIG)
    print("Rain: " + str(data.rain))

    # Get the current time and return in standard format
    data.time = get_time()
    print("Current Time: " + data.time)

    print("Sensor Data Collected.")

def send_over_mqtt(data, CONFIG):
    import gc
    gc.collect()
    from umqtt.simple import MQTTClient
    gc.collect()

    mqtt_client = MQTTClient(CONFIG['UNIQUE_ID'], CONFIG['MQTT_SERVER_IP'])
    try:
        mqtt_client.connect()
    except:
        print("Could not connect to mqtt broker!")
    else:
        mqtt_client.publish(CONFIG['UNIQUE_ID'], "soil_temperature=" + str(data.soil_temperature))
        mqtt_client.publish(CONFIG['UNIQUE_ID'], "soil_moisture=" + str(data.soil_moisture))
        mqtt_client.publish(CONFIG['UNIQUE_ID'], "air_temperature=" + str(data.air_temperature))
        mqtt_client.publish(CONFIG['UNIQUE_ID'], "humidity=" + str(data.humidity))
        mqtt_client.publish(CONFIG['UNIQUE_ID'], "pressure=" + str(data.pressure))
        mqtt_client.publish(CONFIG['UNIQUE_ID'], "rain=" + str(data.rain))
        mqtt_client.publish(CONFIG['UNIQUE_ID'], "time=" + str(data.time))
        mqtt_client.publish(CONFIG['UNIQUE_ID'], "station1_watering=" + str(int(data.station1_watering == 'true')))
        mqtt_client.publish(CONFIG['UNIQUE_ID'], "station2_watering=" + str(int(data.station2_watering == 'true')))
        mqtt_client.publish(CONFIG['UNIQUE_ID'], "station3_watering=" + str(int(data.station3_watering == 'true')))
        mqtt_client.publish(CONFIG['UNIQUE_ID'], "station4_watering=" + str(int(data.station4_watering == 'true')))

        mqtt_client.disconnect()

def sensor_poll_and_transmit(data, CONFIG, WATER_CONFIG):
    read_sensors(data, CONFIG, WATER_CONFIG)
    send_over_mqtt(data, CONFIG)

def check_relays(CONFIG, WATER_CONFIG):
    # First get the date and time
    import gc
    gc.collect()
    import utime
    gc.collect()
    from machine import Pin
    gc.collect()

    # Get the current time and the last time it rained
    current_day = utime.mktime(utime.localtime())/60/60/24
    last_rain = WATER_CONFIG['LAST_RAIN']/60/60/24

    try:
        import mcp
        io = mcp.MCP23008(0x20, CONFIG['SCL_PIN'], CONFIG['SDA_PIN'])
    except:
        print("ERROR: MCP23008 (Relays)")
    #    return
    #else:
        # Set up our outputs
        LED_BUILTIN = Pin(2, Pin.OUT)
        LED_BUILTIN.value(1)

        pins = (CONFIG['RELAY_1_IO_EXPANDER_PIN'], CONFIG['RELAY_2_IO_EXPANDER_PIN'], CONFIG['RELAY_3_IO_EXPANDER_PIN'], CONFIG['RELAY_4_IO_EXPANDER_PIN'])
        for pin in pins:
            try:
                io.setup(pin, mcp.OUT)
            except:
                pass
        
        # If we've had rain then set all outputs to low
        if current_day - last_rain < WATER_CONFIG['RAIN_LOOKBACK']:
            print("Rain in past " + str(WATER_CONFIG['RAIN_LOOKBACK']) + " days, skipping watering...")
            for pin in pins:
                try:
                    io.output(pin, False)
                except:
                    pass
            return

        # Get the current time (in UTC number of seconds)
        now = utime.mktime(utime.localtime())

        # Apply time-zone correction
        now = now + CONFIG['TIMEZONE']*60*60

        # Extract the weekday
        (_, _, _, _, _, _, weekday, _) = utime.localtime(now)

        # Get the relevant watering information
        if weekday == 0:
            start_time = WATER_CONFIG['MON_START']
            duration = WATER_CONFIG['MON_DURATION']
            water = WATER_CONFIG['MON_WATER']
        elif weekday == 1:
            start_time = WATER_CONFIG['TUE_START']
            duration = WATER_CONFIG['TUE_DURATION']
            water = WATER_CONFIG['TUE_WATER']
        elif weekday == 2:
            start_time = WATER_CONFIG['WED_START']
            duration = WATER_CONFIG['WED_DURATION']
            water = WATER_CONFIG['WED_WATER']
        elif weekday == 3:
            start_time = WATER_CONFIG['THU_START']
            duration = WATER_CONFIG['THU_DURATION']
            water = WATER_CONFIG['THU_WATER']
        elif weekday == 4:
            start_time = WATER_CONFIG['FRI_START']
            duration = WATER_CONFIG['FRI_DURATION']
            water = WATER_CONFIG['FRI_WATER']
        elif weekday == 5:
            start_time = WATER_CONFIG['FRI_START']
            duration = WATER_CONFIG['FRI_DURATION']
            water = WATER_CONFIG['FRI_WATER']
        elif weekday == 6:
            start_time = WATER_CONFIG['FRI_START']
            duration = WATER_CONFIG['FRI_DURATION']
            water = WATER_CONFIG['FRI_WATER']
        
        duration_secs = duration*60

        # Extract the time using conversion
        (_, _, _, hour, minute, second, weekday, _) = utime.localtime(now)

        # Convert to a known number of seconds against a reference point
        now_ref = utime.mktime((2000, 0, 0, hour, minute, second, 0, 0))

        # Find the programmed time relative to the same reference point
        water_start_time = utime.mktime((2000, 0, 0, int(start_time), int(start_time*60)%60, 0, 0, 0))

        # Next check if we need to activate the relays. There are 7 days that we need to check
        for pin in pins:
            
            if (water == True) & (now_ref > water_start_time) & (now_ref < (water_start_time + duration_secs)):
                print("Watering station # " + str(pin))
                LED_BUILTIN.value(0)
                try:
                    io.output(pin, True)
                except:
                    pass
            else:
                LED_BUILTIN.value(1)
                try:
                    io.output(pin, False)
                except:
                    pass
            
            # Apply a funky offset that basically runs through the stations in sequence
            water_start_time = water_start_time + duration_secs
        return