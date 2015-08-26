from __future__ import print_function, division
from serial_device2 import find_serial_device_ports
from modular_device import ModularDevices
from bioshake_device import BioshakeDevice, BioshakeError
from exceptions import Exception
import os
import time
import yaml
import argparse
from numpy.polynomial.polynomial import polyfit,polyadd,Polynomial
import csv
import copy
import numpy
import sys

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

    hyb = Hybridizer('example_calibration.yaml','example_config.yaml')
    hyb.run_protocol()
    '''

    def __init__(self,
                 calibration_file_path,
                 config_file_path,
                 mixed_signal_controller=True,
                 bioshake_device=True,
                 *args,**kwargs):
        if 'debug' in kwargs:
            self._debug = kwargs['debug']
        else:
            kwargs.update({'debug': DEBUG})
            self._debug = DEBUG
        self._using_msc = mixed_signal_controller
        self._using_bsc = bioshake_device
        with open(calibration_file_path,'r') as calibration_stream:
            self._calibration = yaml.load(calibration_stream)
        with open(config_file_path,'r') as config_stream:
            self._config = yaml.load(config_stream)
        # check to see if user switched config and calibration files
        if ('head' in self._calibration) and ('quad1' in self._config):
            calibration = self._config
            self._config = self._calibration
            self._calibration = calibration
        self._valves = self._config['head']
        self._valves.update(self._config['manifold'])
        if self._using_msc or self._using_bsc:
            ports = find_serial_device_ports(debug=self._debug)
            self._debug_print('Found serial devices on ports ' + str(ports))
            self._debug_print('Identifying connected devices (may take some time)...')
        if self._using_bsc:
            try:
                self._bsc = BioshakeDevice()
            except RuntimeError:
                # try one more time
                self._bsc = BioshakeDevice()
            self._debug_print('Found bioshake device on port ' + str(self._bsc.get_port()))
            ports.remove(self._bsc.get_port())
            self._SHAKE_SPEED_MIN = self._bsc.get_shake_speed_min()
            self._SHAKE_SPEED_MAX = self._bsc.get_shake_speed_max()
        if self._using_msc:
            modular_devices = ModularDevices(try_ports=ports)

            try:
                msc_dict = modular_devices['mixed_signal_controller']
            except KeyError:
                raise HybridizerError('Could not find mixed_signal_controller. Check connections and permissions.')
            if len(msc_dict) > 1:
                raise HybridizerError('More than one mixed_signal_controller found. Only one should be connected.')
            self._msc = msc_dict[msc_dict.keys()[0]]
            self._debug_print('Found mixed_signal_controller on port ' + str(self._msc.get_port()))

    def _setup(self):
        if self._using_bsc:
            self._bsc.reset_device()
        self._set_all_valves_off()
        self._set_valves_on(['primer','quad1','quad2','quad3','quad4','quad5','quad6'])
        self._debug_print('setting up for ' + str(self._config['setup_duration']) + 's...')
        time.sleep(self._config['setup_duration'])
        self._set_all_valves_off()
        self._debug_print('setup finished!')

    def prime_system(self):
        self._setup()
        self._debug_print('priming system...')
        manifold = self._config['manifold']
        chemicals = manifold.keys()
        try:
            chemicals.remove('aspirate')
        except ValueError:
            pass
        try:
            chemicals.remove('separate')
        except ValueError:
            pass
        self._set_valves_on(['separate','aspirate'])
        for chemical in chemicals:
            self._prime_chemical(chemical,self._config['system_prime_count'])
        self._set_all_valves_off()
        self._debug_print('priming finished!')

    def run_protocol(self):
        self._setup()
        self.protocol_start_time = time.time()
        self._debug_print('running protocol...')
        self._set_valves_on(['separate','aspirate'])
        for chemical_info in self._config['protocol']:
            chemical = chemical_info['chemical']
            try:
                prime_count = chemical_info['prime_count']
            except KeyError:
                prime_count = 1
            try:
                dispense_volume = chemical_info['dispense_volume']
            except KeyError:
                dispense_volume = 2
            try:
                shake_speed = chemical_info['shake_speed']
            except KeyError:
                shake_speed = None
            try:
                shake_duration = chemical_info['shake_duration']
            except KeyError:
                shake_duration = None
            try:
                post_shake_duration = chemical_info['post_shake_duration']
            except KeyError:
                post_shake_duration = 0
            try:
                separate = chemical_info['separate']
            except KeyError:
                separate = False
            try:
                aspirate = chemical_info['aspirate']
            except KeyError:
                aspirate = True
            try:
                temperature = chemical_info['temperature']
            except KeyError:
                temperature = None
            try:
                repeat = chemical_info['repeat']
            except KeyError:
                repeat = 0
            self._run_chemical(chemical,
                               prime_count,
                               dispense_volume,
                               shake_speed,
                               shake_duration,
                               post_shake_duration,
                               separate,
                               aspirate,
                               temperature,
                               repeat)
        self._set_all_valves_off()
        self.protocol_end_time = time.time()
        protocol_run_time = self.protocol_end_time - self.protocol_start_time
        self._debug_print('protocol finished! it took ' + str(round(protocol_run_time/60)) + ' mins to run.')

    def _prime_chemical(self,chemical,prime_count):
        if prime_count > 0:
            self._set_valve_on(chemical)
        for i in range(prime_count):
            self._set_valves_on(['primer','system'])
            self._debug_print('priming ' + chemical + ' for ' + str(self._config['prime_duration']) + 's ' + str(i+1) + '/' + str(prime_count) + '...')
            time.sleep(self._config['prime_duration'])
            self._set_valves_off(['system'])
            self._debug_print('emptying ' + chemical + ' for ' + str(self._config['prime_aspirate_duration']) + 's ' + str(i+1) + '/' + str(prime_count) + '...')
            time.sleep(self._config['prime_aspirate_duration'])
            self._set_valve_off('primer')
        if prime_count > 0:
            self._set_valve_off(chemical)

    def _run_chemical(self,
                      chemical,
                      prime_count=1,
                      dispense_volume=2,
                      shake_speed=None,
                      shake_duration=None,
                      post_shake_duration=0,
                      separate=False,
                      aspirate=True,
                      temp_target=None,
                      repeat=0):
        if (chemical not in self._valves):
            raise HybridizerError(chemical + ' is not listed as part of the manifold in the config file!')
        if repeat < 0:
            repeat = 0
        run_count = repeat + 1
        if self._using_bsc and (temp_target is not None):
            self._debug_print('turning on temperature control for ' + chemical + '...')
            self._bsc.temp_on(temp_target)
            temp_actual = self._bsc.get_temp_actual()
            self._debug_print('actual temperature: ' + str(temp_actual) + ', target temperature: ' + str(temp_target))
            while abs(temp_target - temp_actual) > 0.5:
                time.sleep(1)
                temp_actual = self._bsc.get_temp_actual()
                self._debug_print('actual temperature: ' + str(temp_actual) + ', target temperature: ' + str(temp_target))
            self._debug_print()
        self._prime_chemical(chemical,prime_count)
        for run in range(run_count):
            self._debug_print('running ' + chemical + ' ' + str(run+1) + '/' + str(run_count) + '...')
            self._set_valve_on(chemical)
            self._set_valve_on('aspirate')
            # self._set_valves_on(['quad1','quad2','quad3','quad4','quad5','quad6','aspirate'])
            valves = ['quad1','quad2','quad3','quad4','quad5','quad6']
            self._dispense_volume(valves,dispense_volume)
            # for i in range(dispense_volume):
            #     if i > 0:
            #         dispense_shake_duration = self._config['inter_dispense_shake_duration']
            #         if dispense_shake_duration < self._config['shake_duration_min']:
            #             dispense_shake_duration = self._config['shake_duration_min']
            #         dispense_shake_speed = self._shake_on(self._config['inter_dispense_shake_speed'])
            #         self._debug_print('shaking at ' + str(dispense_shake_speed) + 'rpm for ' + str(dispense_shake_duration) + 's...')
            #         time.sleep(dispense_shake_duration)
            #         self._shake_off(dispense_shake_speed)
            #     self._set_valve_on('system')
            #     self._debug_print('loading ' + chemical + ' into syringes for ' + str(self._config['load_duration']) + 's ' + str(i+1) + '/' + str(dispense_volume) + '...')
            #     time.sleep(self._config['load_duration'])
            #     self._set_valve_off('system')
            #     self._debug_print('dispensing ' + chemical + ' into microplate for ' + str(self._config['dispense_duration']) + 's ' + str(i+1) + '/' + str(dispense_volume) + '...')
            #     time.sleep(self._config['dispense_duration'])
            # self._set_valves_off(['quad1','quad2','quad3','quad4','quad5','quad6'])
            if not ((shake_duration is None) or (shake_duration <= 0)):
                actual_shake_duration = shake_duration
                if shake_duration < self._config['shake_duration_min']:
                    actual_shake_duration = self._config['shake_duration_min']
                actual_shake_speed = self._shake_on(shake_speed)
                self._debug_print('shaking at ' + str(actual_shake_speed) + 'rpm for ' + str(actual_shake_duration) + 's...')
                time.sleep(actual_shake_duration)
                self._shake_off(actual_shake_speed)
            if (post_shake_duration > 0):
                self._debug_print('waiting post shake for ' + str(post_shake_duration) + 's...')
                time.sleep(post_shake_duration)
            if separate:
                separate_shake_speed = self._shake_on(self._config['separate_shake_speed'])
                self._set_valve_off('separate')
                self._debug_print('separating ' + chemical + ' for ' + str(self._config['chemical_separate_duration']) + 's...')
                time.sleep(self._config['chemical_separate_duration'])
                self._set_valve_on('separate')
                self._shake_off(separate_shake_speed)
            if aspirate:
                aspirate_shake_speed = self._shake_on(self._config['aspirate_shake_speed'])
                self._set_valve_off('aspirate')
                self._debug_print('aspirating ' + chemical + ' from microplate for ' + str(self._config['chemical_aspirate_duration']) + 's...')
                time.sleep(self._config['chemical_aspirate_duration'])
                self._set_valve_on('aspirate')
                self._shake_off(aspirate_shake_speed)
            self._set_valve_off(chemical)
            self._debug_print(chemical + ' finished!')
            self._debug_print()
        if self._using_bsc and (temp_target is not None):
            self._debug_print('turning off temperature control for ' + chemical + '...')
            try:
                self._bsc.temp_off()
            except BioshakeError:
                pass
            self._debug_print()

    def _shake_on(self,shake_speed):
        if self._using_bsc:
            if (shake_speed is None) or (shake_speed < self._SHAKE_SPEED_MIN):
                shake_speed = 0
            elif shake_speed > self._SHAKE_SPEED_MAX:
                shake_speed = self._SHAKE_SPEED_MAX
            if shake_speed != 0:
                shook = False
                shake_try = 0
                while (not shook) and (shake_try < self._config['shake_attempts']):
                    shake_try += 1
                    try:
                        self._bsc.shake_on(shake_speed)
                        shook = True
                    except BioshakeError:
                        self._debug_print('bioshake_device.get_error_list(): ' + str(self._bsc.get_error_list()))
                        self._debug_print('BioshakeError! Resetting for ' + str(self._config['setup_duration']) + 's and trying again...')
                        self._bsc.reset_device()
                        time.sleep(self._config['setup_duration'])
        return shake_speed

    def _shake_off(self,shake_speed):
        if self._using_bsc:
            if shake_speed != 0:
                shook = False
                shake_try = 0
                while (not shook) and (shake_try < self._config['shake_attempts']):
                    shake_try += 1
                    try:
                        self._bsc.shake_off()
                        shook = True
                    except BioshakeError:
                        self._debug_print('bioshake_device.get_error_list(): ' + str(self._bsc.get_error_list()))
                        self._debug_print('BioshakeError! Resetting for ' + str(self._config['setup_duration']) + 's and trying again...')
                        self._bsc.reset_device()
                        time.sleep(self._config['setup_duration'])
                time.sleep(self._config['post_shake_off_duration'])

    def _debug_print(self, *args):
        if self._debug:
            print(*args)

    def _set_valve_on(self, valve_key):
        if self._using_msc:
            try:
                valve = self._valves[valve_key]
                channels = [valve['channel']]
                self._msc.set_channels_on(channels)
            except KeyError:
                raise HybridizerError('Unknown valve: ' + str(valve_key) + '. Check yaml config file for errors.')

    def _set_valves_on(self, valve_keys):
        if self._using_msc:
            try:
                channels = [self._valves[valve_key]['channel'] for valve_key in valve_keys]
                self._msc.set_channels_on(channels)
            except KeyError:
                raise HybridizerError('Unknown valve: ' + str(valve_key) + '. Check yaml config file for errors.')

    def _set_valve_off(self, valve_key):
        if self._using_msc:
            try:
                valve = self._valves[valve_key]
                channels = [valve['channel']]
                self._msc.set_channels_off(channels)
            except KeyError:
                raise HybridizerError('Unknown valve: ' + str(valve_key) + '. Check yaml config file for errors.')

    def _set_valves_off(self, valve_keys):
        if self._using_msc:
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

    def _get_adc_values_filtered(self):
        adc_values_filtered = None
        if self._using_msc:
            adc_values = None
            for sample_n in range(self._config['adc_sample_count']):
                try:
                    sample_values = self._msc.get_analog_inputs_filtered()
                    if adc_values is None:
                        adc_values = numpy.array([sample_values],int)
                    else:
                        adc_values = numpy.append(adc_values,[sample_values],axis=0)
                    time.sleep(0.1)
                except IOError:
                    pass
            adc_values_filtered = numpy.median(adc_values,axis=0)
            adc_values_filtered = adc_values_filtered.astype(int)
        return adc_values_filtered

    def _dispense_volume(self,valve_keys,volume):
    #     if i > 0:
    #         dispense_shake_duration = self._config['inter_dispense_shake_duration']
    #         if dispense_shake_duration < self._config['shake_duration_min']:
    #             dispense_shake_duration = self._config['shake_duration_min']
    #         dispense_shake_speed = self._shake_on(self._config['inter_dispense_shake_speed'])
    #         self._debug_print('shaking at ' + str(dispense_shake_speed) + 'rpm for ' + str(dispense_shake_duration) + 's...')
    #         time.sleep(dispense_shake_duration)
    #         self._shake_off(dispense_shake_speed)
    #     self._set_valve_on('system')
    #     self._debug_print('loading ' + chemical + ' into syringes for ' + str(self._config['load_duration']) + 's ' + str(i+1) + '/' + str(dispense_volume) + '...')
    #     time.sleep(self._config['load_duration'])
    #     self._set_valve_off('system')
    #     self._debug_print('dispensing ' + chemical + ' into microplate for ' + str(self._config['dispense_duration']) + 's ' + str(i+1) + '/' + str(dispense_volume) + '...')
    #     time.sleep(self._config['dispense_duration'])
        self._set_valve_on('system')
        self._debug_print('sleeping before cylinder fill for ' + str(self._config['pre_cylinder_fill_duration']) + 's.. ')
        time.sleep(self._config['pre_cylinder_fill_duration'])
        final_adc_values = None
        jumps_list = None
        if self._using_msc and (volume <= self._config['volume_crossover']):
            channels = []
            adc_value_goals = []
            ains = []
            jumps = {}
            valve_keys_copy = copy.copy(valve_keys)
            for valve_key in valve_keys:
                valve = self._valves[valve_key]
                channels.append(valve['channel'])
                adc_value_goal,ain = self._volume_to_adc_and_ain(valve_key,volume)
                adc_value_goals.append(adc_value_goal)
                ains.append(ain)
                jumps[valve_key] = 0

            volume_goal_initial = volume - self._config['volume_threshold_initial']
            fill_duration_initial_max = 0
            fill_durations_initial = []
            if volume_goal_initial >= self._config['volume_threshold_initial']/2:
                for valve_key in valve_keys:
                    fill_duration_initial = self._volume_to_fill_duration(valve_key,volume_goal_initial)
                    fill_durations_initial.append(fill_duration_initial)
                fill_duration_initial_min = min(fill_durations_initial)
                self._msc.set_channels_on_for(channels,fill_duration_initial_min)
                while not self._msc.are_all_set_fors_complete():
                    self._debug_print('Waiting...')
                    time.sleep(0.5 + fill_duration_initial_min/1000)
                self._msc.remove_all_set_fors()

            fill_duration_base = self._config['fill_duration_one_cylinder']
            fill_duration_per_cylinder = (self._config['fill_duration_all_cylinders'] - self._config['fill_duration_one_cylinder'])//(len(channels)-1)
            while len(channels) > 0:
                fill_duration = fill_duration_base + fill_duration_per_cylinder*(len(channels)-1)
                self._debug_print("Setting {0} valves on for {1}ms".format(valve_keys_copy,fill_duration))
                self._msc.set_channels_on_for(channels,fill_duration)
                while not self._msc.are_all_set_fors_complete():
                    self._debug_print('Waiting...')
                    time.sleep(fill_duration/1000)
                self._msc.remove_all_set_fors()
                adc_values_filtered = self._get_adc_values_filtered()
                ains_copy = copy.copy(ains)
                for ain in ains_copy:
                    index = ains.index(ain)
                    valve_key_copy = valve_keys_copy[index]
                    jumps[valve_key_copy] += 1
                    if adc_values_filtered[ain] >= adc_value_goals[index]:
                        channels.pop(index)
                        adc_value_goals.pop(index)
                        ains.pop(index)
                        valve_keys_copy.pop(index)
            adc_values_filtered = self._get_adc_values_filtered()
            final_adc_values = []
            jumps_list = []
            for valve_key in valve_keys:
                adc_value_goal,ain = self._volume_to_adc_and_ain(valve_key,volume)
                adc_value = adc_values_filtered[ain]
                final_adc_values.append(adc_value)
                jumps_list.append(jumps[valve_key])
                # volume = self._adc_to_volume_low(valve_key,adc_value)
        else:
            self._set_valves_on(valve_keys)
            self._debug_print('loading chemical into syringes for ' + str(self._config['load_duration_full']) + 's...')
            time.sleep(self._config['load_duration_full'])
            self._set_valves_off(valve_keys)
        self._set_valve_off('system')
        self._debug_print('sleeping after cylinder fill for ' + str(self._config['post_cylinder_fill_duration']) + 's.. ')
        time.sleep(self._config['post_cylinder_fill_duration'])
        self._set_valves_on(valve_keys)
        self._debug_print('dispensing chemical into microplate for ' + str(self._config['dispense_duration_full']) + 's.. ')
        time.sleep(self._config['dispense_duration_full'])
        self._set_valves_off(valve_keys)
        return final_adc_values,jumps_list

    def _volume_to_adc_and_ain(self,valve_key,volume):
        valve = self._valves[valve_key]
        if volume <= self._config['volume_crossover']:
            ain = valve['analog_inputs']['low']
        else:
            ain = valve['analog_inputs']['high']
        if volume > self._config['volume_max']:
            raise HybridizerError('Asking for volume greater than the max volume of {0}!'.format(self._config['volume_max']))
        if volume <= self._config['volume_crossover']:
            poly = Polynomial(self._calibration[valve_key]['volume_to_adc_low'])
            adc_value = int(round(poly(volume)))
            self._debug_print("valve: {0}, adc_value: {1}, ain: {2}".format(valve_key,adc_value,ain))
            return adc_value,ain
        else:
            poly = Polynomial(self._calibration[valve_key]['volume_to_adc_high'])
            adc_value = int(round(poly(volume)))
            self._debug_print("valve: {0}, adc_value: {1}, ain: {2}".format(valve_key,adc_value,ain))
            return adc_value,ain

    def _volume_to_fill_duration(self,valve_key,volume):
        poly = Polynomial(self._calibration[valve_key]['volume_to_fill_duration'])
        fill_duration = int(round(poly(volume)))
        return fill_duration

    # def run_dispense_tests(self):
    #     self._debug_print('pre setup sequence...')
    #     valves = ['quad1','quad2','quad3','quad4','quad5','quad6']
    #     self._set_valve_on('aspirate')
    #     self._set_valve_on('system')
    #     self._set_valves_on(valves)
    #     time.sleep(10)
    #     self._set_valve_off('system')
    #     time.sleep(10)
    #     self._set_valve_off('aspirate')
    #     time.sleep(20)
    #     self._setup()
    #     self._set_valve_on('aspirate')
    #     time.sleep(10)
    #     self._debug_print('zeroing balance...')
    #     self._balance.zero()
    #     self._debug_print('running dispense tests...')
    #     timestr = time.strftime("%Y%m%d-%H%M%S")
    #     data_file = open(timestr+'.csv','w')
    #     data_writer = csv.writer(data_file)
    #     header = ['dispense_goal','initial_weight']
    #     valve_adc = [valve+'_adc' for valve in valves]
    #     header.extend(valve_adc)
    #     valve_jumps = [valve+'_jumps' for valve in valves]
    #     header.extend(valve_jumps)
    #     header.extend(valves)
    #     data_writer.writerow(header)
    #     # dispense_goals = [5,4,3,2,1]
    #     # dispense_goals = [1,0.75,0.5,0.25]
    #     dispense_goals = [5,1,0.5]
    #     # dispense_goals = [2,1]
    #     # run_count = 10
    #     run_count = 1
    #     # dispense_goals = [1]
    #     # run_count = 2
    #     for dispense_goal in dispense_goals:
    #         for run in range(run_count):
    #             self._set_valve_on('aspirate')
    #             time.sleep(2)
    #             self._debug_print('dispense_goal: {0}, run: {1} out of {2}'.format(dispense_goal,run+1,run_count))
    #             row_data = []
    #             row_data.append(dispense_goal)
    #             initial_weight = self._balance.get_weight()[0]
    #             self._debug_print('initial_weight: {0}'.format(initial_weight))
    #             row_data.append(initial_weight)
    #             self._set_valve_on('system')
    #             time.sleep(2)
    #             final_adc_values,jumps = self._set_valves_on_until(valves,dispense_goal)
    #             row_data.extend(final_adc_values)
    #             row_data.extend(jumps)
    #             self._set_valve_off('system')
    #             time.sleep(4)
    #             weight_prev = initial_weight
    #             for valve in valves:
    #                 self._debug_print('Dispensing {0}'.format(valve))
    #                 self._set_valve_on(valve)
    #                 time.sleep(4)
    #                 self._set_valve_off(valve)
    #                 time.sleep(2)
    #                 weight_total = self._balance.get_weight()[0]
    #                 weight = weight_total - weight_prev
    #                 self._debug_print('{0} measured {1}'.format(valve,weight))
    #                 row_data.append(weight)
    #                 weight_prev = weight_total
    #             self._set_valve_off('aspirate')
    #             self._debug_print('aspirating...')
    #             time.sleep(20)
    #             self._set_all_valves_off()
    #             data_writer.writerow(row_data)
    #     data_file.close()

    # def run_calibration(self):
    #     self._debug_print('pre setup sequence...')
    #     valves = ['quad1','quad2','quad3','quad4','quad5','quad6']
    #     self._set_valve_on('aspirate')
    #     self._set_valve_on('system')
    #     self._set_valves_on(valves)
    #     time.sleep(10)
    #     self._set_valve_off('system')
    #     time.sleep(10)
    #     self._set_valve_off('aspirate')
    #     time.sleep(20)
    #     self._setup()
    #     self._set_valve_on('aspirate')
    #     time.sleep(10)
    #     # self._debug_print('zeroing hall effect sensors...')
    #     # self._store_adc_values_min()
    #     self._debug_print('zeroing balance...')
    #     self._balance.zero()
    #     self._debug_print('running calibration...')
    #     timestr = time.strftime("%Y%m%d-%H%M%S")
    #     data_file = open(timestr+'.csv','w')
    #     data_writer = csv.writer(data_file)
    #     header = ['fill_duration','initial_weight']
    #     valve_adc_low = [valve+'_adc_low' for valve in valves]
    #     header.extend(valve_adc_low)
    #     valve_adc_high = [valve+'_adc_high' for valve in valves]
    #     header.extend(valve_adc_high)
    #     header.extend(valves)
    #     data_writer.writerow(header)
    #     duration_inc = 250
    #     duration_max = 10000
    #     fill_durations = range(duration_inc,duration_max+duration_inc,duration_inc)
    #     run_count = 3
    #     for run in range(run_count):
    #         for fill_duration in fill_durations:
    #             self._set_valve_on('aspirate')
    #             time.sleep(2)
    #             self._debug_print('fill_duration: {0}, run: {1} out of {2}'.format(fill_duration,run+1,run_count))
    #             row_data = []
    #             row_data.append(fill_duration)
    #             initial_weight = self._balance.get_weight()[0]
    #             self._debug_print('initial_weight: {0}'.format(initial_weight))
    #             row_data.append(initial_weight)
    #             self._set_valve_on('system')
    #             time.sleep(2)
    #             channels = []
    #             adc_low_ain = []
    #             adc_high_ain = []
    #             for valve_key in valves:
    #                 valve = self._valves[valve_key]
    #                 channels.append(valve['channel'])
    #                 adc_low_ain.append(valve['analog_inputs']['low'])
    #                 adc_high_ain.append(valve['analog_inputs']['high'])
    #             self._msc.set_channels_on_for(channels,fill_duration)
    #             while not self._msc.are_all_set_fors_complete():
    #                 self._debug_print('Waiting...')
    #                 time.sleep(fill_duration/1000)
    #             self._msc.remove_all_set_fors()
    #             adc_values_filtered = self._get_adc_values_filtered()
    #             adc_low_values = [adc_values_filtered[ain] for ain in adc_low_ain]
    #             adc_high_values = [adc_values_filtered[ain] for ain in adc_high_ain]
    #             row_data.extend(adc_low_values)
    #             row_data.extend(adc_high_values)
    #             self._set_valve_off('system')
    #             time.sleep(4)
    #             weight_prev = initial_weight
    #             for valve in valves:
    #                 self._debug_print('Dispensing {0}'.format(valve))
    #                 self._set_valve_on(valve)
    #                 time.sleep(4)
    #                 self._set_valve_off(valve)
    #                 time.sleep(2)
    #                 weight_total = self._balance.get_weight()[0]
    #                 weight = weight_total - weight_prev
    #                 self._debug_print('{0} measured {1}'.format(valve,weight))
    #                 row_data.append(weight)
    #                 weight_prev = weight_total
    #             self._set_valve_off('aspirate')
    #             self._debug_print('aspirating...')
    #             time.sleep(20)
    #             self._set_all_valves_off()
    #             data_writer.writerow(row_data)
    #     data_file.close()

def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("calibration_file_path", help="Path to yaml calibration file.")
    parser.add_argument("config_file_path", help="Path to yaml config file.")

    args = parser.parse_args()
    calibration_file_path = args.calibration_file_path
    print("Calibration File Path: {0}".format(calibration_file_path))
    config_file_path = args.config_file_path
    print("Config File Path: {0}".format(config_file_path))

    debug = True
    hyb = Hybridizer(debug=debug,calibration_file_path=calibration_file_path,config_file_path=config_file_path)
    hyb.run_protocol()


# -----------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
