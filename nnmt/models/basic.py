"""
Defines Basic network model. A plain network without any assumed structure.
"""

import numpy as np

from .network import Network
from .. import ureg


class Basic(Network):
    """
    Simple basic model that does not assume any network structure.

    This model only reads in the parameter yaml files and calculates the most
    basic dependend parameters. It converts the weights from pA to mV,
    calculates relative thresholds and converts the analysis frequencies to
    angular frequencies.

    Parameters
    ----------
    network_params : [str | dict]
        Network parameters dictionary or yaml file name including:

        - `C` : float
            Membrane capacitance in pF.
        - `V_th_abs` : [float | np.array]
            Absolute threshold potential in mV.
        - `V_0_abs` : [float | np.array]
            Absolute reset potential in mV.
        - `populations` : list of strings
            Names of different populations.
        - `tau_s` : float
            Synaptic time constant in ms.
        - `W` : np.array
            Matrix of amplitudes of post synaptic current in pA. It needs to
            be a `len(populations) x len(populations)` matrix.
        - `W_ext`: np.array
            Matrix of amplitudes of external post synaptic current in pA. It
            needs to be a `len(populations) x len(external_populations)`
            matrix.

    analysis_params : [str | dict]
        Analysis parameters dictionary or yaml file name including:

        - `df` : float
            Step size between two analysis frequencies.
        - `f_min` : float
            Minimal analysis frequency.
        - `f_max` : float
            Maximal analysis frequency.

    See Also
    --------
    nnmt.models.Network : Parent class definings all arguments, attributes, and
                          methods.
    """

    def __init__(self, network_params=None, analysis_params=None, file=None):

        super().__init__(network_params, analysis_params, file)

        derived_network_params = (
            self._calculate_dependent_network_parameters())
        self.network_params.update(derived_network_params)

        # calculate dependend analysis parameters
        derived_analysis_params = (
            self._calculate_dependent_analysis_parameters())
        self.analysis_params.update(derived_analysis_params)

        self._convert_param_dicts_to_base_units_and_strip_units()

    def _instantiate(self, new_network_params, new_analysis_params):
        return Basic(new_network_params, new_analysis_params)

    def _calculate_dependent_network_parameters(self):
        """
        Calculate all network parameters derived from parameters in yaml file

        Returns:
        --------
        dict
            dictionary containing all derived network parameters
        """
        derived_params = {}

        # calculate dimension of system
        dim = len(self.network_params['populations'])
        derived_params['dimension'] = dim

        # reset reference potential to 0
        derived_params['V_0_rel'] = np.ones(
            self.network_params['V_0_abs'].shape) * 0 * ureg.mV
        derived_params['V_th_rel'] = (self.network_params['V_th_abs']
                                      - self.network_params['V_0_abs'])

        # convert weights in pA (current) to weights in mV (voltage)
        tau_s_div_C = self.network_params['tau_s'] / self.network_params['C']
        derived_params['J'] = (tau_s_div_C
                               * self.network_params['W']).to(ureg.mV)

        derived_params['J_ext'] = (
            tau_s_div_C * self.network_params['W_ext']).to(ureg.mV)

        return derived_params

    def _calculate_dependent_analysis_parameters(self):
        """
        Calculate all analysis parameters derived from parameters in yaml file

        Returns:
        --------
        dict
            dictionary containing derived parameters
        """
        derived_params = {}

        # convert regular to angular frequencies
        w_min = 2 * np.pi * self.analysis_params['f_min']
        w_max = 2 * np.pi * self.analysis_params['f_max']
        dw = 2 * np.pi * self.analysis_params['df']

        # enable usage of quantities
        @ureg.wraps(ureg.Hz, (ureg.Hz, ureg.Hz, ureg.Hz))
        def calc_evaluated_omegas(w_min, w_max, dw):
            """ Calculates omegas at which functions are to be evaluated """
            return np.arange(w_min, w_max, dw)

        derived_params['omegas'] = calc_evaluated_omegas(w_min, w_max, dw)

        return derived_params
