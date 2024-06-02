from machine import Pin, Timer, ADC, PWM, I2C
from ssd1306 import SSD1306_I2C
import framebuf
import utime
import network
import secrets
import time
import urequests
from dht import DHT11
import micropython

onboard_led = Pin('LED')

def connect():
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(secrets.SSID, secrets.PASSWORD)
    while wlan.isconnected() == False:
        onboard_led.on()
        print('Waiting for connection...')
        utime.sleep(0.5)
        onboard_led.off()
        utime.sleep(0.5)
    onboard_led.on()
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')

try:
    connect()
except KeyboardInterrupt:
    machine.reset()



red = Pin(15, Pin.OUT)

red.off()

t_sensor = DHT11(Pin(5))



soil_sensors = [
    {
        "port": ADC(Pin(26)),
        "soil_min": 17600,
        "soil_max": 43000
    },
    {
        "port": ADC(Pin(27)),
        "soil_min": 25000,
        "soil_max": 44500
    }
]

data = {
        "soil_sensors": {
                0: None,
                1: None,
                2: None,
                3: None
            },
        "outside_sensors": {
                "temperature": None,
                "humidity": None
            }
    }

 
i2c=I2C(0,sda=Pin(0), scl=Pin(1), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

thermometer_ba = bytearray(b'\x00\x00\x00\x00\x00\x00\x00<\x00\x00f\x00\x00B\xe0\x00B\x00\x00B\x00\x00B\xe0\x00B\x00\x00B\x00\x00B\xe0\x00B\x00\x00B\x00\x00B\xe0\x00B\x00\x00\xc3\x00\x00\x81\x00\x00\x81\x00\x00\x81\x00\x00\x81\x00\x00\xc3\x00\x00~\x00\x00\x00\x00\x00\x00\x00'
)
thermometer_fb = framebuf.FrameBuffer(thermometer_ba,24,24, framebuf.MONO_HLSB)

tear_ba = bytearray(b'\x00\x10\x00\x00\x18\x00\x00\x18\x00\x00<\x00\x00,\x00\x00$\x00\x00f\x00\x00\xc3\x00\x00\x81\x00\x01\x81\x80\x03\x00\xc0\x06\x00`\x04\x00`\x04\x00 \x0c\x000\x04\x00 \x0c\x000\x08\x00 \x04\x00 \x06\x00`\x06\x00@\x03\x01\xc0\x01\xef\x00\x00|\x00')
tear_fb = framebuf.FrameBuffer(tear_ba,24,38, framebuf.MONO_HLSB)

sensors_position = [66, 80, 94, 108]
sensors_labels = ['A', 'B', 'C', 'D']


def displayBaseImage():
    oled.fill(0)
    
    oled.text('OUTSIDE', 0, 3)
    oled.blit(thermometer_fb,0,12)
    oled.blit(tear_fb, 0, 40)
    
    oled.vline(58, 0, 64, 1)
    
    oled.text('SENSORS', 65, 3)
    
    for index, position in enumerate(sensors_position):
        oled.rect(position, 13, 10, 42, 1)
        oled.text(sensors_labels[index], position, 57)
    
def calculateBarFill(smax, smin, percents):
    return smax - (((100 - percents) * (smax - smin)) / 100)

def sendData(data):
    response = urequests.put('https://smart-garden-34ae2-default-rtdb.europe-west1.firebasedatabase.app/rt_sensors.json', json=data)
    response.close()

while True:
    
    displayBaseImage()
    
    for index, sensor in enumerate(soil_sensors):
        soil = sensor["port"].read_u16()
        
        #print(f'{index}: {soil}')
        
        percent_soil = (sensor["soil_max"] - soil) * 100 / (sensor["soil_max"] - sensor["soil_min"])
        bar_position = int(calculateBarFill(13, 55, percent_soil))
        bar_fill = 42 - (bar_position - 13)
        
        if percent_soil < 0:
            oled.fill_rect(sensors_position[index], bar_position, 0, bar_fill, 1)
        else:
            oled.fill_rect(sensors_position[index], bar_position, 10, bar_fill, 1)
            data["soil_sensors"][index] = percent_soil
    try:   
        t_sensor.measure()
        t_sensor_temperature = t_sensor.temperature()
        t_sensor_humidity = t_sensor.humidity()
        oled.text(f'{t_sensor_temperature}C', 28, 18)
        oled.text(f'{t_sensor_humidity}%', 28, 46)
        data["outside_sensors"]["temperature"] = t_sensor_temperature
        data["outside_sensors"]["humidity"] = t_sensor_humidity
            
    except OSError as e:
        oled.text('err!', 28, 18)
        oled.text('err!', 28, 46)
    
    oled.show()
    sendData(data)
    
    print(data)
    print(micropython.mem_info())
    utime.sleep(5)
    
        
        
        

    

