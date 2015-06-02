from __future__ import print_function, division
from serial_device2 import find_serial_device_ports
from modular_device import ModularDevices
from bioshake_device import BioshakeDevice
from exceptions import Exception
import os
import time
import yaml
import argparse

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

    hyb = Hybridizer(config_file_path='example_config.yaml')
    hyb.run_protocol()
    '''

    def __init__(self,*args,**kwargs):
        if 'debug' in kwargs:
            self._debug = kwargs['debug']
        else:
            kwargs.update({'debug': DEBUG})
            self._debug = DEBUG
        if 'config_file_path' in kwargs:
            config_file_path = kwargs['config_file_path']
            config_stream = open(config_file_path, 'r')
            self._config = yaml.load(config_stream)
            self._valves = self._config['head']
            self._valves.update(self._config['manifold'])
        else:
            raise HybridizerError('Must provide yaml configuration file path! e.g. hyb = Hybridizer(config_file_path="example_config.yaml")')
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
        self._SHAKE_SPEED_MIN = self._bsc.get_shake_speed_min()
        self._SHAKE_SPEED_MAX = self._bsc.get_shake_speed_max()
        modular_devices = ModularDevices(try_ports=ports)

        try:
            msc_dict = modular_devices['mixed_signal_controller']
        except KeyError:
            raise HybridizerError('Could not find mixed_signal_controller. Check connections and permissions.')
        if len(msc_dict) > 1:
            raise HybridizerError('More than one mixed_signal_controller found. Only one should be connected.')
        self._msc = msc_dict[msc_dict.keys()[0]]
        self._debug_print('Found mixed_signal_controller on port ' + str(self._msc.get_port()))

    def run_protocol(self):
        self._setup()
        for chemical_info in self._config['protocol']:
            self._run_chemical(chemical_info['chemical'],
                               chemical_info['dispense_count'],
                               chemical_info['shake_speed'],
                               chemical_info['shake_duration'])

    def _setup(self):
        self._bsc.reset_device()
        self._set_all_valves_off()
        self._set_valves_on(['primer','quad1','quad2','quad3','quad4','quad5','quad6'])
        self._debug_print('setting up for ' + str(self._config['setup_duration']) + 's...')
        time.sleep(self._config['setup_duration'])
        self._set_all_valves_off()

    def _run_chemical(self,chemical,dispense_count=1,shake_speed=None,shake_duration=None):
        if (chemical not in self._valves):
            raise HybridizerError(chemical + ' is not listed as part of the manifold in the config file!')
        self._debug_print('running ' + chemical + '...')
        self._set_valves_on(['primer',chemical,'system'])
        self._debug_print('priming ' + chemical + ' for ' + str(self._config['prime_duration']) + 's...')
        time.sleep(self._config['prime_duration'])
        self._set_valve_off('system')
        self._debug_print('aspirating ' + chemical + ' for ' + str(self._config['prime_aspirate_duration']) + 's...')
        time.sleep(self._config['prime_aspirate_duration'])
        self._set_valve_off('primer')
        self._set_valves_on(['quad1','quad2','quad3','quad4','quad5','quad6','aspirate'])
        for i in range(dispense_count):
            self._set_valve_on('system')
            self._debug_print('loading ' + chemical + ' into syringes for ' + str(self._config['load_duration']) + 's ' + str(i+1) + '/' + str(dispense_count) + '...')
            time.sleep(self._config['load_duration'])
            self._set_valve_off('system')
            self._debug_print('dispensing ' + chemical + ' into microplate for ' + str(self._config['dispense_duration']) + 's ' + str(i+1) + '/' + str(dispense_count) + '...')
            time.sleep(self._config['dispense_duration'])
        self._set_valves_off(['quad1','quad2','quad3','quad4','quad5','quad6'])
        if not ((shake_duration is None) or (shake_duration <= 0)):
            if (shake_speed is None) or (shake_speed < self._SHAKE_SPEED_MIN):
                shake_speed = 0
            elif shake_speed > self._SHAKE_SPEED_MAX:
                shake_speed = self._SHAKE_SPEED_MAX
            self._debug_print('shaking at ' + str(shake_speed) + 'rpm for ' + str(shake_duration) + 's...')
            if shake_speed != 0:
                self._bsc.shake_on(shake_speed)
            time.sleep(shake_duration)
            if shake_speed != 0:
                self._bsc.shake_off()
        self._set_valve_off('aspirate')
        self._debug_print('aspirating ' + chemical + ' from microplate for ' + str(self._config['chemical_aspirate_duration']) + 's...')
        time.sleep(self._config['chemical_aspirate_duration'])
        self._set_all_valves_off()
        self._debug_print(chemical + ' finished!')

    def _debug_print(self, *args):
        if self._debug:
            print(*args)

    def _set_valve_on(self, valve_key):
        try:
            valve = self._valves[valve_key]
            channels = [valve['channel']]
            self._msc.set_channels_on(channels)
        except KeyError:
            raise HybridizerError('Unknown valve: ' + str(valve_key) + '. Check yaml config file for errors.')

    def _set_valves_on(self, valve_keys):
        try:
            channels = [self._valves[valve_key]['channel'] for valve_key in valve_keys]
            self._msc.set_channels_on(channels)
        except KeyError:
            raise HybridizerError('Unknown valve: ' + str(valve_key) + '. Check yaml config file for errors.')

    def _set_valve_off(self, valve_key):
        try:
            valve = self._valves[valve_key]
            channels = [valve['channel']]
            self._msc.set_channels_off(channels)
        except KeyError:
            raise HybridizerError('Unknown valve: ' + str(valve_key) + '. Check yaml config file for errors.')

    def _set_valves_off(self, valve_keys):
        try:
            channels = [self._valves[valve_key]['channel'] for valve_key in valve_keys]
            self._msc.set_channels_off(channels)
        except KeyError:
            raise HybridizerError('Unknown valve: ' + str(valve_key) + '. Check yaml config file for errors.')

    def _set_all_valves_off(self):
        valve_keys = self._get_valves()
        self._set_valves_off(valve_keys)

    def _get_valves(self):
        valve_keys = self._valves.keys()
        valve_keys.sort()
        return valve_keys

    def _set_valve_on_until(self, valve_key, percent):
        try:
            valve = self._valves[valve_key]
            channels = [valve['channel']]
            ain = valve['analog_input']
            set_until_index = self._msc.set_channels_on_until(channels,ain,percent)
            while not self._msc.is_set_until_complete(set_until_index):
                percent_current = self._msc.get_analog_input(ain)
                self._debug_print(str(valve_key) + ' is at ' + str(percent_current) + '%, waiting to reach ' + str(percent) + '%')
                time.sleep(1)
            self._msc.remove_set_until(set_until_index)
        except KeyError:
            raise HybridizerError('Unknown valve: ' + str(valve_key) + ', or valve does not have analog_input. Check yaml config file for errors.')

    def _set_valves_on_until_serial(self, valve_keys, percent):
        for valve_key in valve_keys:
            self._set_valve_on_until(valve_key,percent)


# -----------------------------------------------------------------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("config_file_path", help="Path to yaml config file.")

    args = parser.parse_args()
    config_file_path = args.config_file_path
    print("Config File Path: {0}".format(config_file_path))

    debug = True
    hyb = Hybridizer(debug=debug,config_file_path=config_file_path)
    hyb.run_protocol()
