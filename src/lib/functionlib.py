# Library of functions for reading sensors and the like
# Makes main.py nice and tidy

# Class for storing our data, initialise all lists as empty
class Data:
    def __init__(self, empty_list = 0):
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
    from time import sleep_ms
    gc.collect()

    # Note this function assumes only 1 temp sensor is attached via one-wire
    import machine, onewire, ds18x20

    ds_sensor = ds18x20.DS18X20(onewire.OneWire(machine.Pin(CONFIG['ONEWIRE_PIN'])))
    rom = ds_sensor.scan() # Scan for the sensor attached via one-wire

    try:
        ds_sensor.convert_temp()
        sleep_ms(250)
    except:
        print("ERROR: DS18B20 OneWire")
        soilTemperature = -255 # Temperature in celcius
    else:
        soilTemperature = ds_sensor.read_temp(rom[0])
    
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

        moisture += readMoistureSensor(CONFIG)
    
    # Now store the average value
    data.soil_temperature = soil_temperature/samples
    data.air_temperature = air_temperature/samples
    data.humidity = humidity/samples
    data.pressure = pressure/samples
    data.soil_moisture = moisture/samples

    # Now read our soil moisture sensor
    data.soil_temperature = readDS18B20(CONFIG)

    print("") # Blank line for neatness
    print("Air Temperature: " + str(data.air_temperature) + "C")
    print("Humidity: " + str(data.humidity) + "%")
    print("Atmospheric Pressure: " + str(data.pressure) + "hPa")
    print("Soil Temperature: " + str(data.soil_temperature) + "C")
    print("Soil Moisture Level: " + str(data.soil_moisture) + "%")

    # Read boolean values
    data.rain = readRainSensor(CONFIG, WATER_CONFIG)
    print("Rain: " + str(data.rain))

    # Get the current time and return in standard format
    data.time = get_time()
    print("Current Time: " + data.time)

    print("Sensor Data Collected.")

def send_over_http(data, CONFIG):
    import gc
    gc.collect()
    import urequests
    gc.collect()

    # Create our base url string
    baseurl = "http://" + str(CONFIG['HTTP_SERVER_IP'], 'utf-8') + ":" + str(CONFIG['HTTP_PORT']) + "/device/?userid=" + str(CONFIG['USERNAME'], 'utf-8') + "&device_id=" + str(CONFIG['UNIQUE_ID']) + "&token=" + str(CONFIG['TOKEN']).replace('+','%2B') + "&timestamp=" + str(data.time)
    
    # Now send our packets of data
    # First create an array of subsequent urls
    urls = [
        "&type=temperature&value=" + str(data.air_temperature),
        "&type=pressure&value=" + str(data.pressure),
        "&type=humidity&value=" + str(data.humidity),
        "&type=soil%20temp&value=" + str(data.soil_temperature),
        "&type=soil%20moisture%20level&value=" + str(data.soil_moisture),
        "&type=rain%20sensing&value=" + str(data.rain)
    ]

    print(baseurl + urls[0])

    gc.collect()

    # Iterate to send our data packets
    for url in urls:
        try:
            response = urequests.post(baseurl + url)
        except:
            print("Unable to complete HTTP POST request!")
            pass
        else:
            response.close()
        gc.collect()
    
    # Now send our data packet for watering
    baseurl = "http://" + str(CONFIG['HTTP_SERVER_IP'], 'utf-8') + ":" + str(CONFIG['HTTP_PORT']) + "/device/watering/?userid=" + str(CONFIG['USERNAME'], 'utf-8') + "&device_id=" + str(CONFIG['UNIQUE_ID']) + "&token=" + str(CONFIG['TOKEN']).replace('+','%2B') + "&timestamp=" + str(data.time)
    url = "&relay_output_1=" + str(int(data.station1_watering == True)) + "&relay_output_2=" + str(int(data.station2_watering == True)) + "&relay_output_3=" + str(int(data.station3_watering == True)) + "&relay_output_4=" + str(int(data.station4_watering == True))

    print(baseurl + url)

    try:
        response = urequests.post(baseurl + url)
    except:
        print("Unable to complete HTTP POST request!")
        pass
    else:
        response.close()
    gc.collect()
    

def sensor_poll_and_transmit(data, CONFIG, WATER_CONFIG):
    read_sensors(data, CONFIG, WATER_CONFIG)
    #send_over_mqtt(data, CONFIG)
    send_over_http(data, CONFIG)

