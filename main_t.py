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
import json

# LOOP CONTROLER
running = True

# VARIABLE DEFINITIONS
outside_humidity = None
outside_temperature = None
inside_humidity = None

# BUTTONS
debounce_time = 200
button1 = Pin(14, Pin.IN)
button2 = Pin(15, Pin.IN)

# DIODES
onboard_led = Pin('LED')
status_diode_1 = Pin(12, Pin.OUT)
status_diode_2 = Pin(13, Pin.OUT)

# PUMP
pump_active = False
pump_running = False
pump_flag = 0
pump_time = 5
pump_treshold = 50
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

# LED STRIP
numpix = 8
strip = Neopixel(numpix, 0, 6, "RGB")
strip_timer = Timer(-1)
animation_running = False


def logger(message):
    global info_message
    if (message is not None):
        print(message)
    info_message = message
    

def run_pump():
    global running
    global pump_running
    global pwm
    global pump_active
    global pump_flag
    global pump_time
    global inside_humidity
    global pump_treshold
    global info_message
    
    pump_running = True
    while running:
        if not pump_active:
            print('Pump disabled - skiping starting pump')
            logger(None)
            break
        if inside_humidity > pump_treshold:
            print('Humidity level OK - skiping starting pump')
            logger(None)
            pump_flag = 0
            break
        
        pump_flag += 1
        logger(f'Humidity level low - trying to start pump: attemp #{pump_flag}')
        time.sleep(3)
        
        if pump_flag > 2:
            logger(f'Too many tries - disabling pump')
            switch_pump(False)
            pump_flag = 0
            time.sleep(3)
            break
        
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
    pump_running = False
    
def strip_animation_a(_):
    global strip
    
    strip.rotate_right(1)
    strip.show()


def run_strip_animation(animation):
    global strip_timer
    global animation_running
    
    if animation_running:
        strip_timer.deinit()
    
    animation_running = True
    
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
    
    if animation == 'a':
        
        step = round(numpix / len(colors))
        current_pixel = 0
        strip.brightness(50)

        for color1, color2 in zip(colors, colors[1:]):
            strip.set_pixel_line_gradient(current_pixel, current_pixel + step, color1, color2)
            current_pixel += step

        strip.set_pixel_line_gradient(current_pixel, numpix - 1, violet, red)
        strip_timer.init(period=50, mode=Timer.PERIODIC, callback=strip_animation_a)
    
def set_strip_color(rgb):
    global strip
    global strip_timer
    global animation_running
    
    if animation_running:
        strip_timer.deinit()
        animation_running = False
        
    color = (int(rgb[1]), int(rgb[0]), int(rgb[2]))
    strip.fill(color)
    strip.show()
    print(f"LEDs set to color: {color}")
    
def read_dht():
    try:
        global outside_humidity
        global outside_temperature
        dht11.measure()
        outside_humidity = dht11.temperature()
        outside_temperature = dht11.humidity()
        print(f'Room Temperature: {outside_humidity}C')
        print(f'Room Humidity: {outside_temperature}%')
    except:
        print('Failed to read dht')
        
def read_soil_sensor():
    global inside_humidity
    _value = soil_sensor["port"].read_u16()
    _percent_value = (soil_sensor["soil_max"] - _value) * 100 / (soil_sensor["soil_max"] - soil_sensor["soil_min"])
    inside_humidity = max(0, min(100, int(_percent_value)))
    print(f'Soil Humidity: {inside_humidity}%')

def button1_handler(pin):
    global pump_active
    if ap_mode:
        return
    pump_active = not pump_active
    switch_pump(pump_active)
    print("Button 1 pressed")

button2_press_time = 0
def button2_handler(pin):
    global ap_mode
    global button2_press_time
    if ap_mode:
        return
    if pin.value() == 1:  # przycisk naciśnięty
        button2_press_time = time.ticks_ms()
    else:  # przycisk zwolniony
        press_duration = time.ticks_diff(time.ticks_ms(), button2_press_time)
        if press_duration >= 3000:
            ap_mode = True
            button2_press_time = 0
            print("Access Point mode activated")
        else:
            print("Button 2 pressed briefly")
    
    
button1.irq(trigger=Pin.IRQ_FALLING, handler=button1_handler)
button2.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=button2_handler)
        
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
    

def load_html(filename):
    with open(filename, 'r') as file:
        return file.read()


def connect_to_wifi(ssid, password):
    global onboard_led
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
        
    wlan.connect(ssid, password)
    timeout = 5
    while not wlan.isconnected() and timeout > 0:
        print(wlan.status())
        onboard_led.toggle()
        logger(f'Connecting to {ssid} WiFi...')
        time.sleep(1)
        timeout -= 1
    if wlan.isconnected():
        onboard_led.on()
        ip = wlan.ifconfig()[0]
        logger(f'Connected to {ssid} WiFi with IP: {ip}')
        time.sleep(3)
        logger(None)
        return ip
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
        return None


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
    
