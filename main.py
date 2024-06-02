from machine import Pin, PWM, ADC, I2C
import time
from lib.neopixel import Neopixel
from dht import DHT11
from ssd1306 import SSD1306_I2C
import framebuf

onboard_led = Pin('LED')


def run_pump():
    pwm = PWM(Pin(26))
    pwm.freq(200)
    pwm.duty_u16(45000)
    time.sleep(8)
    pwm.duty_u16(0)
    
def run_led_strip():
    numpix = 8
    strip = Neopixel(numpix, 0, 6, "RGB")
    red = (255, 0, 0)
    orange = (255, 50, 0)
    yellow = (255, 100, 0)
    green = (0, 255, 0)
    blue = (0, 0, 255)
    indigo = (100, 0, 90)
    violet = (200, 0, 100)
    colors_rgb = [red, orange, yellow, green, blue, indigo, violet]

    # same colors as normaln rgb, just 0 added at the end
    colors_rgbw = [color+tuple([0]) for color in colors_rgb]
    colors_rgbw.append((0, 0, 0, 255))

    # uncomment colors_rgbw if you have RGBW strip
    colors = colors_rgb
    # colors = colors_rgbw


    step = round(numpix / len(colors))
    current_pixel = 0
    strip.brightness(50)

    for color1, color2 in zip(colors, colors[1:]):
        strip.set_pixel_line_gradient(current_pixel, current_pixel + step, color1, color2)
        current_pixel += step

    strip.set_pixel_line_gradient(current_pixel, numpix - 1, violet, red)

    for x in range(100):
        strip.rotate_right(1)
        time.sleep(0.042)
        strip.show()
    strip.fill((0,0,0))
    strip.show()
    
def read_dht():
    t_sensor = DHT11(Pin(5))
    for x in range(3):
        t_sensor.measure()
        t_sensor_temperature = t_sensor.temperature()
        t_sensor_humidity = t_sensor.humidity()
        print(f'Room Temperature: {t_sensor_temperature}C')
        print(f'Room Humidity: {t_sensor_humidity}%')
        time.sleep(1)
        
def read_soil_sensor():
    sensor = {
        "port": ADC(Pin(27)),
        "soil_min": 18600,
        "soil_max": 43000
    }
    for x in range(3):     
        soil = sensor["port"].read_u16()
        percent_soil = (sensor["soil_max"] - soil) * 100 / (sensor["soil_max"] - sensor["soil_min"])
        print(f'Soil Humidity: {percent_soil}%')
        time.sleep(1)

def read_buttons():
    button1 = Pin(14, Pin.IN)
    button2 = Pin(15, Pin.IN)
    
    while True:
        print(f'Button1 value: {button1.value()}')
        print(f'Button2 value: {button2.value()}')
        if button1.value() and button2.value():
            break
        time.sleep(0.1)
        
def run_display():
    i2c=I2C(0,sda=Pin(0), scl=Pin(1), freq=400000)
    oled = SSD1306_I2C(128, 64, i2c)

    thermometer_ba = bytearray(b'\x00\x00\x00\x00\x00\x00\x00<\x00\x00f\x00\x00B\xe0\x00B\x00\x00B\x00\x00B\xe0\x00B\x00\x00B\x00\x00B\xe0\x00B\x00\x00B\x00\x00B\xe0\x00B\x00\x00\xc3\x00\x00\x81\x00\x00\x81\x00\x00\x81\x00\x00\x81\x00\x00\xc3\x00\x00~\x00\x00\x00\x00\x00\x00\x00'
    )
    thermometer_fb = framebuf.FrameBuffer(thermometer_ba,24,24, framebuf.MONO_HLSB)
    
    tear_ba = bytearray(b'\x00\x10\x00\x00\x18\x00\x00\x18\x00\x00<\x00\x00,\x00\x00$\x00\x00f\x00\x00\xc3\x00\x00\x81\x00\x01\x81\x80\x03\x00\xc0\x06\x00`\x04\x00`\x04\x00 \x0c\x000\x04\x00 \x0c\x000\x08\x00 \x04\x00 \x06\x00`\x06\x00@\x03\x01\xc0\x01\xef\x00\x00|\x00')
    tear_fb = framebuf.FrameBuffer(tear_ba, 24,24, framebuf.MONO_HLSB)

    sensors_position = [66, 80, 94, 108]
    sensors_labels = ['A', 'B', 'C', 'D']
    
    oled.fill(0)
    
    oled.text('OUTSIDE', 0, 3)
    oled.blit(thermometer_fb,0,12)
    oled.blit(tear_fb, 0, 40)
    
    oled.vline(58, 0, 64, 1)
    
    oled.text('SENSORS', 65, 3)
    
    for index, position in enumerate(sensors_position):
        oled.rect(position, 13, 10, 42, 1)
        oled.text(sensors_labels[index], position, 57)
    
    oled.text(f'0C', 28, 18)
    oled.text(f'0%', 28, 46)
    
    oled.show()
    time.sleep(5)
    oled.fill(0)
    oled.show()
    
def run_status_diode_1():
    status_diode_1 = Pin(12, Pin.OUT)
    for _ in range(6):
        status_diode_1.value(1)
        time.sleep(0.2)
        status_diode_1.value(0)
        time.sleep(0.2)
def run_status_diode_2():
    status_diode_2 = Pin(13, Pin.OUT)
    for _ in range(6):
        status_diode_2.value(1)
        time.sleep(0.2)
        status_diode_2.value(0)
        time.sleep(0.2)

def run_test_sequence():
    onboard_led.on()
    run_pump()
    run_status_diode_1()
    run_status_diode_2()
    run_led_strip()
    read_dht()
    read_soil_sensor()
    run_display()
    read_buttons()
    onboard_led.off()
    
run_test_sequence()








