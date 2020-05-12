import pytest
import numpy as np
import lif_meanfield_tools as lmt

ureg = lmt.ureg


class Test_initialization:
    
    def test_network_params_updated_on_initialization(self,
                                                      network_params_yaml,
                                                      analysis_params_yaml):
        tau_m = 1000 * ureg.ms
        network = lmt.Network(network_params_yaml,
                              analysis_params_yaml,
                              new_network_params=dict(tau_m=tau_m))
        assert network.network_params['tau_m'] == tau_m
    
    def test_analysis_params_updated_on_initialization(self,
                                                       network_params_yaml,
                                                       analysis_params_yaml):
        df = 1000 * ureg.Hz
        network = lmt.Network(network_params_yaml,
                              analysis_params_yaml,
                              new_analysis_params=dict(df=df))
        assert network.analysis_params['df'] == df
    
    def test_warning_is_given_if_necessary_parameters_are_missing(self):
        """What are necessary parameters? For what?"""
        raise NotImplementedError
    
    def test_if_derive_params_false_no_calculation_of_derived_params(
            self, mocker, network_params_yaml, analysis_params_yaml):
        mocker.patch.object(lmt.Network,
                            '_calculate_dependent_network_parameters',
                            autospec=True)
        mocker.patch.object(lmt.Network,
                            '_calculate_dependent_analysis_parameters',
                            autospec=True)
        network = lmt.Network(network_params_yaml,
                              analysis_params_yaml,
                              derive_params=False)
        network._calculate_dependent_network_parameters.assert_not_called()
        network._calculate_dependent_analysis_parameters.assert_not_called()

    def test_hash_is_crated(self, network):
        assert network.hash
    
    def test_loading_of_existing_results(self):
        """How do we want them to be loaded?"""
        raise NotImplementedError
    

class Test_calculation_of_dependent_network_params:
    
    def test_dimension(self, network):
        assert network.network_params['dimension'] == 8
    
    def test_V0_rel(self, network):
        assert network.network_params['V_0_rel'] == 0 * ureg.mV
    
    def test_V_th_rel(self, network):
        assert network.network_params['V_th_rel'] == 15 * ureg.mV
    
    def test_j(self, network):
        assert network.network_params['j'] == 0.1756 * ureg.mV
    
    def test_W(self, network):
        W = [[87.8, -351.2, 87.8, -351.2, 87.8, -351.2, 87.8, -351.2]
             for i in range(network.network_params['dimension'])] * ureg.pA
        W[0][2] *= 2
        np.testing.assert_array_equal(network.network_params['W'], W)
    
    def test_J(self, network):
        J = [[0.1756, -0.7024, 0.1756, -0.7024, 0.1756, -0.7024, 0.1756,
              -0.7024] for i in range(network.network_params['dimension'])
             ] * ureg.mV
        J[0][2] *= 2
        np.testing.assert_array_equal(network.network_params['J'], J)

    def test_Delay(self, network):
        Delay = [[1.5, 0.75, 1.5, 0.75, 1.5, 0.75, 1.5, 0.75]
                 for i in range(network.network_params['dimension'])
                 ] * ureg.ms
        np.testing.assert_array_equal(network.network_params['Delay'], Delay)

    def test_Delay_sd(self, network):
        Delay_sd = [[0.75, 0.375, 0.75, 0.375, 0.75, 0.375, 0.75, 0.375]
                    for i in range(network.network_params['dimension'])
                    ] * ureg.ms
        np.testing.assert_array_equal(network.network_params['Delay_sd'],
                                      Delay_sd)
    

class Test_calculation_of_dependent_analysis_params:
    
    def test_omegas(self, network):
        omegas = [6.28318531e-01,
                  1.89123878e+02,
                  3.77619437e+02,
                  5.66114996e+02,
                  7.54610555e+02,
                  9.43106115e+02,
                  1.13160167e+03,
                  1.32009723e+03,
                  1.50859279e+03,
                  1.69708835e+03] * ureg.Hz
        np.testing.assert_allclose(network.analysis_params['omegas'].magnitude,
                                   omegas.magnitude, 1e-5)
        assert network.analysis_params['omegas'].units == omegas.units
    
    def test_k_wavenumbers(self, network):
        k_wavenumbers = [1, 11, 21, 31, 41, 51, 61, 71, 81, 91] * (1 / ureg.mm)
        np.testing.assert_array_equal(network.analysis_params['k_wavenumbers'],
                                      k_wavenumbers)
    
    
class Test_meta_functions:
    
    def test_change_of_parameters(self):
        pass
    
    
class Test_check_and_store_decorator:
    
    def test_check_and_store(self):
        """Very complicated!"""
        pass
    
    
class Test_saving_and_loading_routines:
    
    def test_saving(self):
        pass
    
    def test_loading(self):
        pass
    
    
meanfield_calls = dict(
    firing_rates=['firing_rates'],
    mean_input=['mean'],
    std_input=['standard_deviation'],
    delay_dist_matrix_multi=['delay_dist_matrix'],
    delay_dist_matrix_single=['delay_dist_matrix'],
    transfer_function_multi=['transfer_function'],
    transfer_function_single=['transfer_function'],
    sensitivity_measure=['transfer_function',
                         'delay_dist_matrix',
                         'sensitivity_measure'],
    power_spectra=['power_spectra'],
    eigenvalue_spectra=['eigen_spectra'],
    r_eigenvec_spectra=['eigen_spectra'],
    l_eigenvec_spectra=['eigen_spectra'],
    additional_rates_for_fixed_input=['additional_rates_for_fixed_input'],
    fit_transfer_function=['fit_transfer_function',
                           'effective_coupling_strength'],
    scan_fit_transfer_function_mean_std_input=[
        'scan_fit_transfer_function_mean_std_input'],
    linear_interpolation_alpha=['linear_interpolation_alpha'],
    compute_profile_characteristics=['solve_chareq_rate_boxcar'],
    )

network_calls = dict(
    working_point=['firing_rates', 'mean_input', 'std_input'],
    transfer_function_multi=['mean_input', 'std_input'],
    transfer_function_single=['mean_input', 'std_input'],
    sensitivity_measure=['mean_input', 'std_input'],
    power_spectra=['delay_dist_matrix', 'firing_rates', 'tranfser_function'],
    eigenvalue_spectra=['transfer_function', 'delay_dist_matrix'],
    r_eigenvec_spectra=['transfer_function', 'delay_dist_matrix'],
    l_eigenvec_spectra=['transfer_function', 'delay_dist_matrix'],
    fit_transfer_function=['transfer_function', 'mean_input', 'std_input'],
    linear_interpolation_alpha=['mean_input', 'std_input'],
    compute_profile_characteristics=['xi_of_k', 'solve_chareq_rate_boxcar'],
    )
    
    
class Test_functionality:
    pass
    # @pytest.mark.parametrize(
    #     'method, called_funcs', zip(meanfield_calls.keys(),
    #                                 meanfield_calls.values()),
    #     ids=meanfield_calls.keys())
    # def test_correct_meanfield_functions_are_called(self, mocker, network,
    #                                                 method, called_funcs):
    #     mocked_funcs = []
    #     for func in called_funcs:
    #         mocked_funcs.append(mocker.patch(
    #             'lif_meanfield_tools.meanfield_calcs.{}'.format(func)))
    #     getattr(network, method)()
    #     for mocked_func in mocked_funcs:
    #         mocked_func.assert_called_once()
