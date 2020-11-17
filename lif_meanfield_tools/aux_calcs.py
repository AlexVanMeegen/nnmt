"""
This module contains lots of auxiliary calculations. It is sometimes called by meanfield_calcs.

Functions:
nu0_fb433
nu_0
siegert1
siegert2
Phi
Phi_prime_mu
d_nu_d_mu_fb433
d_nu_d_mu
Psi
d_Psi
d_2_Psi
Psi_x_r
dPsi_x_r
d2Psi_x_r
d_nu_d_nu_fb
determinant
determinant_same_rows
p_hat_boxcar
solve_chareq_rate_boxcar
"""

from __future__ import print_function
from scipy.special import erf, zetac, lambertw, erfcx, dawsn, roots_legendre
from scipy.integrate import quad

import numpy as np
import math
import mpmath

from . import ureg


def nu0_fb433(tau_m, tau_s, tau_r, V_th_rel, V_0_rel, mu, sigma):
    """
    Calcs stationary firing rates for exp PSCs

    Calculates the stationary firing rate of a neuron with synaptic filter of
    time constant tau_s driven by Gaussian noise with mean mu and standard
    deviation sigma, using Eq. 433 in Fourcaud & Brunel (2002) with Taylor
    expansion k = sqrt(tau_s/tau_m).

    Parameters:
    -----------
    tau_m: float
        Membrane time constant in seconds.
    tau_s: float
        Synaptic time constant in seconds.
    tau_r: float
        Refractory time in seconds.
    V_th_rel: float
        Relative threshold potential in mV.
    V_0_rel: float
        Relative reset potential in mV.
    mu: float
        Mean neuron activity in mV.
    sigma: float
        Standard deviation of neuron activity in mV.

    Returns:
    --------
    float:
        Stationary firing rate in Hz.
    """
    alpha = np.sqrt(2.) * abs(zetac(0.5) + 1)
    x_th = np.sqrt(2.) * (V_th_rel - mu) / sigma
    x_r = np.sqrt(2.) * (V_0_rel - mu) / sigma

    # preventing overflow in np.exponent in Phi(s)
    if x_th > 20.0 / np.sqrt(2.):
        result = nu_0(tau_m, tau_r, V_th_rel, V_0_rel, mu, sigma)
    else:
        r = nu_0(tau_m, tau_r, V_th_rel, V_0_rel, mu, sigma)
        dPhi = Phi(x_th) - Phi(x_r)
        result = (r - np.sqrt(tau_s / tau_m) * alpha / (tau_m * np.sqrt(2))
                  * dPhi * (r * tau_m)**2)
    if math.isnan(result):
        print(mu, sigma, x_th, x_r)
    return result


def nu_0(tau_m, tau_r, V_th_rel, V_0_rel, mu, sigma):
    """
    Calculates stationary firing rates for delta shaped PSCs.

    Parameters:
    -----------
    tau_m: float
        Membrane time constant in seconds.
    tau_r: float
        Refractory time in seconds.
    V_th_rel: float
        Relative threshold potential in mV.
    V_0_rel: float
        Relative reset potential in mV.
    mu: float
        Mean neuron activity in mV.
    sigma:
        Standard deviation of neuron activity in mV.

    Returns:
    --------
    float:
        Stationary firing rate in Hz.
    """
    y_th = (V_th_rel - mu) / sigma
    y_r = (V_0_rel - mu) / sigma
    y_th = np.atleast_1d(y_th)
    y_r = np.atleast_1d(y_r)
    assert y_th.shape == y_r.shape
    assert y_th.ndim == y_r.ndim == 1

    # determine order of quadrature
    params = {'start_order': 10, 'epsrel': 1e-12, 'maxiter': 10}
    gl_order = _get_erfcx_integral_gl_order(y_th=y_th, y_r=y_r, **params)

    # separate domains
    mask_exc = y_th < 0
    mask_inh = 0 < y_r
    mask_interm = (y_r <= 0) & (0 <= y_th)

    # calculate siegert
    nu = np.zeros(shape=y_th.shape)
    params = {'tau_m': tau_m, 't_ref': tau_r, 'gl_order': gl_order}
    nu[mask_exc] = _siegert_exc(y_th=y_th[mask_exc],
                                y_r=y_r[mask_exc], **params)
    nu[mask_inh] = _siegert_inh(y_th=y_th[mask_inh],
                                y_r=y_r[mask_inh], **params)
    nu[mask_interm] = _siegert_interm(y_th=y_th[mask_interm],
                                      y_r=y_r[mask_interm], **params)

    # convert back to scalar if only one value calculated
    if nu.shape == (1,):
        return nu.item(0)
    else:
        return nu


