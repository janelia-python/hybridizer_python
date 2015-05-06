hybridizer_python
=================

This Python package (hybridizer) creates a class named Hybridizer to
communcate with and control the Janelia Hybridizer. The hybridizer
controls consist of two modular_devices, the power_switch_controller
to control the valves and the mixed_signal_controller to read the
analog signals from the cylinder hall effect sensors. The
bioshake_device is used to control the heater/shaker.

Authors::

    Peter Polidoro <polidorop@janelia.hhmi.org>

License::

    BSD

Example Usage::

    from hybridizer import Hybridizer
    hyb = Hybridizer() #Automatically finds devices, may take some time

