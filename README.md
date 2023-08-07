
# SPONSORS
This project was sponsored by the [Provincia Autonoma di Bolzano (PAB)](https://home.provincia.bz.it/it/home), Italy.

<p >
  <img src="https://github.com/Ecosteer-SRL/ecosteer_examples/blob/e311d2c1565c7745dde7e9d96825e0a6786f451c/pab_logo.png" width="30%"/>
</p>


# REPO STRUCTURE
This repository collects some examples to show how to use the DVCO (Data Visibility Control Overlay) stack APIs in programs that publish data to a pub-sub broker, like a MQTT broker. 

The first example (in the python_sensor folder) is a Python program that publishes real CO2 data points to a MQTT broker. The second example (in the micropython_sensor folder) is a Micropython program that publishes VOC, temp and humidity data to a MQTT broker. This program has been deployed and tested on a ESP32 microcontroller connected to a BME680 sensor, shown in the picture below.

<p >
  <img src="https://github.com/Ecosteer-SRL/ecosteer_examples/blob/a997bb7626791ac365eb018624d05e286afb8084/ESP32-BME680.png" width="20%"/>
</p>


For each example program, two versions (BEFORE and AFTER) are provided:
- a base implementation <b>without</b> DVCO capabilities (python: sensor.py, Micropython: st_sm_sens.py)
- an upgraded implementation <b>with</b> DVCO capabilities, that implements the necessary calls to the DVCO pub stack APIs and dopifies the data streams  (python: dvco_sensor.py, Micropython: st_sm_sens_dop.py)

The differences between the two versions (BEFORE and AFTER) show how a publisher program can be modified in order to use the DVCO pub stack. Please note that the DVCO publisher stack used in these examples is a stub implementation.

The repository contains the following folders: 
- common: collects modules shared between multiple classes in the project, and between the Python and Micropython programs
- dvco_stub: contains a stub implementation of the DVCO publisher stack, useful to show how a general-purpose program can be integrated with the DVCO pub stack and become a DVCO-enabled publisher
- Micropython sensor: 
    - contains the library for the communication with a BME680 sensor via I2C and the two programs, one without DVCO and one DVCO-enabled (with stub implementation) in Micropython
- python_sensor: 
    - externals: contains the code for reading CO2 data 
    - sensor: contains the two versions of the Python program, sensor.py and dvco_sensor.py. As the dvco_sensor.py uses a stub implementation of the pub stack, the dopified data corresponds to the input data. This folder also contains a module, mqtt_output.py, which offers a client implementation that wraps mqtt paho client. 

# PYTHON
## CO2 SENSOR 

Sensor: TFA Monitor DE CO2 DOSTMANN AIRCO2NTROL Mini 1.5006, 31.5006.02

The CO2Meter implementation thankfully provided by Michael Nosthoff in https://github.com/heinemml/CO2Meter was adapted for this project. 


## INSTALLATION

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


### SOFTWARE DEPENDENCIES

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

### INSTALL PROJECT AND RUN

Clone this repo in a local folder called ecosteer_examples/python_sensor. 

To run the sensor program:
```
> source ~/virtualenv/dop/bin/activate
> cd ${HOME}/ecosteer_examples/python_sensor/sensor
> source env.sh 
> python sensor.py -c ${PATH_TO_CURRENT_DIRECTORY}/sensors_co2_mosq.yaml
```
The env.sh file contains PYTHONPATH environmental variable that should indicate the path to the python_sensor directory.  

In order to run the dvco_sensor program the steps are similar. This will dopify the data by using the stub implementation of the DVCO pub stack, and will publish it by using the callback installed on the stack.  
```
> source ~/virtualenv/dop/bin/activate
> cd ${HOME}/ecosteer_examples/python_sensor/sensor
> source env.sh 
> python dvco_sensor.py -c ${PATH_TO_CURRENT_DIRECTORY}/sensors_co2_mosq.yaml -p product.json
``` 


## IMPLEMENTATION NOTES

The class MqttClient offers an implementation of a client for MQTT protocol to be used to publish data. 
Its write() method is not thread-safe, so the access to it needs to be synchronized in a multi-threaded environment. 

The sensor program uses this method in a single thread, which is responsible for reading and publishing sensor data, and therefore no synchronization is implemented. 

In the DVCO-instrumented implementation of the sensor program, this write() method of MqttClient is called inside the function used as the data callback by the DVCO stack. In this specific implementation, the callback (and thus the method write()) is solely called by the DVCO stack stub implementation, therefore the synchronization implemented by the DVCO stack provides the proper thread safety. If, instead, the function used as the data callback is used by threads that are not solely under the control of the DVCO-stack – then the same function has to be responsible for the necessary synchronization, as the DVCO-stack cannot be aware of all the threads firing the same function.


# MICROPYTHON

The Micropython publisher uses modules found in the folders common, dvco_stub and micropython_sensor. 


## HARDWARE

This project requires an ESP32 and a BME680 sensor from Arduino. The SCL pin of the sensor should be connected to pin 19 of the ESP32 and the SDA pin to pin 18 of ESP32. 

The sensor measures air quality indicators as VOC (Volatile Organic Compounds), humidity, pressure and temperature.

## INSTALLATION

### SOFTWARE DEPENDENCIES
The following software is recommended for the deployment on a microcontroller:
- Python (at least 3.8): the installation of Python is out of the scope of this document
- Thonny IDE: you can install it from https://thonny.org/
- ampy: you can install it by typing in the shell the following command:
```
    pip install adafruit-ampy
```
- Micropython firmware version 1.19.1: you can download the ESP32 port from https://Micropython.org/download/esp32/ 

For testing the deployment: 
- mosquitto_sub: you can download the installer from https://mosquitto.org/download/ or, if you are running on a Linux-based system, you can install it with 
```
sudo apt install -y mosquitto-clients
```

### INSTALL PROJECT AND RUN

First of all you need to flash the Micropython firmware on the microcontroller. To flash the Micropython firmware on the board:
1) Connect your ESP32 board to your computer, and take note of the COM port it is connected to.
2) Open Thonny IDE. Go to Tools > Options > Interpreter.
3) Select the interpreter you want to use and select the COM port your board is connected to. Click on Install or Update firmware.
4) Select again the port, and click on the Browse button to open the .bin file with the Micropython firmware you have downloaded. Click on Install.

