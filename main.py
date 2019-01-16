# The MIT License (MIT)
# Copyright (c) 2019 2stacks@2stacks.net
# https://opensource.org/licenses/MIT
#

from umqtt.simple import MQTTClient
import machine
import network
import sys
import ubinascii

# Wireless station and AP settings
# There are five values for authmode:
#    0 -- open
#    1 -- WEP
#    2 -- WPA-PSK
#    3 -- WPA2-PSK
#    4 -- WPA/WPA2-PSK
# See - https://docs.micropython.org/en/latest/library/network.WLAN.html
STA_ESSID = '<essid>'
STA_PASSWD = '<passwd>'
STA_HOSTNAME = 'ESP-01'
AP_ESSID = 'MPonoff'
AP_PASSWD = '<passwd>'
AP_CHANNEL = 11
AP_AUTHMODE = 3

# ESP8266 ESP-12 modules have blue, active-low LED on GPIO2
# GPIO0  General-purpose input/output No. 0
# GPIO2  General-purpose input/output No. 2
# GPIO12 Sonoff pin number for relay
# GPIO13 Sonoff pin number for LED
# GPIO14 Sonoff pin number for spare
LED = machine.Pin(13, machine.Pin.OUT, value=1)

# connect to Adafruit IO MQTT broker using unsecure TCP (port 1883)
# 
# To use a secure connection (encrypted) with TLS: 
#   set MQTTClient initializer parameter to "ssl=True"
#   Caveat: a secure connection uses about 9k bytes of the heap
#         (about 1/4 of the micropython heap on the ESP8266 platform)
ADAFRUIT_IO_URL = b'io.adafruit.com' 
ADAFRUIT_USERNAME = b'<aio_username>'
ADAFRUIT_IO_KEY = b'<aio_key>'
ADAFRUIT_IO_FEEDNAME = b'onoff'
USE_SSL = False

state = 0


def sub_cb(topic, msg):
    global state
    print(topic, msg)
    if msg == b"on":
        LED.value(0)
        state = 1
    elif msg == b"off":
        LED.value(1)
        state = 0
    elif msg == b"toggle":
        # LED is inverse, so setting it to current state
        # value will make it toggle
        LED.value(state)
        state = 1 - state


def main():
    # Connect to local wireless network
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.config(dhcp_hostname=STA_HOSTNAME)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.connect(STA_ESSID, STA_PASSWD)
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())

    # Create access-point interface
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(True)
    ap_if.config(essid=AP_ESSID,
                 authmode=AP_AUTHMODE,
                 password=AP_PASSWD,
                 channel=AP_CHANNEL,)

    # create a random MQTT clientID
    mqtt_client_id = ubinascii.hexlify(machine.unique_id())

    client = MQTTClient(client_id=mqtt_client_id,
                        server=ADAFRUIT_IO_URL,
                        user=ADAFRUIT_USERNAME,
                        password=ADAFRUIT_IO_KEY,
                        ssl=USE_SSL,)

    client.set_callback(sub_cb)

    try:
        client.connect()
    except Exception as e:
        print('could not connect to MQTT server {}'.format(e))
        sys.exit()

    mqtt_feedname = bytes('{:s}/feeds/{:s}'.format(ADAFRUIT_USERNAME, ADAFRUIT_IO_FEEDNAME), 'utf-8')
    client.subscribe(mqtt_feedname)
    print("Connected to %s, subscribed to %s feed" % (ADAFRUIT_IO_URL, ADAFRUIT_IO_FEEDNAME))

    try:
        while True:
            client.wait_msg()
    except KeyboardInterrupt:
        print('Ctrl-C pressed...exiting')
        sys.exit()
    except Exception as e:
        print(e)
        machine.reset()
    finally:
        client.disconnect()


if __name__ == '__main__':
    main()
