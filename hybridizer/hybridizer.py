from __future__ import print_function, division
from serial_device2 import find_serial_device_ports
from modular_device import ModularDevices
from bioshake_device import BioshakeDevice
from exceptions import Exception
import os
import time

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
            'asp' : {
                'channel' : 8,
            },
            'red' : {
                'channel' : 9,
            },
            'green' : {
                'channel' : 9,
            },
            'yellow' : {
                'channel' : 10,
            },
            'blue' : {
                'channel' : 11,
            },
            'wash' : {
                'channel' : 13,
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

    def set_valves_on(self, valve_key_list):
        try:
            channels = [self._valves[valve_key]['channel'] for valve_key in valve_key_list]
            self._msc.set_channels_on(channels)
        except KeyError:
            raise HybridizerError('Unknown valve key.')

    def set_valve_off(self, valve_key):
        try:
            valve = self._valves[valve_key]
            channels = [valve['channel']]
            self._msc.set_channels_off(channels)
        except KeyError:
            raise HybridizerError('Unknown valve key.')

    def set_valves_off(self, valve_key_list):
        try:
            channels = [self._valves[valve_key]['channel'] for valve_key in valve_key_list]
            self._msc.set_channels_off(channels)
        except KeyError:
            raise HybridizerError('Unknown valve key.')

    def set_all_valves_off(self):
        valve_keys = self.get_valves()
        set_valves_off(valve_keys)

    def get_valves(self):
        valve_keys = self._valves.keys()
        valve_keys.sort()
        return valve_keys

    def set_valve_on_until(self, valve_key, percent):
        try:
            valve = self._valves[valve_key]
            channels = [valve['channel']]
            ain = valve['analog_input']
            set_until_index = self._msc.set_channels_on_until(channels,ain,percent)
            while not self._msc.is_set_until_complete(set_until_index):
                percent_current = self._msc.get_analog_input(ain)
                print(str(valve_key) + ' is at ' + str(percent_current) + '%, waiting to reach ' + str(percent) + '%')
                time.sleep(1)
            self._msc.remove_set_until(set_until_index)
        except KeyError:
            raise HybridizerError('Unknown valve key or valve does not have analog_input.')

    def set_valves_on_until_serial(self, valve_key_list, percent):
        for valve_key in valve_key_list:
            self.set_valve_on_until(valve_key,percent)

    def run(self,valve_key):
        print('running ' + valve_key + '...')
        self.set_valves_on(['primer',valve_key])
        self.set_valve_on('system')
        print('priming ' + valve_key + '...')
        time.sleep(5)
        self.set_valve_off('system')
        print('aspirating ' + valve_key + '...')
        time.sleep(5)
        self.set_valve_off('primer')
        self.set_valves_on(['quad1','quad2','quad3','quad4','quad5','quad6','asp'])
        self.set_valve_on('system')
        print('loading ' + valve_key + ' into syringes...')
        time.sleep(20)
        self.set_valve_off('system')
        print('dispensing ' + valve_key + ' into microplate...')
        time.sleep(10)
        self.bsc.shake_on()
        print('shaking...')
        time.sleep(10)
        self.bsc.shake_off()
        self.set_valve_off('asp')
        print('aspirating ' + valve_key + ' from microplate...')
        time.sleep(20)
        self.set_valve_off(valve_key)
        print(valve_key + ' finished!')

# -----------------------------------------------------------------------------------------
if __name__ == '__main__':

    debug = True
    hyb = Hybridizer(debug=debug)
    hyb.get_valves()
