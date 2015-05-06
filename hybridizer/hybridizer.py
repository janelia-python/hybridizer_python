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

    _VALVE_SUPPLY_VOLTAGE = 24.0
    _VALVE_HEAD_SPIKE_VOLTAGE = 12.0
    _VALVE_HEAD_SPIKE_DURATION = 10
    _VALVE_HEAD_HOLD_VOLTAGE = 3.5
    _VALVE_SYSTEM_SPIKE_VOLTAGE = 12.0
    _VALVE_SYSTEM_SPIKE_DURATION = 10
    _VALVE_SYSTEM_HOLD_VOLTAGE = 6.0
    _VALVE_MANIFOLD_SPIKE_VOLTAGE = 12.0
    _VALVE_MANIFOLD_SPIKE_DURATION = 10
    _VALVE_MANIFOLD_HOLD_VOLTAGE = 6.0

    def __init__(self,*args,**kwargs):
        if 'debug' in kwargs:
            self.debug = kwargs['debug']
        else:
            kwargs.update({'debug': DEBUG})
            self.debug = DEBUG
        ports = find_serial_device_ports(debug=self.debug)
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
            psc_dict = modular_devices['power_switch_controller']
        except KeyError:
            raise HybridizerError('Could not find power_switch_controller. Check connections and permissions.')
        if len(psc_dict) > 1:
            raise HybridizerError('More than one power_switch_controller found. Only one should be connected.')
        self.psc = psc_dict[psc_dict.keys()[0]]

        try:
            msc_dict = modular_devices['mixed_signal_controller']
        except KeyError:
            raise HybridizerError('Could not find mixed_signal_controller. Check connections and permissions.')
        if len(msc_dict) > 1:
            raise HybridizerError('More than one mixed_signal_controller found. Only one should be connected.')
        self.msc = msc_dict[msc_dict.keys()[0]]

    def _debug_print(self, *args):
        if self.debug:
            print(*args)

    def test(self):
        pass
        self._debug_print(self.psc.get_methods())
        self._debug_print(self.msc.get_methods())



# -----------------------------------------------------------------------------------------
if __name__ == '__main__':

    debug = True
    hyb = Hybridizer(debug=debug)
    hyb.test()
