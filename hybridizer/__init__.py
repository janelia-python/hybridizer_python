'''
This Python package (hybridizer) creates a class named Hybridizer to
communcate with and control the Janelia Hybridizer. The hybridizer
uses two hardware control devices, the mixed_signal_controller
modular_device, and the bioshake_device. The
mixed_signal_controller both switches the valves and reads the
analog signals from the cylinder hall effect sensors. The
bioshake_device controls the heater/shaker.
Example Usage:

hyb = Hybridizer('example_config.yaml')
hyb.run_protocol()
'''
from hybridizer import Hybridizer, HybridizerError