def check_relays(data, CONFIG, WATER_CONFIG):
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
        
        # If we've had rain OR our soil moisture is high then set all outputs to low
        if current_day - last_rain < WATER_CONFIG['RAIN_LOOKBACK'] or data.soil_moisture < WATER_CONFIG['SOIL_MOISTURE_THRESHOLD_PERCENT']:
            print("Rain in past " + str(WATER_CONFIG['RAIN_LOOKBACK']) + " days, skipping watering...")
            print("Soil Moisture Level is " + str(data.soil_moisture) + "%")
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
            start_time = WATER_CONFIG['SAT_START']
            duration = WATER_CONFIG['SAT_DURATION']
            water = WATER_CONFIG['SAT_WATER']
        elif weekday == 6:
            start_time = WATER_CONFIG['SUN_START']
            duration = WATER_CONFIG['SUN_DURATION']
            water = WATER_CONFIG['SUN_WATER']
        
        duration_secs = duration*60

        # Extract the time using conversion
        (_, _, _, hour, minute, second, weekday, _) = utime.localtime(now)

        # Convert to a known number of seconds against a reference point
        now_ref = utime.mktime((2000, 0, 0, hour, minute, second, 0, 0))

        # Find the programmed time relative to the same reference point
        water_start_time = utime.mktime((2000, 0, 0, int(start_time), int(start_time*60)%60 + 1, 0, 0, 0))

        # Next check if we need to activate the relays. There are 7 days that we need to check
        i = 0
        for pin in pins:
            i = i + 1
            if (water == True) & (now_ref > water_start_time) & (now_ref < (water_start_time + duration_secs)):
                print("Watering station # " + str(pin))
                LED_BUILTIN.value(0)
                if i == 1:
                    data.station1_watering = True
                elif i == 2:
                    data.station2_watering = True
                elif i == 3:
                    data.station3_watering = True
                elif i == 4:
                    data.station4_watering = True
                try:
                    io.output(pin, True)
                except:
                    pass
            else:
                LED_BUILTIN.value(1)
                if i == 1:
                    data.station1_watering = False
                elif i == 2:
                    data.station2_watering = False
                elif i == 3:
                    data.station3_watering = False
                elif i == 4:
                    data.station4_watering = False
                try:
                    io.output(pin, False)
                except:
                    pass
            
            # Apply a funky offset that basically runs through the stations in sequence
            water_start_time = water_start_time + duration_secs
        return

def display_OLED(oled, data, CONFIG):
    # Start with blank screen
    oled.fill(0)

    # First make sure we show the local time in the first row
    import gc
    gc.collect()
    import utime
    gc.collect()
    
    now = utime.mktime(utime.localtime()) # Get the current time (in UTC number of seconds)
    now = now + CONFIG['TIMEZONE']*60*60 # Apply time-zone correction
    (year, month, day, hour, minute, second, _, _) = utime.localtime(now) # Extract the time

    #oled.text(str(hour) + ':' + str(minute) + ':' + str(second), 30, 0)
    oled.text('%02d:%02d:%02d' % (hour, minute, second), 30, 0)

    # Now work out which screen we should display
    s_remainder = int(now % (CONFIG['OLED_CYCLE_S']*CONFIG['OLED_NUMBER_OF_SCREENS']))
    counter = int(s_remainder/CONFIG['OLED_CYCLE_S'])

    # Next check our cases and respond accordingly
    if counter == 0: # First screen shows Air conditions
        oled.text('T: %.2fC' % data.air_temperature, 0, 16)
        oled.text('H: %.2f%%' % data.humidity, 0, 32)
        oled.text('P: %.1fhPa' % data.pressure, 0, 48)

    elif counter == 1: # Second screen shows soil conditions
        oled.text('Soil T: %.2fC' % data.soil_temperature, 0, 16)
        oled.text('Moist:  %.2f%%' % data.soil_moisture, 0, 32)
        if data.rain == 1:
            buf = 'True'
        else:
            buf = 'False'
        oled.text('Rain:   ' + buf, 0, 48)
    
    elif counter == 2: # Third screen shows watering data
        if data.station1_watering == True or data.station2_watering == True or data.station3_watering == True or data.station4_watering == True:
            oled.text('Watering: True', 0, 16)
            if data.station1_watering == True:
                oled.text('Station:  1', 0, 32)
            elif data.station2_watering == True:
                oled.text('Station:  2', 0, 32)
            elif data.station3_watering == True:
                oled.text('Station:  3', 0, 32)
            elif data.station4_watering == True:
                oled.text('Station:  4', 0, 32)
        else:
            oled.text('Watering: False', 0, 16)
    
    elif counter == 3: # Fourth screen shows key network info
        import gc
        gc.collect()
        import network
        gc.collect()

        (IP, _, _, _) = network.WLAN(network.STA_IF).ifconfig()

        oled.text(str(CONFIG['SSID']), 0, 16)
        oled.text(str(IP), 0, 32)
        oled.text('%02d/%02d/%04d' % (day, month, year), 0, 48)
    
    # Finally, push the update to our display
    oled.show()