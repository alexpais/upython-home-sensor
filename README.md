# Ambient Sensor with ESP and Micropython

## Overview

This repository contains Micropython code for the ESP with a DHT11 shield. What it does is tranform the small MCU into a small ambient sensor, that reads Temperature and Humidity and publishes the date to a local MQTT Broker on my home network. 

To parse, store and display the data, i also setup Mosquitto, Node Red, InfluxDB, and built a few Grafana Dashboards, since i used a couple of this small sensors around the house, for bedroom and living room

I used a small ESP01-S, which is an inexpensive ESP with a attached onto a small PCB. The code makes use of the deepsleep available on the MCU, in order to reduce the battery so it can run for a long time, but since it only has very few Pins available on the plug, to use the deepsleep properly i had to solder a small wire connecting GPIO 16 (available on the chip) to the RST Pin, which is available on the plug. 

Because i used a very small version of the ESP, there are a few tricks that are listed on this readme, that are specific to this MCU/Package.

## Code explanation

Altough the functionality is quite basic, the code has passed through a few iterations until all bugs were eliminated. Pretty much the usual connection problems, like stalled MQTT, unfinished wifi connection.

The steps the application performs are:
	
- connect to wifi network
- connect to mqtt broker
- acquire data from sensors
- publish sensor data via mqtt
- publish network status via mqtt
- deep sleep/sleep for N seconds

## Hardware Requirements

- ESP01-S
- USB Programmer
- Thin wire for the deepsleep shunt
- a piece of wire to shunt other pins
- ESP DHT11 Shield
- 

## Software Requirements

- Ampy
- ESPtool
  
## Usefull commands

* send a file to a board running micropython
```bash
ampy -p /dev/ttyUSB0 -b 115200 put path/to/file
```
* enter REPL over serial
```bash
screen /dev/ttyUSB0 115200
```
* basic esptool command
```bash
esptool.py --chip esp8266 --port /dev/ttyUSB1 ?????
```
* clear flash memory
```bash
esptool.py --chip esp8266 --port /dev/ttyUSB0 erase_flash
```
* upload new firmware
```bash
esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash --flash_size=detect 0 esp826-???????
```

## FAQ

* How to setup the code ?
1) clean the MCU flash memory, 2) flash the MCU with the new micropython firmware, 3) send over the project files (WiFi and MQTT already configured)

* How the deepsleep works ?
after the chip enters the deepsleep mode, it disables everything except a clock, which continues to tick for a finite number of seconds, configured by the user. When the sleep time expires, the chip emits an interrupt on Pin 16, so being it connected to RST, it makes the chip reset and execute it's code again.

* How to flash the ESP01-S ?
add a small piece of wire to shunt the Pin IO0 to GND before putting the MCU onto the USB Programmer

image

* How to enable deepsleep ?
solder a piece of thin wire between GPIO 16 and the RST Pin, to allow the chip to wake from the deepsleep.

image

