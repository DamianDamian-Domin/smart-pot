from machine import Pin, PWM, ADC, I2C, Timer
import machine
import time
from lib.neopixel import Neopixel
from dht import DHT11
from ssd1306 import SSD1306_I2C
import framebuf
import _thread
import network
import socket
import ure

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


def connect_to_wifi(ssid, password):
    global onboard_led
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
        
    wlan.connect(ssid, password)
    timeout = 20
    while not wlan.isconnected() and timeout > 0:
        print(wlan.status())
        onboard_led.toggle()
        logger(f'Connecting to {ssid} WiFi...')
        time.sleep(1)
        timeout -= 1
    if wlan.isconnected():
        onboard_led.on()
        print(wlan.ifconfig())
        logger(f'Connected to {ssid} WiFi with IP: {wlan.ifconfig()[0]}')
        time.sleep(5)
        logger(None)
    else:
        onboard_led.off()
        message = None
        if wlan.status() == -3:
            message = 'Wrong password'
        elif wlan.status() == -2:
            message = 'No access point found'
        elif wlan.status() == -1:
            message = 'Failed to connect'
        else:
            message = 'Error: Unknown'
        logger(f'Failed to connect to WiFi: {message}')
        time.sleep(3)
        logger(None)


def save_wifi_config(ssid, password):
    with open('wifi_config.txt', 'w', encoding='utf-8') as f:
        f.write(f'{ssid}\n{password}')

def load_wifi_config():
    try:
        with open('wifi_config.txt', 'r') as f:
            ssid = f.readline().strip()
            password = f.readline().strip()
            return ssid, password
    except OSError:
        return None, None

def run_ap():
    global ap_mode
    
    ap = network.WLAN(network.AP_IF)
    ap.config(essid='SmartPot', password='qqqwwweee')
    ap.active(True)
    while ap.active() == False:
        logger('Starting AP...')
    
    logger('AP Mode Is Active IP:' + ap.ifconfig()[0])

def serve():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   #creating socket object
    s.bind(('', 80))
    s.listen(5)
    
    while True:
        cl, addr = s.accept()
        print('Client connected from', addr)
        request = cl.recv(1024).decode()
        print('Request:', request)

        if 'GET / ' in request:
            response = """\
HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
<body>
<h1>Configure WiFi</h1>
<form action="/configure" method="post">
SSID:<br>
<input type="text" name="ssid"><br>
Password:<br>
<input type="text" name="password"><br>
<input type="submit" value="Submit">
</form>
</body>
</html>
"""
            cl.send(response)

        if 'POST /configure ' in request:
                match = ure.search(r'ssid=([^&]*)&password=(.*)', request)
                if match:
                    ssid = match.group(1).replace('%20', ' ').replace('+', ' ')
                    password = match.group(2).replace('%20', ' ')
                    save_wifi_config(ssid, password)
                    response = """\
HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
<body>
<h1>Configuration Saved - Restart your device</h1>
<p>SSID: {}</p>
<p>Password: {}</p>
</body>
</html>
""".format(ssid, password)
                    cl.send(response)
                    cl.close()
                    break
        cl.close()


    
def main():
    global running
    global pump_active
    try:
        
        switch_pump(pump_active)    
        timer = Timer(-1)
        timer.init(period=500, mode=Timer.PERIODIC, callback=run_display)
        
        ssid, password = load_wifi_config()
        if ssid and password:
            connect_to_wifi(ssid, password)
        
        while running:
            if ap_mode == True:
                run_ap()
                serve()
            read_dht()
            read_soil_sensor()
            run_pump()
            time.sleep(1)
    except KeyboardInterrupt:
        print('Finished loop')
        timer.deinit()
        running = False
        
main()
    