Please clone the repository, or download the archive containing the source code from GitHub. 

Go to the project folder and open a shell. Create an empty file named \_\_init\_\_.py, which you will need to copy on the microcontroller.

The Micropython publisher requires 'umqtt.simple' that can be downloaded directly from github with the following command:
```
> wget https://raw.githubusercontent.com/Micropython/Micropython-lib/master/Micropython/umqtt.simple/umqtt/simple.py
```


Copy the needed modules on the microcontroller, adjusting the port to the one your microcontroller is connected to:

```
ampy --port com10 mkdir common
ampy --port com10 mkdir common/python
ampy --port com10 put common/python/config_utils.py common/python/config_utils.py
ampy --port com10 put common/python/dop_stop_event_mpy.py common/python/dop_stop_event_mpy.py
ampy --port com10 put common/python/error.py common/python/error.py
ampy --port com10 put common/python/threads.py common/python/threads.py
ampy --port com10 put __init__.py common/python/__init__.py


ampy --port com10 mkdir dvco_stub
ampy --port com10 put dvco_stub/abstract_pub_stack.py dvco_stub/abstract_pub_stack.py
ampy --port com10 put dvco_stub/pub_stack_stub.py dvco_stub/pub_stack_stub.py
ampy --port com10 put __init__.py dvco_stub/python/__init__.py

ampy --port com10 mkdir umqtt
ampy --port com10 put simple.py umqtt/simple.py
ampy --port com10 put __init__.py umqtt/python/__init__.py

ampy --port com10 put micropython_sensor/bme680i2c.py bme680i2c.py

```


Edit the files product.json and transport.json to adjust the configuration for the publisher, and set the WiFi SSID and Password of your network, then copy them to the microcontroller. 
```
ampy --port com10 put micropython_sensor/product.json product.json
ampy --port com10 put micropython_sensor/transport.json transport.json 
```


Copy the main program you want to deploy on the microcontroller, and name it boot.py:
```
ampy --port com10 put micropython_sensor/st_sm_sens.py boot.py 
```
or 
```
ampy --port com10 put micropython_sensor/st_sm_sens_dvco.py boot.py   
```

Now you can run the program either from Thonny (open the file boot.py and click Run) or by pressing the reset button on ESP32 (EN), which will start the program automatically.

If you did not change the configuration values for the transport, you can see the data points via the following command:
```
mosquitto_sub -h test.mosquitto.org -t sens_dvco
```
