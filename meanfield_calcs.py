from __future__ import print_function

import numpy as np
import pint
from scipy.special import zetac

from input_output import ureg
import aux_calcs


@ureg.wraps(ureg.Hz, (ureg.dimensionless, ureg.s, ureg.s,
                      ureg.s, ureg.mV, ureg.mV, ureg.dimensionless, ureg.mV,
                      ureg.mV, ureg.Hz, ureg.dimensionless))
def firing_rates(dimension, tau_m, tau_s, tau_r, V_0_rel, V_th_rel, K, J, j,
                 nu_ext, K_ext):
    '''
    Returns vector of population firing rates in Hz.

    Parameters:
    -----------
    dimension: Quantity(int, 'dimensionless')
        Number of populations.
    tau_m: Quantity(float, 'second')
        Membrane time constant.
    tau_s: Quantity(float, 'second')
        Synaptic time constant.
    tau_r: Quantity(float, 'second')
        Refractory time.
    V_0_rel: Quantity(float, 'millivolt')
        Relative reset potential.
    V_th_rel: Quantity(float, 'millivolt')
        Relative threshold potential.
    K: Quantity(np.ndarray, 'dimensionless')
        Indegree matrix.
    J: Quantity(np.ndarray, 'millivolt')
        Effective connectivity matrix.
    j: Quantity(float, 'millivolt')
        Effective connectivity weight.
    nu_ext: Quantity(float, 'hertz')
        Firing rate of external input.
    K_ext: Quantity(np.ndarray, 'dimensionless')
        Numbers of external input neurons to each population.

    Returns:
    --------
    Quantity(np.ndarray, 'hertz')
        Array of firing rates of each population in hertz.
    '''

    def rate_function(mu, sigma):
        """ calculates stationary firing rate with given parameters """
        return aux_calcs.nu0_fb433(tau_m, tau_s, tau_r, V_th_rel, V_0_rel, mu,
                                   sigma)

    def get_rate_difference(nu):
        """ calculate difference between new iteration step and previous one """
        ### new mean
        # contribution from within the network
        m0 = np.dot(K * J, nu) * tau_m
        # contribution from external sources
        m_ext = j * K_ext * nu_ext * tau_m
        # add them up
        mu = m0 + m_ext

        ### new std
        # contribution from within the network to variance
        var0 = np.dot(K * J**2, nu) * tau_m
        # contribution from external sources to variance
        var_ext = j**2 * K_ext * nu_ext * tau_m
        # add them up
        var = var0 + var_ext
        # standard deviation is square root of variance
        sigma = np.sqrt(var)

        new_nu = np.array([x for x in list(map(rate_function, mu, sigma))])

        return -nu + new_nu

    # do iteration procedure, until stationary firing rates are found
    dt = 0.05
    y = np.zeros((2, int(dimension)))
    eps = 1.0
    while eps >= 1e-5:
        delta_y = get_rate_difference(y[0])
        y[1] = y[0] + delta_y*dt
        epsilon = (y[1] - y[0])
        eps = max(np.abs(epsilon))
        y[0] = y[1]

    return y[1]

@ureg.wraps(ureg.mV, (ureg.Hz, ureg.dimensionless, ureg.mV, ureg.mV, ureg.s,
                      ureg.Hz, ureg.dimensionless))
def mean(nu, K, J, j, tau_m, nu_ext, K_ext):
    '''
    Calc mean inputs to populations as function of firing rates of populations

    Following Fourcaud & Brunel (2002)

    Parameters:
    -----------
    nu: Quantity(np.ndarray, 'hertz')
        firing rates of populations
    K: Quantity(np.ndarray, 'dimensionless')
        indegree matrix
    J: Quantity(np.ndarray, 'millivolt')
        effective connectivity matrix
    j: Quantity(float, 'millivolt')
        effective connectivity weight
    tau_m: Quantity(float, 'millisecond')
        membrane time constant
    nu_ext: Quantity(float, 'hertz')
        firing rate of external input
    K_ext: Quantity(np.ndarray, 'dimensionless')
        numbers of external input neurons to each population

    Returns:
    --------
    Quantity(np.ndarray, 'millivolt')
        array of mean inputs to each population in millivolt
    '''

    # contribution from within the network
    m0 = np.dot(K * J, nu) * tau_m
    # contribution from external sources
    m_ext = j * K_ext * nu_ext * tau_m
    # add them up
    m = m0 + m_ext

    return m