def nu0_fb(tau_m, tau_s, tau_r, V_th, V_r, mu, sigma):
    """
    Calculates stationary firing rates for filtered synapses based on
    Fourcaud & Brunel 2002 (using the shift of the integration boundaries)

    Parameters:
    -----------
    tau_m: float
        Membrane time constant in seconds.
    tau_s: float
        Synaptic time constant in seconds.
    tau_r: float
        Refractory time in seconds.
    V_th_rel: float
        Relative threshold potential in mV.
    V_0_rel: float
        Relative reset potential in mV.
    mu: float
        Mean neuron activity in mV.
    sigma:
        Standard deviation of neuron activity in mV.

    Returns:
    --------
    float:
        Stationary firing rate in Hz.
    """

    alpha = np.sqrt(2)*abs(zetac(0.5)+1)
    # effective threshold
    V_th1 = V_th + sigma*alpha/2.*np.sqrt(tau_s/tau_m)
    # effective reset
    V_r1 = V_r + sigma*alpha/2.*np.sqrt(tau_s/tau_m)
    # use standard Siegert with modified threshold and reset
    return nu_0(tau_m, tau_r, V_th1, V_r1, mu, sigma)


def _get_erfcx_integral_gl_order(y_th, y_r, start_order, epsrel, maxiter):
    """Determine order of Gauss-Legendre quadrature for erfcx integral."""
    # determine maximal integration range
    a = min(np.abs(y_th).min(), np.abs(y_r).min())
    b = max(np.abs(y_th).max(), np.abs(y_r).max())

    # adaptive quadrature from scipy.integrate for comparison
    I_quad = quad(erfcx, a, b, epsabs=0, epsrel=epsrel)[0]

    # increase order to reach desired accuracy
    order = start_order
    for _ in range(maxiter):
        I_gl = _erfcx_integral(a, b, order=order)[0]
        rel_error = np.abs(I_gl/I_quad - 1)
        if rel_error < epsrel:
            return order
        else:
            order *= 2
    msg = f'Failed to converge after {maxiter} iterations. '
    msg += f'Last relative error {rel_error}.'
    raise RuntimeError(msg)


def _erfcx_integral(a, b, order):
    """Fixed order Gauss-Legendre quadrature of erfcx from a to b."""
    assert np.all(a >= 0) and np.all(b >= 0)
    x, w = roots_legendre(order)
    x = x[:, np.newaxis]
    w = w[:, np.newaxis]
    return (b-a) * np.sum(w * erfcx((b-a)*x/2 + (b+a)/2), axis=0) / 2


def _siegert_exc(y_th, y_r, tau_m, t_ref, gl_order):
    """Calculate Siegert for y_th < 0."""
    assert np.all(y_th < 0)
    Int = _erfcx_integral(np.abs(y_th), np.abs(y_r), gl_order)
    return 1 / (t_ref + tau_m * np.sqrt(np.pi) * Int)


def _siegert_inh(y_th, y_r, tau_m, t_ref, gl_order):
    """Calculate Siegert for 0 < y_th."""
    assert np.all(0 < y_r)
    e_V_th_2 = np.exp(-y_th**2)
    Int = 2 * dawsn(y_th) - 2 * np.exp(y_r**2 - y_th**2) * dawsn(y_r)
    Int -= e_V_th_2 * _erfcx_integral(y_r, y_th, gl_order)
    return e_V_th_2 / (e_V_th_2 * t_ref + tau_m * np.sqrt(np.pi) * Int)


def _siegert_interm(y_th, y_r, tau_m, t_ref, gl_order):
    """Calculate Siegert for y_r <= 0 <= y_th."""
    assert np.all((y_r <= 0) & (0 <= y_th))
    e_V_th_2 = np.exp(-y_th**2)
    Int = 2 * dawsn(y_th)
    Int += e_V_th_2 * _erfcx_integral(y_th, np.abs(y_r), gl_order)
    return e_V_th_2 / (e_V_th_2 * t_ref + tau_m * np.sqrt(np.pi) * Int)


def Phi(s):
    """
    helper function to calculate stationary firing rates with synaptic
    filtering

    corresponds to u^-2 F in Eq. 53 of the following publication


    Schuecker, J., Diesmann, M. & Helias, M.
    Reduction of colored noise in excitable systems to white
    noise and dynamic boundary conditions. 1–23 (2014).
    """
    return np.sqrt(np.pi / 2.) * (np.exp(s**2 / 2.) * (1 + erf(s / np.sqrt(2))))


