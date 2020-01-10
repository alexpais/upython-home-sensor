"""****************************************************************************
*
*
*	_author			: Alexandre Pais
*	_email			: alexandre.pais@gmail.com
*	_date			: March 2019
*	_project		: micropython sensor data collector for esp-01s/dht11
*	_description	: collect dht11 sensor data and send to mqtt broker
*
*	flow of the application
*	
*	- connect to wifi network
*	- connect to mqtt broker
*	- acquire data from sensors*
*	- publish sensor data via mqtt
*	- publish network connection staus data via mqtt
*	- deep sleep the mcu for N seconds or
*	- sleep the program loop for N seconds
*
*
****************************************************************************"""


import dht
import machine
import time
import socket
import network
from mqtt import MQTTClient 
import esp
import ujson


"""****************************************************************************
*
*	user configuration
*
****************************************************************************"""

# ** id of the sensor, to be indentifiable in mqtt
# 	device naming convention: ZZ-XXYY: 
# 		ZZ: device name
# 		XX: sensor type
# 		YY: sensor numeric id
sensor_id = "esp01s-dht01"

# ** toggle the deep sleep mode
dsleep_flag = False

# ** data collection interval (in minutes)
c_rate = 10

# ** toggle serial log messages
log = True

# ** gpio where some sensor might be connected
# 	esp-01s has only IO0 and IO2
input_sensor_gpio = 2

# ** wifi network credentials
wifi_ssid = "myhomenetwork"
wifi_pwd = "1234"
  
# ** mqtt broker config
client_id = sensor_id
broker = "192.168.1.2"
port= "1883"

"""****************************************************************************
*	end of user configuration
****************************************************************************"""



"""****************************************************************************
*
*	Functions
*
****************************************************************************"""
def wifi_activate():
	"""Activate the wifi modem
	"""
	
	wifi_handler = network.WLAN(network.STA_IF)
	# ap = network.WLAN(network.AP_IF)
	wifi_handler.active(True)
	# ap.active(False)
	return wifi_handler

def wifi_scan_user_ap(wifi_handler):
	"""Scan the surrounding wifi networks to see if the user network is transmitting
	- function WIFI.scan() reurns list of tuples: (ssid, bssid, channel, RSSI, authmode, hidden)
	"""

	for nwk in wifi_handler.scan():
		if nwk[0].decode() == wifi_ssid:
			return True
	
	if log: print("error connecting wifi: could not find network")	
	return False

def wifi_connect_user_ap(wifi_handler):
	"""Connect to the user wifi network
	- scan the surroundings to see if the network is transmitting
	- if the device does not find the network, returns error
	"""
	
	wlan = wifi_handler
	# ap = wifi_handler
	try:
		if log: print("starting wifi connection to {}".format(wifi_ssid))
	
		if not wlan.isconnected():
			if log: print("connecting to network...")
			# wlan.ifconfig('192.168.1.20','255.255.255.0','192.168.1.1')
			wlan.connect(wifi_ssid, wifi_pwd)
			while not wlan.isconnected():
				pass
			wlan.config(dhcp_hostname=sensor_id)
		
	except BaseException as err:
		if log: print("error connecting wifi {}".format(err.args))
		return None
	
	finally:
		if log: print('wifi connected! \nifconfig:', wlan.ifconfig())
		return wlan

def get_sensor_data(sensor, mqtt_conn):
	"""Get sensor readings and publish them to MQTT
	"""

	if log: print("collecting sensor data... ", end="")
	try:
		temp_measurement = []
		hum_measurement = []
		
		# take N readings from each "sensor"
		for _ in range(5):
			sensor.measure()
			temp_measurement.append(sensor.temperature()) # eg. 23 (°C)
			hum_measurement.append(sensor.humidity())    # eg. 41 (% RH)
			time.sleep(2)

		# get each measurement average		
		temp = sum(temp_measurement)/len(temp_measurement)
		hum = sum(hum_measurement)/len(hum_measurement)
		
		if log: print("{}º, {}%".format(temp, hum))
		mqtt_conn.publish(topic="device/{}/sensor/temperature".format(sensor_id), msg=str(temp))
		mqtt_conn.publish(topic="device/{}/sensor/humidity".format(sensor_id), msg=str(hum))
	
	except BaseException as err:
		if log: print("error reading sensor: {}".format(err.args))
		mqtt_conn.publish(topic="device/{}/sensor/error".format(sensor_id), msg=str(err.args))