@ureg.wraps(ureg.mV, (ureg.Hz, ureg.dimensionless, ureg.mV, ureg.mV, ureg.s,
                      ureg.Hz, ureg.dimensionless))
def standard_deviation(nu, K, J, j, tau_m, nu_ext, K_ext):
    '''
    Calc standard devs of inputs to populations as function of firing rates

    Following Fourcaud & Brunel (2002)

    Parameters:
    -----------
    nu: Quantity(np.ndarray, 'hertz')
        firing rates of populations
    K: Quantity(np.ndarray, 'dimensionless')
        indegree matrix
    J: Quantity(np.ndarray, 'millivolt')
        effective connectivity matrix
    j: Quantity(float, 'millivolt')
        effective connectivity weight
    tau_m: Quantity(float, 'millisecond')
        membrane time constant
    nu_ext: Quantity(float, 'hertz')
        firing rate of external input
    K_ext: Quantity(np.ndarray, 'dimensionless')
        numbers of external input neurons to each population

    Returns:
    --------
    Quantity(np.ndarray, 'millivolt')
        array of standard dev of inputs to each population in millivolt
    '''
    # contribution from within the network to variance
    var0 = np.dot(K * J**2, nu) * tau_m
    # contribution from external sources to variance
    var_ext = j**2 * K_ext * nu_ext * tau_m
    # add them up
    var = var0 + var_ext
    # standard deviation is square root of variance
    std = np.sqrt(var)

    return std


@ureg.wraps(ureg.dimensionless, (ureg.dimensionless, ureg.s, ureg.s,
                                 ureg.dimensionless, ureg.Hz), strict=False)
def delay_dist_matrix(dimension, Delay, Delay_sd, delay_dist, omega):
    '''
    Calcs matrix of delay distribution specific pre-factors at frequency omega.

    ???
    Assumes lower boundary for truncated Gaussian distributed delays to be zero
    (exact would be dt, the minimal time step).

    Parameters:
    -----------
    dimension: Quantity(int, 'dimensionless')
        Dimension of the system / number of populations'
    Delay: Quantity(np.ndarray, 's')
        Delay matrix.
    Delay_sd: Quantity(np.ndarray, 's')
        Delay standard deviation matrix.
    delay_dist: str
        String specifying delay distribution.
    omega: float
        Frequency.

    Returns:
    --------
    Quantity(nd.array, 'dimensionless')
        Matrix of delay distribution specific pre-factors at frequency omega.
    '''

    mu = Delay
    sigma = Delay_sd
    D = np.ones((int(dimension),int(dimension)))

    if delay_dist == 'none':
        print(-complex(0,1)*omega*mu)
        return D*np.exp(-complex(0,omega)*mu)

    elif delay_dist == 'truncated_gaussian':
        a0 = aux_calcs.Phi(-mu/sigma+1j*omega*sigma)
        a1 = aux_calcs.Phi(-mu/sigma)
        b0 = np.exp(-0.5*np.power(sigma*omega,2))
        b1 = np.exp(-complex(0,omega)*mu)
        return (1.0-a0)/(1.0-a1)*b0*b1

    elif delay_dist == 'gaussian':
        b0 = np.exp(-0.5*np.power(sigma*omega,2))
        b1 = np.exp(-complex(0,omega)*mu)
        return b0*b1


@ureg.wraps(ureg.Hz/ureg.mV, (ureg.mV, ureg.mV, ureg.s, ureg.s, ureg.s,
                              ureg.mV, ureg.mV, ureg.Hz))