def Phi_prime_mu(s, sigma):
    """
    Derivative of the helper function Phi(s) with respect to the mean input
    """
    return -np.sqrt(np.pi) / sigma * (s * np.exp(s**2 / 2.)
    * (1 + erf(s / np.sqrt(2)))
    + np.sqrt(2) / np.sqrt(np.pi))


def d_nu_d_mu_fb433(tau_m, tau_s, tau_r, V_th_rel, V_0_rel, mu, sigma):
    """
    Derivative of the stationary firing rates with synaptic filtering
    with respect to the mean input

    See Appendix B in
    Schuecker, J., Diesmann, M. & Helias, M.
    Reduction of colored noise in excitable systems to white
    noise and dynamic boundary conditions. 1–23 (2014).

    Parameters:
    -----------
    tau_m: float
        Membrane time constant in seconds.
    tau_s: float
        Synaptic time constant in seconds.
    tau_r: float
        Refractory time in seconds.
    V_th_rel: float
        Relative threshold potential in mV.
    V_0_rel: float
        Relative reset potential in mV.
    mu: float
        Mean neuron activity in mV.
    sigma:
        Standard deviation of neuron activity in mV.

    Returns:
    --------
    float:
        Something in Hz/mV.
    """
    alpha = np.sqrt(2) * abs(zetac(0.5) + 1)
    x_th = np.sqrt(2) * (V_th_rel - mu) / sigma
    x_r = np.sqrt(2) * (V_0_rel - mu) / sigma
    integral = 1. / (nu_0(tau_m, tau_r, V_th_rel, V_0_rel, mu, sigma) * tau_m)
    prefactor = np.sqrt(tau_s / tau_m) * alpha / (tau_m * np.sqrt(2))
    dnudmu = d_nu_d_mu(tau_m, tau_r, V_th_rel, V_0_rel, mu, sigma)
    dPhi_prime = Phi_prime_mu(x_th, sigma) - Phi_prime_mu(x_r, sigma)
    dPhi = Phi(x_th) - Phi(x_r)
    phi = dPhi_prime * integral + (2 * np.sqrt(2) / sigma) * dPhi**2
    return dnudmu - prefactor * phi / integral**3


def d_nu_d_mu(tau_m, tau_r, V_th_rel, V_0_rel, mu, sigma):
    """
    Derivative of the stationary firing rate without synaptic filtering
    with respect to the mean input

    Parameters:
    -----------
    tau_m: float
        Membrane time constant in seconds.
    tau_s: float
        Synaptic time constant in seconds.
    tau_r: float
        Refractory time in seconds.
    V_th_rel: float
        Relative threshold potential in mV.
    V_0_rel: float
        Relative reset potential in mV.
    mu: float
        Mean neuron activity in mV.
    sigma:
        Standard deviation of neuron activity in mV.

    Returns:
    --------
    float:
        Something in Hz/mV.
    """
    y_th = (V_th_rel - mu)/sigma
    y_r = (V_0_rel - mu)/sigma
    nu0 = nu_0(tau_m, tau_r, V_th_rel, V_0_rel, mu, sigma)
    return (np.sqrt(np.pi) * tau_m * nu0**2 / sigma
            * (np.exp(y_th**2) * (1 + erf(y_th)) - np.exp(y_r**2)
               * (1 + erf(y_r))))

def Psi(z, x):
    """
    Calcs Psi(z,x)=exp(x**2/4)*U(z,x), with U(z,x) the parabolic cylinder func.
    """
    return np.exp(0.25*x**2) * complex(mpmath.pcfu(z, -x))


def d_Psi(z, x):
    """
    First derivative of Psi using recurrence relations.

    (Eq.: 12.8.9 in http://dlmf.nist.gov/12.8)
    """
    return (1. / 2. + z) * Psi(z + 1, x)


def d_2_Psi(z, x):
    """
    Second derivative of Psi using recurrence relations.

    (Eq.: 12.8.9 in http://dlmf.nist.gov/12.8)
    """
    return (1. / 2. + z) * (3. / 2. + z) * Psi(z + 2, x)


def Psi_x_r(z, x, y):
    """Difference of Psi for same first argument z."""
    return Psi(z, x) - Psi(z, y)


def dPsi_x_r(z, x, y):
    """Difference of derivatives of Psi for same first argument z."""
    return d_Psi(z, x) - d_Psi(z, y)


