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
from hybridizer import Hybridizer
hyb = Hybridizer()
```

##Installation

###Linux and Mac OS X

[Setup Python for Linux](./PYTHON_SETUP_LINUX.md)

[Setup Python for Mac OS X](./PYTHON_SETUP_MAC_OS_X.md)

```shell
mkdir -p ~/virtualenvs/hybridizer
virtualenv ~/virtualenvs/hybridizer
source ~/virtualenvs/hybridizer/bin/activate
pip install hybridizer
```

###Windows

[Setup Python for Windows](./PYTHON_SETUP_WINDOWS.md)

```shell
virtualenv C:\virtualenvs\hybridizer
C:\virtualenvs\hybridizer\Scripts\activate
pip install hybridizer
```