def transfer_function_1p_taylor(mu, sigma, tau_m, tau_s, tau_r, V_th_rel,
                                V_0_rel, omega):
    """
    Calcs value of transfer func for one population at given frequency omega.

    The calculation is done according to Eq. 93 in Schuecker et al (2014).

    Parameters:
    -----------
    mu: Quantity(float, 'millivolt')
        Mean neuron activity of one population in mV.
    sigma: Quantity(float, 'millivolt')
        Standard deviation of neuron activity of one population in mV.
    tau_m: Quantity(float, 'millisecond')
        Membrane time constant.
    tau_s: Quantity(float, 'millisecond')
        Synaptic time constant.
    tau_r: Quantity(float, 'millisecond')
        Refractory time.
    V_th_rel: Quantity(float, 'millivolt')
        Relative threshold potential.
    V_0_rel: Quantity(float, 'millivolt')
        Relative reset potential.
    omega: Quantity(flaot, 'hertz')
        Input frequency to population.

    Returns:
    --------
    Quantity(float, 'hertz/millivolt')
    """

    # for frequency zero the exact expression is given by the derivative of
    # f-I-curve
    if np.abs(omega- 0.) < 1e-15:
        return aux_calcs.d_nu_d_mu_fb433(tau_m, tau_s, tau_r, V_th_rel, V_0_rel,
                                         mu, sigma)
    else:
        nu0 = aux_calcs.nu_0(tau_m, tau_r, V_th_rel, V_0_rel, mu, sigma)
        nu0_fb = aux_calcs.nu0_fb433(tau_m, tau_s, tau_r, V_th_rel, V_0_rel, mu,
                                     sigma)
        x_t = np.sqrt(2.) * (V_th_rel - mu) / sigma
        x_r = np.sqrt(2.) * (V_0_rel - mu) / sigma
        z = complex(-0.5, complex(omega * tau_m))
        alpha = np.sqrt(2) * abs(zetac(0.5) + 1)
        k = np.sqrt(tau_s / tau_m)
        A = alpha * tau_m * nu0 * k / np.sqrt(2)
        a0 = aux_calcs.Psi_x_r(z, x_t, x_r)
        a1 = aux_calcs.dPsi_x_r(z, x_t, x_r) / a0
        a3 = A / tau_m / nu0_fb * (-a1**2 + aux_calcs.d2Psi_x_r(z, x_t, x_r)/a0)
        result = (np.sqrt(2.) / sigma * nu0_fb / complex(1., omega * tau_m)* (a1 + a3))
        return result


@ureg.wraps(ureg.Hz/ureg.mV, (ureg.mV, ureg.mV, ureg.s, ureg.s, ureg.s,
                              ureg.mV, ureg.mV, ureg.Hz))
def transfer_function_1p_shift(mu, sigma, tau_m, tau_s, tau_r, V_th_rel,
                               V_0_rel, omega):
    """
    Calcs value of transfer func for one population at given frequency omega.

    Calculates transfer function according to $\tilde{n}$ in Schuecker et al.
    (2015). The expression is to first order equivalent to
    `transfer_function_1p_taylor`. Since the underlying theory is correct to
    first order, the two expressions are exchangeable.

    Parameters:
    -----------
    mu: Quantity(float, 'millivolt')
        Mean neuron activity of one population in mV.
    sigma: Quantity(float, 'millivolt')
        Standard deviation of neuron activity of one population in mV.
    tau_m: Quantity(float, 'millisecond')
        Membrane time constant.
    tau_s: Quantity(float, 'millisecond')
        Synaptic time constant.
    tau_r: Quantity(float, 'millisecond')
        Refractory time.
    V_th_rel: Quantity(float, 'millivolt')
        Relative threshold potential.
    V_0_rel: Quantity(float, 'millivolt')
        Relative reset potential.
    omega: Quantity(flaot, 'hertz')
        Input frequency to population.

    Returns:
    --------
    Quantity(float, 'hertz/millivolt')
    """

    # effective threshold and reset
    alpha = np.sqrt(2) * abs(zetac(0.5) + 1)
    V_th_rel += sigma * alpha / 2. * np.sqrt(tau_s / tau_m)
    V_0_rel += sigma * alpha / 2. * np.sqrt(tau_s / tau_m)

    # for frequency zero the exact expression is given by the derivative of
    # f-I-curve
    if np.abs(omega - 0.) < 1e-15:
        return aux_calcs.d_nu_d_mu(tau_m, tau_s, tau_r, V_th_rel, V_0_rel, mu,
                                   sigma)
    else:
        nu = aux_calcs.nu_0(tau_m, tau_r, V_th_rel, V_0_rel, mu, sigma)

        x_t = np.sqrt(2.) * (V_th_rel - mu) / sigma
        x_r = np.sqrt(2.) * (V_0_rel - mu) / sigma
        z = complex(-0.5, complex(omega * tau_m))

        frac = aux_calcs.dPsi_x_r(z, x_t, x_r) / aux_calcs.Psi_x_r(z, x_t, x_r)

        return (np.sqrt(2.) / sigma * nu
                / (1. + complex(0., complex(omega*tau_m))) * frac)


