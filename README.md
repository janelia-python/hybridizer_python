hybridizer_python
=================

This Python package (hybridizer) creates a class named Hybridizer to
communcate with and control the Janelia Hybridizer. The hybridizer
controls consist of two modular\_devices, the power\_switch\_controller
to control the valves and the mixed\_signal\_controller to read the
analog signals from the cylinder hall effect sensors. The
bioshake\_device is used to control the heater/shaker.

Authors:

    Peter Polidoro <polidorop@janelia.hhmi.org>

License:

    BSD

##Example Usage


```python
from bioshake_device import BioshakeDevice
dev = BioshakeDevice() # Automatically finds device if one available
dev = BioshakeDevice('/dev/ttyUSB0') # Linux specific port
dev = BioshakeDevice('/dev/tty.usbmodem262471') # Mac OS X specific port
dev = BioshakeDevice('COM3') # Windows specific port
dev.get_description()
dev.set_shake_target_speed(1000)
dev.shake_on()
dev.shake_off()
dev.set_temp_target(45)
dev.temp_on()
dev.temp_off()
devs = BioshakeDevices()  # Automatically finds all available devices
dev = devs[0]
```

##Installation

###Linux and Mac OS X

[Setup Python for Linux](./PYTHON_SETUP_LINUX.md)

[Setup Python for Mac OS X](./PYTHON_SETUP_MAC_OS_X.md)

```shell
mkdir -p ~/virtualenvs/bioshake_device
virtualenv ~/virtualenvs/bioshake_device
source ~/virtualenvs/bioshake_device/bin/activate
pip install bioshake_device
```

###Windows

[Setup Python for Windows](./PYTHON_SETUP_WINDOWS.md)

```shell
virtualenv C:\virtualenvs\bioshake_device
C:\virtualenvs\bioshake_device\Scripts\activate
pip install bioshake_device
```
