# ecosteer-examples

The first example is found in sensor_stream directory, which contains a Python program that publishes real CO2 data points on an MQTT broker.

Two versions of the program are provided:
- sensor.py: a base implementation, without DVCO capabilities
- dvco_sensor.py: an upgraded implementation of sensor.py, that contains the necessary calls to the DVCO pub stack primitives and dopifies the data streams

The difference between these two programs is used to show how a general purpose data stream can be integrated with the DVCO pub stack.

The sensor_stream directory contains the following subdirectories: 
- common: collects modules shared between multiple classes in the project
- dvco_stub: contains a stub implementation of the DVCO publisher stack, useful to show how a general purpose program can be integrated with the DVCO pub stack and become a DVCO-enabled publisher
- externals: contains the code for reading CO2 data 
- provider: contains a provider-based implementation of an MQTT client, used by the publisher to send data to a broker
- sensor: contains the two versions of the program, sensor.py and dvco_sensor.py. As the dvco_sensor.py uses a stub implementation of the pub stack, the dopified data corresponds to the input data.


# CO2 SENSOR 

Sensor: TFA Monitor DE CO2 DOSTMANN AIRCO2NTROL Mini 1.5006, 31.5006.02

The CO2Meter implementation thankfully provided by Michael Nosthoff in https://github.com/heinemml/CO2Meter was adapted for this project. 


# INSTALLATION

Connect the USB sensor to a Linux computer, such as an Ubuntu 18 or 
to a Raspberry Pi Zero W board. It should be listed by inserting the following command: 
```
> lsusb
```
The output should contain the following entry:  
```
Bus 001 Device 003: ID 04d9:a052 Holtek Semiconductor, Inc. USB-zyTemp
```
The hexadecimal ID contains four digits:   
- the first two (0x04d9) indicate the vendor id;  
- the last two (0xa052) indicathe the product id.  

You can also check the product with the online search engine: https://www.the-sz.com/products/usbid/index.php?


The default driver for USB in linux is HIDRAW. 
```
> ls /dev/
```
There should be two entries, hidraw0 and hidraw1.  
Please note that the /dev/hidraw0 can be used by other devices as well and it cannot be accessed without
root privileges. In order to avoid this issue create a file called 90-co2mini.rules in the folder /etc/udev/rules.d.

```
> touch /etc/udev/rules.d/90-co2mini.rules
```
It should contain the following contents:
```
ACTION=="remove", GOTO="co2mini_end"
SUBSYSTEMS=="usb", KERNEL=="hidraw*", ATTRS{idVendor}=="04d9", ATTRS{idProduct}=="a052", GROUP="plugdev", MODE="0660", SYMLINK+="co2mini%n", GOTO="co2mini_end"
LABEL="co2mini_end"
```
The file instructs the OS to create a simlink called co2mini%n, where %n is a auto incrementing number, for any USB with vendor id 04d9 and product id a052. The mask is 0660, which means that the file /dev/co2mini%n can be accessed by any user in the plugdev group. On debian systems, plugdev is a system group and the user you are using to ssh into the device should belong to the group. Check that plugdev is listed in your groups:
```
groups
```
Alternatively, if you are using an Ubuntu system that does not have the plugdev group, you can set the mode to 0666 in the above code snippet (MODE="0666") and you will be able to access the device with any user. 

Now, every time the sensor will be re-connected to the computer it will be listed as co2mini%n in /dev directory. The entry needs to be passed as a configuration to CO2Meter.


## SOFTWARE DEPENDENCIES

- Python version 3.9.10  
- paho-mqtt version 1.6.1  

The paho-mqtt package can be installed in a virtualenv:
```
> cd ${HOME}
> mkdir -p virtualenv
> cd virtualenv
> python3.9 -m venv dop 
> source dop/bin/activate
> pip install wheel
> pip install paho-mqtt 
```

## INSTALL PROJECT AND RUN

Clone this repo in a local folder called ecosteer_examples/sensor_stream. 

To run the sensor program:
```
> source ~/virtualenv/dop/bin/activate
> cd ${HOME}/ecosteer_examples/sensor_stream/sensor
> source env.sh 
> python sensor.py -c ${PATH_TO_CURRENT_DIRECTORY}/sensors_co2_mosq.yaml
```
The env.sh file contains PYTHONPATH environmental variable that should indicate the path to the sensor_stream directory.  

### IMPLEMENTATION NOTES

The mqtt output provider is not thread-safe, so the access to the method write() is syncronized at the level of the main program. 

In provider_pres_output.py and pres_output_mqtt.py there is a DopEvent type: the source file for the DopEvent was not included in the repo, as it is not relevant for the project at hand. Its definition nevertheless is needed as it is used as a parameter to the writeEvent() method, therefore it was defined as a NewType. 