def transfer_function(mu, sigma, tau_m, tau_s, tau_r, V_th_rel, V_0_rel,
                      dimension, omegas):
    """
    Returns transfer functions for all populations.

    Parameters:
    -----------
    mu: Quantity(float, 'millivolt')
        Mean neuron activity of one population in mV.
    sigma: Quantity(float, 'millivolt')
        Standard deviation of neuron activity of one population in mV.
    tau_m: Quantity(float, 'millisecond')
        Membrane time constant.
    tau_s: Quantity(float, 'millisecond')
        Synaptic time constant.
    tau_r: Quantity(float, 'millisecond')
        Refractory time.
    V_th_rel: Quantity(float, 'millivolt')
        Relative threshold potential.
    V_0_rel: Quantity(float, 'millivolt')
        Relative reset potential.
    omegas: Quantity(np.ndarray, 'hertz')
        Input frequencies to population.

    Returns:
    --------
    list of Quantities(np.nd.array, 'hertz/millivolt'):
        Returns one array for each population collected in a list. The arrays
        contain the values of the transfer function corresponding to the
        given omegas.
    """

    transfer_functions = [[transfer_function_1p_shift(mu[i], sigma[i], tau_m,
                                                      tau_s, tau_r, V_th_rel,
                                                      V_0_rel, omega)
                           for omega in omegas]
                          for i in range(dimension.magnitude)]

    # convert list of list of quantities to list of quantities containing np.ndarray
    tf_magnitudes = [np.array([tf.magnitude for tf in tf_population])
                     for tf_population in transfer_functions]
    tf_unit = transfer_functions[0][0].units

    return tf_magnitudes * tf_unit

# def create_H(self, omega):
#     ''' Returns vector of the transfer function and
#     the instantaneous rate jumps at frequency omega.
#     '''
#     # factor due to weight scaling of NEST in current equation
#     # of 'iaf_psc_exp'-model
#     fac = 2*self.tau_s/self.C
#     if self.tf_mode == 'analytical':
#         # find nearest omega, important when the transfer function is
#         # read from file
#         k = np.argmin(abs(self.omegas-np.abs(omega.real)))
#         trans_func = np.transpose(self.trans_func)
#         if omega < 0:
#             trans_func = np.conjugate(trans_func)
#         H = taum*fac*trans_func[k]/complex(1,omega*tauf)
#     else:
#         tau = self.tau_impulse*0.001
#         H = self.H_df/(1.0+complex(0,omega)*tau)
#     return H
#
# def power_spectra(tf_mode, omegas, firing_rates, dimension, N, omega):
#     """
#     """
#     Delay_dist = delay_dist_matrix(dimension, Delay, Delay_sd, delay_dist, omega)
#
#     if tf_mode == 'analytical':
#         # find nearest omega, important when the transfer function is
#         # read from file
#         k = np.argmin(abs(omegas-np.abs(omega.real)))
#         trans_func = np.transpose(trans_func)
#         if omega < 0:
#             trans_func = np.conjugate(trans_func)
#         H = taum*fac*trans_func[k]/complex(1,omega*tauf)
#     else:
#         tau = self.tau_impulse*0.001
#         H = self.H_df/(1.0+complex(0,omega)*tau)
#     MH_plus = self.create_MH(omega)
#     Q_plus = np.linalg.inv(np.identity(self.dimension)-MH_plus)
#     C = np.dot(Q_plus,np.dot(self.D,np.transpose(np.conjugate(Q_plus))))
#     D = np.diag(np.ones(dimension)) * firing_rates / N
#
#     # MH_plus = self.create_MH(omega)
#     # Q_plus = np.linalg.inv(np.identity(self.dimension)-MH_plus)
#     # C = np.dot(Q_plus,np.dot(self.D,np.transpose(np.conjugate(Q_plus))))
#     # return np.power(abs(np.diag(C)),2)