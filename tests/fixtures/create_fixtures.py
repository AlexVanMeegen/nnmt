#!/usr/bin/env python
# encoding:utf8
'''
Creates fixtures for lif_meanfield_tools tests.

WARNING: Only use this script, if your code is trustworthy! The script runs
         the code to produce the fixtures that are then stored in h5 format.
         If you run this script and your code is not working correctly, most
         tests will pass despite your code giving wrong results.

If you still want to run this script type: python create_fixtures.py -f

Usage: create_fixtures.py [options]

Options:
    -f, --force        force code to run
    -h, --help         show this information
'''

import docopt
import sys

import lif_meanfield_tools as lmt
ureg = lmt.ureg

# always show help message if not invoked with -f option
if len(sys.argv) == 1:
    sys.argv.append('-h')
    
args = docopt.docopt(__doc__)

# only run code if users are sure they want to do it
if '--force' in args.keys():

    fixture_path = ''

    cases = [0, 1]
    for case in cases:
        if case == 0:
            parameters = '{}network_params_microcircuit.yaml'.format(fixture_path)
            regime = 'noise_driven'
        elif case == 1:
            parameters = '{}minimal_negative.yaml'.format(fixture_path)
            regime = 'negative_firing_rate'
        elif case == 2:
            parameters = '{}small_network.yaml'.format(fixture_path)
            regime = 'mean_driven'
        else:
            print('Case not defined! Choose existing case, '
                  'otherwise nothing happens!')

        network = lmt.Network(parameters, ('{}analysis_params_test.yaml'
                                           ).format(fixture_path))

        network.network_params['regime'] = regime

        network.working_point()

        network.transfer_function(method='shift')
        network.results['tf_shift'] = network.results.pop('transfer_function')
        network.transfer_function(method='taylor')
        network.results['tf_taylor'] = network.results['transfer_function']

        original_delay_dist = network.network_params['delay_dist']
        network.network_params['delay_dist'] = 'none'
        network.delay_dist_matrix()
        dd_none = network.results['delay_dist']
        network.network_params['delay_dist'] = 'truncated_gaussian'
        network.delay_dist_matrix()
        dd_truncated_gaussian = network.results.pop('delay_dist')
        network.network_params['delay_dist'] = 'gaussian'
        network.delay_dist_matrix()
        dd_gaussian = network.results.pop('delay_dist')
        network.results['delay_dist_none'] = dd_none
        network.results['delay_dist_truncated_gaussian'] = dd_truncated_gaussian
        print(network.analysis_params['omegas'][0])
        network.results['delay_dist_gaussian'] = dd_gaussian
        network.network_params['delay_dist'] = original_delay_dist

        omega = network.analysis_params['omega']
        network.sensitivity_measure(omega)
        network.transfer_function(omega)
        network.delay_dist_matrix()
        network.power_spectra()

        network.eigenvalue_spectra('MH')
        network.eigenvalue_spectra('prop')
        if regime != 'negative_firing_rate':
            network.eigenvalue_spectra('prop_inv')

        network.r_eigenvec_spectra('MH')
        network.r_eigenvec_spectra('prop')
        if regime != 'negative_firing_rate':
            network.r_eigenvec_spectra('prop_inv')

        network.l_eigenvec_spectra('MH')
        network.l_eigenvec_spectra('prop')
        if regime != 'negative_firing_rate':
            network.l_eigenvec_spectra('prop_inv')

        nu_e_ext, nu_i_ext = network.additional_rates_for_fixed_input(
            network.network_params['mean_input_set'],
            network.network_params['std_input_set'])
        network.results['add_nu_e_ext'] = nu_e_ext
        network.results['add_nu_i_ext'] = nu_i_ext

        eff_coupling_strength = lmt.meanfield_calcs.effective_coupling_strength(
            network.network_params['tau_m'],
            network.network_params['tau_s'],
            network.network_params['tau_r'],
            network.network_params['V_0_rel'],
            network.network_params['V_th_rel'],
            network.network_params['J'],
            network.results['mean_input'],
            network.results['std_input'])
        network.results['effective_coupling_strength'] = eff_coupling_strength

        params = network.network_params

        network.save(file_name='{}{}_regime.h5'.format(fixture_path, regime))