def get_connection_data(wifi_conn, mqtt_conn):
	"""Get WiFi signal quality
	"""

	if log: print("collecting network data... ", end="")
	try:
		data = {
			"rssi": wifi_conn.status("rssi"),
			#wifi_conn.status(),
			#wifi_conn.ifconfig()
		}
		if log: print("{}".format(data))
		for key in data:
				mqtt_conn.publish(topic="device/{}/wifi/{}".format(sensor_id, key), msg=str(data[key]))

	except BaseException as err:
		if log: print("error getting connection status: {}".format(err.args))


def mqtt_connect():
	"""Start the mqtt connection and return the connection object
	"""

	try:
		if log: print("starting mqtt connection to: {}:{}".format(broker,port))
		client = MQTTClient(client_id, broker,user="", password="", port=port)
		client.connect()
		if log: print("mqtt connected!")
		return client
	except BaseException as err:
		if log: print("error connecting mqtt: {}".format(err.args))
		return

def standby():
	"""Put the mcu in standby mode, either by stalling the main 
	thread with sleep() or entering deep sleep mode
	"""

	print("standing by... ", "deep sleep" if dsleep_flag else "")

	# delay for next execution
	if dsleep_flag is False:
		time.sleep(c_rate * 60 * 1000)
		machine.reset()

	else:
		# when deepsleep is enabled, further configuration is required

		# configure RTC.ALARM0 to be able to wake the device
		rtc = machine.RTC()
		rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)

		# set teh RTC.ALARM0 to fire the interrupt after certain time
		rtc.alarm(rtc.ALARM0, c_rate * 60 * 1000)
		
		# go to sleep baby!
		machine.deepsleep()

def main():
	#
	#	When deepsleep is ENABLED, each run passes through here
	#

	#
	#	instantiate the sensor driver object and other state variables
	#
	dht_sensor = dht.DHT11(machine.Pin(input_sensor_gpio))
	wifi_is_connected = False
	mqtt_is_connected = False

	#
	#	connect to wifi when user network is available, otherwise skip
	#
	wifi_handler = wifi_activate()
	if wifi_scan_user_ap(wifi_handler) is True:
		while 1:
			wifi_conn = wifi_connect_user_ap(wifi_handler)
			if wifi_conn is not None:
				wifi_is_connected = True
				break
			time.sleep(10)
	
	#
	#	connect to mqtt when wifi connection is available, otherwise skip
	#
	if wifi_is_connected is True:
		for _ in range(5):
			mqtt_conn = mqtt_connect()
			if mqtt_conn is not None:
				mqtt_is_connected = True
				break
			time.sleep(10)

	#
	#	when deepsleep is DISABLED, each run stays stuck in the following loop
	#
	while 1:

		if wifi_is_connected and mqtt_is_connected:

			get_sensor_data(dht_sensor, mqtt_conn)
			get_connection_data(wifi_conn, mqtt_conn)

			# allow the background jobs to complete???
			# for deep sleep, it appears to be necessary...
			# further investigation is required
			time.sleep(1.5)
			mqtt_conn.disconnect()
			time.sleep(3)

		standby()


if __name__ == '__main__':
	if log: print('\napplication start: ', end="")
	
	if machine.reset_cause() == machine.DEEPSLEEP_RESET:
		print('starting: from a deep sleep')
	else:
		print('starting: from power on or hard reset')
	
	main()
