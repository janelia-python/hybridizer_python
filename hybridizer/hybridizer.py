from __future__ import print_function, division
from serial_device2 import find_serial_device_ports
from modular_device import ModularDevices
from bioshake_device import BioshakeDevice
from exceptions import Exception
import os

try:
    from pkg_resources import get_distribution, DistributionNotFound
    _dist = get_distribution('hybridizer')
    # Normalize case for Windows systems
    dist_loc = os.path.normcase(_dist.location)
    here = os.path.normcase(__file__)
    if not here.startswith(os.path.join(dist_loc, 'hybridizer')):
        # not installed, but there is another version that *is*
        raise DistributionNotFound
except (ImportError,DistributionNotFound):
    __version__ = None
else:
    __version__ = _dist.version


DEBUG = True
BAUDRATE = 9600


class HybridizerError(Exception):
    def __init__(self,value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class Hybridizer(object):
    '''
    '''
    def __init__(self,*args,**kwargs):
        if 'debug' in kwargs:
            self._debug = kwargs['debug']
        else:
            kwargs.update({'debug': DEBUG})
            self._debug = DEBUG
        ports = find_serial_device_ports(debug=self._debug)
        self._debug_print('Found serial devices on ports ' + str(ports))
        self._debug_print('Identifying connected devices (may take some time)...')
        try:
            self.bsc = BioshakeDevice()
        except RuntimeError:
            # try one more time
            self.bsc = BioshakeDevice()
        self._debug_print('Found bioshake device on port ' + str(self.bsc.get_port()))
        ports.remove(self.bsc.get_port())
        modular_devices = ModularDevices(try_ports=ports)

        try:
            msc_dict = modular_devices['mixed_signal_controller']
        except KeyError:
            raise HybridizerError('Could not find mixed_signal_controller. Check connections and permissions.')
        if len(msc_dict) > 1:
            raise HybridizerError('More than one mixed_signal_controller found. Only one should be connected.')
        self._msc = msc_dict[msc_dict.keys()[0]]
        self._debug_print('Found mixed_signal_controller on port ' + str(self._msc.get_port()))

        self._valves = {
            'primer' : {
                'channel' : 0,
                'analog_input' : 0,
            },
            'quad1' : {
                'channel' : 1,
                'analog_input' : 1,
            },
            'quad2' : {
                'channel' : 2,
                'analog_input' : 2,
            },
            'quad3' : {
                'channel' : 3,
                'analog_input' : 3,
            },
            'quad4' : {
                'channel' : 4,
                'analog_input' : 4,
            },
            'quad5' : {
                'channel' : 5,
                'analog_input' : 5,
            },
            'quad6' : {
                'channel' : 6,
                'analog_input' : 6,
            },
            'system' : {
                'channel' : 7,
            },
        }

    def _debug_print(self, *args):
        if self._debug:
            print(*args)

    def set_valve_on(self, valve_key):
        try:
            valve = self._valves[valve_key]
            channels = [valve['channel']]
            self._msc.set_channels_on(channels)
        except KeyError:
            raise HybridizerError('Unknown valve key.')

    def set_valve_off(self, valve_key):
        try:
            valve = self._valves[valve_key]
            channels = [valve['channel']]
            self._msc.set_channels_off(channels)
        except KeyError:
            raise HybridizerError('Invalid valve key.')

    def set_all_valves_off(self):
        for valve in self._valves:
            self.set_valve_off(valve)

    def get_valves(self):
        valve_keys = self._valves.keys()
        valve_keys.sort()
        return valve_keys


# -----------------------------------------------------------------------------------------
if __name__ == '__main__':

    debug = True
    hyb = Hybridizer(debug=debug)
    hyb.get_valves()
