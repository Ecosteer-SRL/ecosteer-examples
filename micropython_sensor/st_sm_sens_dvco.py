# date:     22/05/2023
# author:   georgiana
# version:  1.1 beta

# changes 22/05/2023  
# change sampling and pump interval based on how many iterations were done so far

from machine import Pin, SoftI2C, I2C, WDT
import usocket as socket
import ssl
import sys
import network     
import utime 
import gc
from umqtt.simple import MQTTClient
from bme680i2c import *

import json
from dvco_stub.pub_stack_stub import PubStackStub

# The following 5 globals will be changed based on contents of transport file
g_wifi_ssid: str = "SSID"
g_wifi_pwd: str = "PASSWORD"
g_broker_hostname: str  = ""
g_broker_port: int = 1883
g_broker_topic_root = "sens_dvco/"

g_broker_topic: str = ""
g_broker_keepalive: int =60
g_mqtt_connected: bool = False
g_mqtt_client = None
g_mqtt_client_id: str = "XYZ"       #   this is calculated later based on MAC address
g_broker_qos: int = 1

g_min_delay: int = 100                   # common dividend of g_sample_interval and loop_interval
g_sample_interval: int = 2000            #   controls sample and sending frequency
g_sample_delay = int(g_sample_interval/g_min_delay) # e.g. 20

g_wdt_timeout: int = 20000          #   controls WDT timeout


g_transport_file="transport.json"
g_product_file= "product.json"


def disconnect():
    global g_mqtt_client
    global g_mqtt_connected

    if g_mqtt_client == None:
        return
    try:
        if g_mqtt_connected == True:
            g_mqtt_client.disconnect()
    except Exception as e:
        print(f"Exception in mqtt disconnect: {e}")

    #   no matter what - kill it
    g_mqtt_client = None     
    g_mqtt_connected = False   

def connect():
    global g_mqtt_connected
    global g_mqtt_client
    global g_broker_hostname
    global g_broker_port
    global g_broker_keepalive

    while g_mqtt_connected == False:
        try:
            g_mqtt_client = MQTTClient(g_mqtt_client_id, g_broker_hostname, g_broker_port, None, None, g_broker_keepalive)
            res = g_mqtt_client.connect()
            if res==0:
                g_mqtt_connected = True
            else:
                g_mqtt_client = None
                utime.sleep_ms(500)
        except Exception as e:
            print(f"Exception in mqtt connect: {e}")
            g_mqtt_connected = False
            utime.sleep_ms(500)

def publish(payload):
    global g_mqtt_client
    global g_broker_topic
    #   try to send an infinite number of times
    #   after a while the WTC will stop it
    while True:
        connect()
        try:
            g_mqtt_client.publish(g_broker_topic.encode('UTF-8'),payload.encode("UTF-8"),qos=g_broker_qos)
            break
        except Exception as e:
            print(f"Exception in mqtt publish: {e}")
            disconnect()


def dop_loop_step(pub_stack, counter: int):
    #   here you can sample sensors etc. to form
    #   the payload to be sent

    err: int = 1
    while err==1:
        #   NOTE:
        #   in case the sampling is not valid
        #   then the function will enter an infinite loop, causing the WDT to go off
        #   thus rebooting everything
        
        payload = {
            "payload_number": str(counter),
            "mem": str(gc.mem_free())
            }

        try:
            r_temperature = bme.temperature 
            r_humidity = bme.humidity
            r_pressure = bme.pressure
            r_gas = bme.gas

            temperature = f"{str(round(r_temperature, 2))} C"   
            humidity = f"{str(round(r_humidity, 2))} %"
            pressure = f"{str(round(r_pressure, 2))} hPa"
            gas = f"{str(round(r_gas/1000, 2))} KOhms"

            
            payload["temp"] = temperature
            payload["hum"] = humidity
            payload["press"] = pressure
            payload["voc"] = gas
            payload["err"] = "0"
            
            err=0

        except OSError as e:
            payload["err"] = 1
            utime.sleep_ms(500)
            err=1

        payload_str = json.dumps(payload)
        print(payload_str)    
        #publish(payload)
        res = pub_stack.dopify(payload_str)


def mac2Str(mac): 
    return ''.join([f"{b:02X}" for b in mac])


print('You can ctrl-c now')
utime.sleep_ms(5000)
print('Too late')



#   start the wdt
g_main_wdt = WDT(timeout = g_wdt_timeout)


with open(g_transport_file) as transport:
    transport_conf = json.loads(transport.read())

    
url = transport_conf['url']     #"mqtt://127.0.0.1:1883"
try: 
    url_arr = url.split(':')    #["mqtt", "//127.0.0.1", "1883"]
    g_broker_hostname = url_arr[1][2:]       # "127.0.0.1" or "test.mosquitto.org" or any other broker
    g_broker_port = int(url_arr[2])           # "1883"
except Exception:
    print("Url format not valid")
    sys.exit()

g_broker_topic_root = f'{transport_conf["topic"]}/'
g_wifi_ssid = transport_conf["wifissid"]
g_wifi_pwd = transport_conf["wifipass"]


#   scan the I2C bus
i2c = I2C(scl=Pin(19,Pin.OUT), sda=Pin(18,Pin.OUT), freq=100000)
print("I2C scanning ", end='')
devices: list = i2c.scan()
while len(devices)<1:
    print('.',end='')
    utime.sleep_ms(5000)
    devices = i2c.scan()
print("I2C device found " + str(devices[0]))

#   here we assume that our device is the first
#   in the list. if we had more than one device, then this assumption
#   would not work
bme = BME680_I2C(i2c=i2c,address=devices[0])


#   initialize wifi phy layer
nic = network.WLAN(network.STA_IF) 
nic.active(True) 

g_main_wdt.feed()

gc.enable()

#   disconnect in order to avoid reboot issues
counter: int = 0

while nic.isconnected():
    print('Disconnecting', end='')
    nic.disconnect()
    print('.',end='')
    utime.sleep_ms(1000)


nic.connect(g_wifi_ssid,g_wifi_pwd) 
print("Connecting ",end='')
while not nic.isconnected() and nic.status() >= 0: 
    print(".", end='') 
    utime.sleep_ms(500)

print() 
print(nic.ifconfig())


###########################
# DVCO
###########################

def publish_callback(payload: str, userdata):
    print(payload)
    publish(payload)

with open(g_product_file) as conf:
    try:
        dvco_conf = json.loads(conf.read())
    except Exception: 
        print("error in reading product file")

pub_stack = PubStackStub()
pub_stack.init(dvco_conf)
pub_stack.set_pub_callback(publish_callback)



loop_interval = dvco_conf['loop_interval']
pump_delay = int(loop_interval/g_min_delay) # pump every pump_delay iterations

dvco_counter = 0
sample_counter = 0

#   main logic loop
while True:
    if not nic.isconnected():
        break
    #   get the MAC ADDRESS and use it as the mqtt client id and for the topic label
    mac = nic.config('mac')
    g_mqtt_client_id = mac2Str(mac)
    g_broker_topic = g_broker_topic_root + g_mqtt_client_id

    
    if dvco_counter % pump_delay == 0:    
        pub_stack.pump()
        dvco_counter = 0

    #   dop_loop_step holds the main logic of the program
    #   for instance, dop_loop_step can integrate with sensors etc.
    if sample_counter % g_sample_delay == 0:
        dop_loop_step(pub_stack, counter)
        counter = counter + 1
        sample_counter = 0

    
    dvco_counter += 1
    sample_counter += 1
    utime.sleep_ms(g_min_delay)
    g_main_wdt.feed()
    gc.collect()
    