def d2Psi_x_r(z, x, y):
    """Difference of second derivatives of Psi for same first argument z."""
    return d_2_Psi(z, x) - d_2_Psi(z, y)


def d_nu_d_nu_in_fb(tau_m, tau_s, tau_r, V_th, V_r, j, mu, sigma):
    """
    Derivative of nu_0 by input rate for low-pass-filtered synapses with tau_s.
    Effective threshold and reset from Fourcaud & Brunel 2002.

    Parameters:
    -----------
    tau_m: float
        Membrane time constant in seconds.
    tau_s: float
        Synaptic time constant in seconds.
    tau_r: float
        Refractory time in seconds.
    V_th_rel: float
        Relative threshold potential in mV.
    V_0_rel: float
        Relative reset potential in mV.
    j: float
        Effective connectivity weight in mV.
    mu: float
        Mean neuron activity in mV.
    sigma:
        Standard deviation of neuron activity in mV.

    Returns:
    --------
    float:
        Derivative in Hz/mV (sum of linear (mu) and squared (sigma^2) contribution).
    float:
        Derivative in Hz/mV (linear (mu) contribution).
    float:
        Derivative in Hz/mV (squared (sigma^2) contribution).
    """
    alpha = np.sqrt(2) * abs(zetac(0.5) + 1)

    y_th = (V_th - mu) / sigma
    y_r = (V_r - mu) / sigma

    y_th_fb = y_th + alpha / 2. * np.sqrt(tau_s / tau_m)
    y_r_fb = y_r + alpha / 2. * np.sqrt(tau_s / tau_m)

    nu0 = nu0_fb(tau_m, tau_s, tau_r, V_th, V_r, mu, sigma)

    # linear contribution
    lin = np.sqrt(np.pi) * (tau_m * nu0)**2 * j / sigma * (np.exp(y_th_fb**2) * (1 +
             erf(y_th_fb)) - np.exp(y_r_fb**2) * (1 + erf(y_r_fb)))

    # quadratic contribution
    sqr = np.sqrt(np.pi) * (tau_m * nu0)**2 * j / sigma * (np.exp(y_th_fb**2) * (1 + erf(y_th_fb)) *\
             0.5 * y_th * j / sigma - np.exp(y_r_fb**2) * (1 + erf(y_r_fb)) * 0.5 * y_r * j / sigma)

    return lin + sqr, lin, sqr

def determinant(matrix):
    """
    Solve
        det(matrix - x*identity) = 0
    for the integer x and a square matrix
    using sympy.

    Return only non-trivial (!=0) solutions.

    Parameters:
    -----------
    matrix: np.ndarray
        A matrix.

    Returns:
    --------
    res: float or complex
    """
    all_res = np.linalg.eigvals(matrix)

    idx = np.where(np.abs(all_res) > 1.E-10)[0]
    if len(idx) !=1 : raise Exception
    #assert len(idx) == 1, 'Multiple non-trivial solutions exist.'
    res = all_res[idx[0]]

    return res


def determinant_same_rows(matrix):
    """
    Compute determinant of matrix with same rows.

    Parameters:
    -----------
    matrix: np.ndarray
        A matrix with same rows.

    Returns:
    --------
        res: float or complex
    """
    res = np.sum(matrix, axis=1)[0]
    return res


def p_hat_boxcar(k, width):
    """
    Fourier transform of boxcar connectivity kernel at wave number k.

    Parameters:
    -----------
    k: float
        Wavenumber.
    width: float or np.ndarray
        Width(s) of boxcar kernel(s).

    Returns:
    --------
    ft: float
    """
    if k == 0:
        ft = 1.
    else:
        ft = np.sin(k * width) / (k * width)
    return ft


def solve_chareq_rate_boxcar(branch, k, tau, W_rate, width, delay):
    """
    Solve the characteristic equation for the linearized rate model for
    one branch analytically.
    Requires a spatially organized network with boxcar connectivity profile.

    Parameters:
    -----------
    branch: float
        Branch number.
    k: float
        Wavenumber in 1/mm.
    tau: float
        Time constant from fit in s.
    W_rate: np.ndarray
        Weights from fit.
    width: np.ndarray
        Spatial widths of boxcar connectivtiy profile in mm.
    delay: float
        Delay in s.

    Returns:
    --------
    eigenval: complex

    delay, tau must be floats, W,
    width is vector
    """

    M = W_rate * p_hat_boxcar(k, width)
    xi = determinant(M)

    eigenval = -1./tau + 1./delay * \
        lambertw(xi * delay/tau * np.exp(delay/tau), branch)
    return eigenval
