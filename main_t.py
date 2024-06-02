from machine import Pin, PWM, ADC, I2C
import time
from lib.neopixel import Neopixel
from dht import DHT11
from ssd1306 import SSD1306_I2C
import framebuf


# VARIABLE DEFINITIONS
outside_humidity = None
outside_temperature = None
inside_humidity = None
humidity_treshold = 50

# BUTTONS
button1 = Pin(14, Pin.IN)
button2 = Pin(15, Pin.IN)

# DIODES
onboard_led = Pin('LED')
status_diode_1 = Pin(12, Pin.OUT)
status_diode_2 = Pin(13, Pin.OUT)

# PUMP
pump_active = False
pump_flag = 0
pump_time = 5

# SENSORS
dht11 = DHT11(Pin(5))
soil_sensor = {
    "port": ADC(Pin(27)),
    "soil_min": 18600,
    "soil_max": 43000
}

# OLED
i2c=I2C(0,sda=Pin(0), scl=Pin(1), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)


def run_pump():
    global pump_active
    global pump_flag
    global pump_time
    global inside_humidity
    global humidity_treshold
    pwm = PWM(Pin(26))
    
    while True:
        if not pump_active:
            return
        if inside_humidity > humidity_treshold:
            pump_flag = 0
            return
        
        pump_flag += 1
        
        if pump_flag > 3:
            switch_status_diodes(False)
            return
        
        # start pump
        pwm.freq(200)
        pwm.duty_u16(45000)
        
        # water for x time
        time.sleep(pump_time)
        
        # stop pump
        pwm.duty_u16(0)
        pwm.freq(0)
        
        # wait for imersia
        time.sleep(5)
        
        # do three measures
        for _ in 3:
            read_soil_sensor()
            time.sleep(1)
        

    
    
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
    global outside_humidity
    global outside_temperature
    dht11.measure()
    outside_humidity = dht11.temperature()
    outside_temperature = dht11.humidity()
    print(f'Room Temperature: {outside_humidity}C')
    print(f'Room Humidity: {outside_temperature}%')
        
def read_soil_sensor():
    global inside_humidity
    _value = soil_sensor["port"].read_u16()
    _percent_value = (soil_sensor["soil_max"] - _value) * 100 / (soil_sensor["soil_max"] - soil_sensor["soil_min"])
    inside_humidity = max(0, min(100, int(_percent_value)))
    print(f'Soil Humidity: {inside_humidity}%')

def button1_handler(pin):
    global pump_active
    pump_active = not pump_active
    switch_status_diodes(pump_active)
    print("Button 1 pressed")

def button2_handler(pin):
    print("Button 2 pressed")
    
button1.irq(trigger=Pin.IRQ_FALLING, handler=button1_handler)
button2.irq(trigger=Pin.IRQ_FALLING, handler=button2_handler)
        
def run_display():
    
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
    
    oled.text('SENSOR', 65, 3)
    
    oled.rect(64, 13, 60, 20, 1)

    oled.text('DATA', 65, 36)
    oled.text('31.05.24', 65, 46)
    oled.text('Piwonia', 65, 56)
    oled.text(f'{outside_humidity}C', 28, 18)
    oled.text(f'{outside_temperature}%', 28, 46)
    
    # FILL DATA
    _fill_value = int(0 + (inside_humidity / 100) * (60-0))
    print(_fill_value)
    oled.fill_rect(64, 13, _fill_value, 20, 1)
    
    oled.show()
    
def switch_status_diodes(value):
    global status_diode_1
    global status_diode_2
    status_diode_1.value(value)
    status_diode_2.value(not value)
    
def run_status_diode_2():
    global status_diode_2
    global pump_active
    return

    
def main():
    global pump_active
    switch_status_diodes(pump_active)
    while True:
        read_dht()
        read_soil_sensor()
        run_display()
        time.sleep(1)
        
main()
    









