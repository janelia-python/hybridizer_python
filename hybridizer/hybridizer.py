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

    _VALVE_HEAD_SPIKE_DUTY_CYCLE = 50
    _VALVE_HEAD_SPIKE_DURATION = 20
    _VALVE_HEAD_HOLD_DUTY_CYCLE = 14
    _VALVE_SYSTEM_SPIKE_DUTY_CYCLE = 50
    _VALVE_SYSTEM_SPIKE_DURATION = 10
    _VALVE_SYSTEM_HOLD_DUTY_CYCLE = 25
    _VALVE_MANIFOLD_SPIKE_DUTY_CYCLE = 50
    _VALVE_MANIFOLD_SPIKE_DURATION = 10
    _VALVE_MANIFOLD_HOLD_DUTY_CYCLE = 25
    _RELAY_START_DELAY = 200

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
        self._debug_print('Found power_switch_controller on port ' + str(self.psc.get_port()))

        try:
            msc_dict = modular_devices['mixed_signal_controller']
        except KeyError:
            raise HybridizerError('Could not find mixed_signal_controller. Check connections and permissions.')
        if len(msc_dict) > 1:
            raise HybridizerError('More than one mixed_signal_controller found. Only one should be connected.')
        self.msc = msc_dict[msc_dict.keys()[0]]
        self._debug_print('Found mixed_signal_controller on port ' + str(self.msc.get_port()))

        self.valves = {
            'primer' : {
                'channel' : 0,
                'type' : 'head',
                'analog_input' : 0,
                'pulse_wave_index' : None,
            },
            'quad1' : {
                'channel' : 1,
                'type' : 'head',
                'analog_input' : 1,
                'pulse_wave_index' : None,
            },
            'quad2' : {
                'channel' : 2,
                'type' : 'head',
                'analog_input' : 2,
                'pulse_wave_index' : None,
            },
            'quad3' : {
                'channel' : 3,
                'type' : 'head',
                'analog_input' : 3,
                'pulse_wave_index' : None,
            },
            'quad4' : {
                'channel' : 4,
                'type' : 'head',
                'analog_input' : 4,
                'pulse_wave_index' : None,
            },
            'quad5' : {
                'channel' : 5,
                'type' : 'head',
                'analog_input' : 5,
                'pulse_wave_index' : None,
            },
            'quad6' : {
                'channel' : 6,
                'type' : 'head',
                'analog_input' : 6,
                'pulse_wave_index' : None,
            },
            'system' : {
                'channel' : 7,
                'type' : 'system',
                'pulse_wave_index' : None,
            },
        }

    def _debug_print(self, *args):
        if self.debug:
            print(*args)

    def _get_spike_and_hold_values(self, valve_type):
        if valve_type == 'head':
            spike_duty_cycle = self._VALVE_HEAD_SPIKE_DUTY_CYCLE
            spike_duration = self._VALVE_HEAD_SPIKE_DURATION
            hold_duty_cycle = self._VALVE_HEAD_HOLD_DUTY_CYCLE
        elif valve_type == 'system':
            spike_duty_cycle = self._VALVE_SYSTEM_SPIKE_DUTY_CYCLE
            spike_duration = self._VALVE_SYSTEM_SPIKE_DURATION
            hold_duty_cycle = self._VALVE_SYSTEM_HOLD_DUTY_CYCLE
        elif valve_type == 'manifold':
            spike_duty_cycle = self._VALVE_MANIFOLD_SPIKE_DUTY_CYCLE
            spike_duration = self._VALVE_MANIFOLD_SPIKE_DURATION
            hold_duty_cycle = self._VALVE_MANIFOLD_HOLD_DUTY_CYCLE
        else:
            raise HybridizerError('Unknown valve type.')
        return (spike_duty_cycle,spike_duration,hold_duty_cycle)

    def set_valve_on(self, valve_key):
        try:
            valve = self.valves[valve_key]
            if valve['pulse_wave_index'] is None:
                channels = [valve['channel']]
                delay = self._RELAY_START_DELAY
                valve_type = valve['type']
                (spike_duty_cycle,spike_duration,hold_duty_cycle) = self._get_spike_and_hold_values(valve_type)
                pulse_wave_index = self.psc.start_spike_and_hold(channels,delay,spike_duty_cycle,spike_duration,hold_duty_cycle)
                valve['pulse_wave_index'] = pulse_wave_index
        except KeyError:
            raise HybridizerError('Unknown valve key.')

    def set_valve_off(self, valve_key):
        try:
            valve = self.valves[valve_key]
            if valve['pulse_wave_index'] is not None:
                self.psc.stop_pulse_wave(valve['pulse_wave_index'])
                valve['pulse_wave_index'] = None
        except KeyError:
            raise HybridizerError('Invalid valve key.')

    def set_all_valves_off(self):
        self.psc.stop_all_pulses()
        for valve_key in self.valves:
            self.valves[valve_key]['pulse_wave_index'] = None

    def test(self):
        pass
        # self._debug_print(self.psc.get_methods())
        # self._debug_print(self.msc.get_methods())
        self._debug_print(self.valves)



# -----------------------------------------------------------------------------------------
if __name__ == '__main__':

    debug = True
    hyb = Hybridizer(debug=debug)
    hyb.test()