def save_pump_config(treshold, time):
    with open('pump_config.txt', 'w', encoding='utf-8') as f:
        f.write(f'{treshold}\n{time}')
    
def load_pump_config():
    try:
        with open('pump_config.txt', 'r') as f:
            treshold = f.readline().strip()
            time = f.readline().strip()
            return int(treshold), int(time)
    except OSError:
        return None, None
    
def set_pump_config(treshold, time):
    global pump_treshold
    global pump_time
    
    pump_treshold = treshold
    pump_time = time

def parse_query_params(query):
    params = {}
    for param in query.split('&'):
        key, value = param.split('=')
        params[key] = value
    return params

def serve_ap_website():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)#creating socket object
    s.bind(('', 80))
    s.listen(5)
    
    ap_index = load_html('ap_index.html')
    ap_configure = load_html('ap_configure.html')
    
    while True:
        cl, addr = s.accept()
        print('Client connected from', addr)
        request = cl.recv(1024).decode()
        print('Request:', request)

        if 'GET / ' in request:
            response = ap_index
            cl.send(response)

        if 'POST /configure ' in request:
                match = ure.search(r'ssid=([^&]*)&password=(.*)', request)
                if match:
                    ssid = match.group(1).replace('%20', ' ').replace('+', ' ')
                    password = match.group(2).replace('%20', ' ')
                    save_wifi_config(ssid, password)
                    response = ap_configure.format(ssid, password)
                    cl.send(response)
        cl.close()

def run_ap():
    global ap_mode
    
    ap = network.WLAN(network.AP_IF)
    ap.config(essid='SmartPot', password='qqqwwweee')
    ap.active(True)
    while ap.active() == False:
        logger('Starting AP...')
    
    logger('AP Mode Is Active IP:' + ap.ifconfig()[0])
    
    serve_ap_website()


def open_wifi_socket(ip):
    # Open a socket
    address = (ip, 80)
    connection = socket.socket()
    connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    connection.bind(address)
    connection.listen(1)
    return connection


def serve_wifi_website(connection):
    global pump_time
    global pump_treshold
    while True:
        client = connection.accept()[0]
        request = client.recv(1024)
        request = str(request)
        print(request)

        match = ure.search(r'GET\s([^\s]+)', request)
        if match:
            path = match.group(1)
            if '?' in path:
                path, query = path.split('?', 1)
                params = parse_query_params(query)
            else:
                params = {}
                
        if '/set_strip_color' in request:
            if 'rgb' in params:
                    rgb = params['rgb'].split(',')
                    set_strip_color(rgb)
                    response = 'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK'
            else:
                response = 'HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\n\r\nInvalid parameters'
        elif '/turn_off_strip' in request:
            set_strip_color([0,0,0])
            response = 'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK'
        elif '/run_animation_a' in request:
            run_strip_animation('a')
            response = 'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK'
        elif path == '/set_pump_config':
                if 'time' in params and 'treshold' in params:
                    pump_time = int(params['time'])
                    pump_treshold = int(params['treshold'])
                    set_pump_config(pump_treshold, pump_time)
                    save_pump_config(pump_treshold, pump_time)
                    response = 'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK'
                else:
                    response = 'HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\n\r\nInvalid parameters'
        elif path == '/get_pump_config':
                response = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n' + json.dumps({"treshold": pump_treshold, "time": pump_time})
        else:
            response = load_html('wifi_index.html')
            
        client.send(response)
        client.close()
    
        
def hardware_loop(_):
    global pump_running
    if ap_mode == True:
        run_ap()
    read_dht()
    read_soil_sensor()
    if not pump_running:
        run_pump()
def main():
    global running
    global pump_active
    try:
        
        switch_pump(pump_active)
        
        treshold, time = load_pump_config()
        if treshold and time:
            set_pump_config(treshold, time)
        else:
            set_pump_config(50, 5)
        
        display_timer = Timer(-1)
        display_timer.init(period=500, mode=Timer.PERIODIC, callback=run_display)
        
        hardware_timer = Timer(-1)
        hardware_timer.init(period=5000, mode=Timer.PERIODIC, callback=hardware_loop) 
    
        ssid, password = load_wifi_config()
        if ssid and password:
            ip = connect_to_wifi(ssid, password)
            if ip:
                connection = open_wifi_socket(ip)
                serve_wifi_website(connection)

    except KeyboardInterrupt:
        print('Finished loop')
        display_timer.deinit()
        hardware_timer.deinit()
        running = False
        
main()
    
















