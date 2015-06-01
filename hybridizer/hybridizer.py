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
    This Python package (hybridizer) creates a class named Hybridizer to
    communcate with and control the Janelia Hybridizer. The hybridizer
    uses two hardware control devices, the mixed_signal_controller
    modular_device, and the bioshake_device. The
    mixed_signal_controller both switches the valves and reads the
    analog signals from the cylinder hall effect sensors. The
    bioshake_device controls the heater/shaker.
    Example Usage:

    hyb = Hybridizer() #Automatically finds devices, may take some time
    hyb.setup()
    hyb.run_chemicals()
    '''
    _SETUP_DURATION = 10
    _PRIME_DURATION = 10
    _PRIME_ASPIRATE_DURATION = 5
    _LOAD_DURATION = 20
    _DISPENSE_DURATION = 10
    _SHAKE_SPEED = 200
    _SHAKE_DURATION = 10
    _CHEMICAL_ASPIRATE_DURATION = 20
    _CHEMICALS = ['red','green','blue','yellow','wash']
    _VALVES = {
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
            'channel' : 10,
        },
        'yellow' : {
            'channel' : 11,
        },
        'blue' : {
            'channel' : 12,
        },
        'wash' : {
            'channel' : 13,
        },
    }

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
            self._bsc = BioshakeDevice()
        except RuntimeError:
            # try one more time
            self._bsc = BioshakeDevice()
        self._debug_print('Found bioshake device on port ' + str(self._bsc.get_port()))
        ports.remove(self._bsc.get_port())
        modular_devices = ModularDevices(try_ports=ports)

        try:
            msc_dict = modular_devices['mixed_signal_controller']
        except KeyError:
            raise HybridizerError('Could not find mixed_signal_controller. Check connections and permissions.')
        if len(msc_dict) > 1:
            raise HybridizerError('More than one mixed_signal_controller found. Only one should be connected.')
        self._msc = msc_dict[msc_dict.keys()[0]]
        self._debug_print('Found mixed_signal_controller on port ' + str(self._msc.get_port()))

    def setup(self):
        self._set_all_valves_off()
        self._set_valves_on(['primer','quad1','quad2','quad3','quad4','quad5','quad6'])
        print('setting up for ' + str(self._SETUP_DURATION) + 's...')
        time.sleep(self._SETUP_DURATION)
        self._set_all_valves_off()

    def get_chemicals(self):
        return self._CHEMICALS

    def run_chemical(self,chemical):
        if (chemical not in self._CHEMICALS) or (chemical not in self._VALVES):
            raise HybridizerError('Unknown chemical')
        print('running ' + chemical + '...')
        self._set_valves_on(['primer',chemical])
        self._set_valve_on('system')
        print('priming ' + chemical + ' for ' + str(self._PRIME_DURATION) + 's...')
        time.sleep(self._PRIME_DURATION)
        self._set_valve_off('system')
        print('aspirating ' + chemical + ' for ' + str(self._PRIME_ASPIRATE_DURATION) + 's...')
        time.sleep(self._PRIME_ASPIRATE_DURATION)
        self._set_valve_off('primer')
        self._set_valves_on(['quad1','quad2','quad3','quad4','quad5','quad6','asp'])
        self._set_valve_on('system')
        print('loading ' + chemical + ' into syringes for ' + str(self._LOAD_DURATION) + 's...')
        time.sleep(self._LOAD_DURATION)
        self._set_valve_off('system')
        print('dispensing ' + chemical + ' into microplate for ' + str(self._DISPENSE_DURATION) + 's...')
        time.sleep(self._DISPENSE_DURATION)
        self._set_valves_off(['quad1','quad2','quad3','quad4','quad5','quad6'])
        self._bsc.shake_on(self._SHAKE_SPEED)
        print('shaking for ' + str(self._SHAKE_DURATION) + 's...')
        time.sleep(self._SHAKE_DURATION)
        self._bsc.shake_off()
        self._set_valve_off('asp')
        print('aspirating ' + chemical + ' from microplate for ' + str(self._CHEMICAL_ASPIRATE_DURATION) + 's...')
        time.sleep(self._CHEMICAL_ASPIRATE_DURATION)
        self._set_all_valves_off()
        print(chemical + ' finished!')

    def run_chemicals(self):
        chemicals = ['wash','red','green','blue','yellow','wash','wash']
        for chemical in chemicals:
            self.run_chemical(chemical)

    def _debug_print(self, *args):
        if self._debug:
            print(*args)

    def _set_valve_on(self, valve_key):
        try:
            valve = self._VALVES[valve_key]
            channels = [valve['channel']]
            self._msc.set_channels_on(channels)
        except KeyError:
            raise HybridizerError('Unknown valve key.')

    def _set_valves_on(self, valve_keys):
        try:
            channels = [self._VALVES[valve_key]['channel'] for valve_key in valve_keys]
            self._msc.set_channels_on(channels)
        except KeyError:
            raise HybridizerError('Unknown valve key.')

    def _set_valve_off(self, valve_key):
        try:
            valve = self._VALVES[valve_key]
            channels = [valve['channel']]
            self._msc.set_channels_off(channels)
        except KeyError:
            raise HybridizerError('Unknown valve key.')

    def _set_valves_off(self, valve_keys):
        try:
            channels = [self._VALVES[valve_key]['channel'] for valve_key in valve_keys]
            self._msc.set_channels_off(channels)
        except KeyError:
            raise HybridizerError('Unknown valve key.')

    def _set_all_valves_off(self):
        valve_keys = self._get_valves()
        self._set_valves_off(valve_keys)

    def _get_valves(self):
        valve_keys = self._VALVES.keys()
        valve_keys.sort()
        return valve_keys

    def _set_valve_on_until(self, valve_key, percent):
        try:
            valve = self._VALVES[valve_key]
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

    def _set_valves_on_until_serial(self, valve_keys, percent):
        for valve_key in valve_keys:
            self._set_valve_on_until(valve_key,percent)


# -----------------------------------------------------------------------------------------
if __name__ == '__main__':

    debug = True
    hyb = Hybridizer(debug=debug)
