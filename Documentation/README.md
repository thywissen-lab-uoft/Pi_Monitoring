# raspy2c
Comprehensive support for I2C devices on the Raspberry Pi

uses packages:
  - smbus (raspy2c, pyKraken)
  - time (raspy2c(example), pyKraken)
  - RPi.GPIO (pyKraken)

This project originated from the need to measure and correlate multiple 
(slow) signals -- e.g. temperature, humidity, laser-beam pointing -- 
in a quantum optics lab at the University of Toronto, Canada.

I2C in combination with a Raspberry Pi was chosen as the way to go, since it
provides a simple and easily expandable architecture. Further inclusion of 
GPIO pins allows for triggered measurements, e.g. to measure the intensity of a
laser pulse whenever it is turned on.

The architecture of the classes supporting different devices is built to easily
add new devices with help of the respective datasheet, while (hopefully) maintaining 
a common syntax. The project deliberately does not make much use of additional
modules (e.g. numpy, matplotlib, MultiProcessing, autologging, ...), so that
the setup from unboxing to first data acquisition is as easy as can be.
Installing i2c-tools (provides the tremendously usefull i2cdetect) is higly
recommended: 'sudo apt-get install -y i2c-tools'

Do not choose this repository if you need fast ADC reading or real-time DAQ.
The effective data rate for repeated measurements of a single 12-bit ADS1015
channel on a RPi 2B+ is limited to about 1000 SPS -- useful enough to do basic
monitoring tasks, but far too slow for e.g. accoustig measurements.

Beware of static shock and other hazards when playing with your hardware!
