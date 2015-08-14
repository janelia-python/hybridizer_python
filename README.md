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
hybridzer example_calibration.yaml example_config.yaml
```

##Installation

####Debian-based Linux Install Dependencies

Open a terminal and enter:

```shell
sudo apt-get install git python-pip python-virtualenv python-dev build-essential -y
```

###Linux and Mac OS X

[Setup Python for Linux](./PYTHON_SETUP_LINUX.md)

[Setup Python for Mac OS X](./PYTHON_SETUP_MAC_OS_X.md)

Open a terminal and enter:

```shell
mkdir ~/git
cd ~/git
git clone https://github.com/janelia-idf/hybridizer_config.git
git clone https://github.com/janelia-idf/hybridizer.git
cd hybridizer
git submodule init
git submodule update
cd ~
mkdir ~/virtualenvs
cd ~/virtualenvs
virtualenv hybridizer
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
pip install ipython
pip install hybridizier
```
