from machine import Pin, PWM, ADC, I2C, Timer
import time
from lib.neopixel import Neopixel
from dht import DHT11
from ssd1306 import SSD1306_I2C
import framebuf
import _thread
import network
import socket

# LOOP CONTROLER
running = True

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
pwm = PWM(Pin(26))

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
info_message = None

# ACCES POINT
ap_mode = False

def logger(message):
    global info_message
    if (message is not None):
        print(message)
    info_message = message
    

def run_pump():
    global running
    global pwm
    global pump_active
    global pump_flag
    global pump_time
    global inside_humidity
    global humidity_treshold
    global info_message
    
    
    while running:
        if not pump_active:
            print('Pump disabled - skiping starting pump')
            logger(None)
            return
        if inside_humidity > humidity_treshold:
            print('Humidity level OK - skiping starting pump')
            logger(None)
            pump_flag = 0
            return
        
        pump_flag += 1
        logger(f'Humidity level low - trying to start pump: attemp #{pump_flag}')
        time.sleep(3)
        
        if pump_flag > 2:
            logger(f'Too many tries - disabling pump')
            switch_pump(False)
            pump_flag = 0
            time.sleep(3)
            return
        
        logger(f'Starting pump for {pump_time}s')
        # start pump
        pwm.freq(200)
        pwm.duty_u16(45000)
        
        # water for x time
        time.sleep(pump_time)
        
        # stop pump
        pwm.duty_u16(0)
        
        logger(f'Waiting for imersia 5s')
        # wait for imersia
        time.sleep(5)
        
        # do three measures
        for _ in range(3):
            read_soil_sensor()
            logger(f'Reading sensor after watering - current level: {inside_humidity}%')
            time.sleep(3)
    
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
    switch_pump(pump_active)
    print("Button 1 pressed")

def button2_handler(pin):
    global ap_mode
    ap_mode = not ap_mode
    print(ap_mode)
    print("Button 2 pressed")
    
button1.irq(trigger=Pin.IRQ_FALLING, handler=button1_handler)
button2.irq(trigger=Pin.IRQ_FALLING, handler=button2_handler)
        
def run_display(_):
    global running
    global inside_humidity
    global info_message
    thermometer_ba = bytearray(b'\x00\x00\x00\x00\x00\x00\x00<\x00\x00f\x00\x00B\xe0\x00B\x00\x00B\x00\x00B\xe0\x00B\x00\x00B\x00\x00B\xe0\x00B\x00\x00B\x00\x00B\xe0\x00B\x00\x00\xc3\x00\x00\x81\x00\x00\x81\x00\x00\x81\x00\x00\x81\x00\x00\xc3\x00\x00~\x00\x00\x00\x00\x00\x00\x00'
    )
    thermometer_fb = framebuf.FrameBuffer(thermometer_ba,24,24, framebuf.MONO_HLSB)
    
    tear_ba = bytearray(b'\x00\x10\x00\x00\x18\x00\x00\x18\x00\x00<\x00\x00,\x00\x00$\x00\x00f\x00\x00\xc3\x00\x00\x81\x00\x01\x81\x80\x03\x00\xc0\x06\x00`\x04\x00`\x04\x00 \x0c\x000\x04\x00 \x0c\x000\x08\x00 \x04\x00 \x06\x00`\x06\x00@\x03\x01\xc0\x01\xef\x00\x00|\x00')
    tear_fb = framebuf.FrameBuffer(tear_ba, 24,24, framebuf.MONO_HLSB)

    oled.fill(0)
    
    if info_message is not None:
        height = 0
        row = ''
        for word in info_message.split(' '):
            if len(row) + len(word) < 16:
                row += word + ' '
                oled.text(row, 0, height)
            else:
                height += 10
                row = word + ' '
                oled.text(row, 0, height)
    else:
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
        _fill_value = int(0 + (inside_humidity / 100) * (60 - 0)) if inside_humidity is not None else 0
        oled.fill_rect(64, 13, _fill_value, 20, 1)
    
    oled.show()
    
    
def switch_pump(value):
    global status_diode_1
    global status_diode_2
    global pump_active
    pump_active = value
    status_diode_1.value(value)
    status_diode_2.value(not value)
    
def web_page():
  html = """<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
            <body><h1>Hello world</h1></body></html>
         """
  return html

# if you do not see the network you may have to power cycle
# unplug your pico w for 10 seconds and plug it in again
def run_ap():
    global ap_mode
    
    ap = network.WLAN(network.AP_IF)
    ap.config(essid='SmartPot', password='qqqwwweee')
    ap.active(True)
    while ap.active() == False:
        logger('Starting AP...')
    
    logger('AP Mode Is Active IP:' + ap.ifconfig()[0])

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   #creating socket object
    s.bind(('', 80))
    s.listen(5)

    while ap_mode == True:
        conn, addr = s.accept()
        print('Got a connection from %s' % str(addr))
        request = conn.recv(1024)
        print('Content = %s' % str(request))
        response = web_page()
        conn.send(response)
        conn.close()
    
    ap.active(False)
    while ap.active() == True:   
        logger('Disabling Acess Point...')
    time.sleep(1)
    logger(None)
    
def main():
    global running
    global pump_active
    try:
        
        switch_pump(pump_active)    
        timer = Timer(-1)
        timer.init(period=500, mode=Timer.PERIODIC, callback=run_display)
        
        while running:
            if ap_mode == True:
                run_ap()
            read_dht()
            read_soil_sensor()
            run_pump()
            time.sleep(2)
    except KeyboardInterrupt:
        print('Finished loop')
        timer.deinit()
        running = False
        
main()
    











