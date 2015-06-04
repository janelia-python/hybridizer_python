hybridizer_python
=================

This Python package (hybridizer) creates a class named Hybridizer to
communcate with and control the Janelia Hybridizer. The hybridizer
uses two hardware control devices, the mixed\_signal\_controller
modular\_device, and the bioshake_device. The
mixed\_signal\_controller both switches the valves and reads the
analog signals from the cylinder hall effect sensors. The
bioshake\_device controls the heater/shaker.

Authors::

    Peter Polidoro <polidorop@janelia.hhmi.org>

License::

    BSD

Example Usage::

    from hybridizer import Hybridizer
    hyb = Hybridizer('example_config.yaml')
    hyb.run_protocol()

