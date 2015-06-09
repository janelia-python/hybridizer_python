hybridizer_python
=================

This Python package (hybridizer) creates a class named Hybridizer to
communcate with and control the Janelia Hybridizer. The hybridizer
uses two hardware control devices, the mixed\_signal\_controller
modular\_device, and the bioshake_device. The
mixed\_signal\_controller both switches the valves and reads the
analog signals from the cylinder hall effect sensors. The
bioshake\_device controls the heater/shaker.

Authors:

    Peter Polidoro <polidorop@janelia.hhmi.org>

License:

    BSD

##Example Usage

[Example Config File](./example_config.yaml)

Open a terminal and enter:

```shell
source ~/virtualenvs/hybridizer/bin/activate
cd ~/git/hybridizer_python
ipython
```

In iPython enter:

```python
from hybridizer import Hybridizer
hyb = Hybridizer('example_config.yaml')
hyb.run_protocol()
```

##Installation

###Linux and Mac OS X

[Setup Python for Linux](./PYTHON_SETUP_LINUX.md)

[Setup Python for Mac OS X](./PYTHON_SETUP_MAC_OS_X.md)

Open a terminal and enter:

```shell
mkdir -p ~/virtualenvs/hybridizer
virtualenv ~/virtualenvs/hybridizer
source ~/virtualenvs/hybridizer/bin/activate
pip install hybridizer
```

On linux, you may need to add yourself to the group 'dialout' in order
to have write permissions on the USB port:

Open a terminal and enter:

```shell
sudo usermod -aG dialout $USER
sudo reboot
```

###Windows

[Setup Python for Windows](./PYTHON_SETUP_WINDOWS.md)

Open a terminal and enter:

```shell
virtualenv C:\virtualenvs\hybridizer
C:\virtualenvs\hybridizer\Scripts\activate
pip install hybridizer
```
