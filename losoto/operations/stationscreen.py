#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This is the station-screen operation for LoSoTo


import logging
from losoto.operations_lib import *

logging.debug('Loading STATIONSCREEN module.')


def run_parser(soltab, parser, step):
    outSoltab = parser.getstr( step, "outSoltab" )
    order = parser.getint( step, "Order", 5 )
    beta = parser.getfloat( step, "Beta", 5.0/3.0 )
    niter = parser.getint( step, "niter", 2 )
    nsigma = parser.getfloat( step, "nsigma", 5.0 )
    refAnt = parser.getint( step, "RefAnt", -1 )
    scale_order = parser.getbool( step, "ScaleOrder", True )
    scale_dist = parser.getfloat( step, "nsigma", 25000.0 )
    min_order = parser.getint( step, "MinOrder", 5 )
    adjust_order = parser.getbool( step, "AdjustOrder", True )

    return run(soltab, outSoltab, order, beta, ncpu, niter, nsigma,
        refAnt, scale_order, scale_dist, min_order, adjust_order)


def calculate_piercepoints(station_positions, source_positions):
    """
    Returns array of piercepoint locations

    Parameters
    ----------
    station_positions : array
        Array of station positions
    source_positions : array
        Array of source positions

    Returns
    -------
    pp : array
        Array of pierce points
    midRA : float
        Reference RA for WCS system (deg)
    midDec : float
        Reference Dec for WCS system (deg)

    """
    import pyrap.measures
    import numpy as np
    try:
        import progressbar
    except ImportError:
        import losoto.progressbar as progressbar

    logging.info('Calculating screen pierce-point locations...')
    N_sources = source_positions.shape[0]
    N_stations = station_positions.shape[0]
    N_piercepoints = N_stations * N_sources
    pp = np.zeros((N_piercepoints, 3))

    xyz = np.zeros((N_sources, 3))
    ra_deg = source_positions.T[0] * 180.0 / np.pi
    dec_deg = source_positions.T[1] * 180.0 / np.pi
    xy, midRA, midDec = getxy(ra_deg, dec_deg)
    xyz[:, 0] = xy[0]
    xyz[:, 1] = xy[1]
    pp_idx = 0
    for i in range(N_sources):
        for station_position in station_positions:
            pp[pp_idx, :] = xyz[i]
            pp_idx += 1

    return pp, midRA, midDec


def get_ant_dist(ant_xyz, ref_xyz):
    """
    Returns distance between ant and ref in m

     Parameters
    ----------
    ant_xyz : array
        Array of station position
    ref_xyz : array
        Array of reference position

    Returns
    -------
    dist : float
        Distance between station and reference positions

    """
    import numpy as np

    return np.sqrt((ref_xyz[0] - ant_xyz[0])**2 + (ref_xyz[1] - ant_xyz[1])**2 + (ref_xyz[2] - ant_xyz[2])**2)


def getxy(RA, Dec, midRA=None, midDec=None):
    """
    Returns array of projected x and y values.

    Parameters
    ----------
    RA, Dec : list
        Lists of RA and Dec in degrees
    midRA : float
        RA for WCS reference in degrees
    midDec : float
        Dec for WCS reference in degrees

    Returns
    -------
    x, y : numpy array, numpy array, float, float
        arrays of x and y values

    """
    import numpy as np

    if midRA is None or midDec is None:
        x, y  = radec2xy(RA, Dec)

        # Refine x and y using midpoint
        if len(x) > 1:
            xmid = min(x) + (max(x) - min(x)) / 2.0
            ymid = min(y) + (max(y) - min(y)) / 2.0
            xind = np.argsort(x)
            yind = np.argsort(y)
            try:
                midxind = np.where(np.array(x)[xind] > xmid)[0][0]
                midyind = np.where(np.array(y)[yind] > ymid)[0][0]
                midRA = RA[xind[midxind]]
                midDec = Dec[yind[midyind]]
                x, y  = radec2xy(RA, Dec, midRA, midDec)
            except IndexError:
                midRA = RA[0]
                midDec = Dec[0]
        else:
            midRA = RA[0]
            midDec = Dec[0]

    x, y  = radec2xy(RA, Dec, refRA=midRA, refDec=midDec)

    return np.array([x, y]), midRA, midDec


def radec2xy(RA, Dec, refRA=None, refDec=None):
    """
    Returns x, y for input ra, dec.

    Note that the reference RA and Dec must be the same in calls to both
    radec2xy() and xy2radec() if matched pairs of (x, y) <=> (RA, Dec) are
    desired.

    Parameters
    ----------
    RA : list
        List of RA values in degrees
    Dec : list
        List of Dec values in degrees
    refRA : float, optional
        Reference RA in degrees.
    refDec : float, optional
        Reference Dec in degrees

    Returns
    -------
    x, y : list, list
        Lists of x and y pixel values corresponding to the input RA and Dec
        values

    """
    import numpy as np

    x = []
    y = []
    if refRA is None:
        refRA = RA[0]
    if refDec is None:
        refDec = Dec[0]

    # Make wcs object to handle transformation from ra and dec to pixel coords.
    w = makeWCS(refRA, refDec)

    for ra_deg, dec_deg in zip(RA, Dec):
        ra_dec = np.array([[ra_deg, dec_deg]])
        x.append(w.wcs_world2pix(ra_dec, 0)[0][0])
        y.append(w.wcs_world2pix(ra_dec, 0)[0][1])

    return x, y


def xy2radec(x, y, refRA=0.0, refDec=0.0):
    """
    Returns x, y for input ra, dec.

    Note that the reference RA and Dec must be the same in calls to both
    radec2xy() and xy2radec() if matched pairs of (x, y) <=> (RA, Dec) are
    desired.

    Parameters
    ----------
    x : list
        List of x values in pixels
    y : list
        List of y values in pixels
    refRA : float, optional
        Reference RA in degrees
    refDec : float, optional
        Reference Dec in degrees

    Returns
    -------
    RA, Dec : list, list
        Lists of RA and Dec values corresponding to the input x and y pixel
        values

    """
    import numpy as np

    RA = []
    Dec = []

    # Make wcs object to handle transformation from ra and dec to pixel coords.
    w = makeWCS(refRA, refDec)

    for xp, yp in zip(x, y):
        x_y = np.array([[xp, yp]])
        RA.append(w.wcs_pix2world(x_y, 0)[0][0])
        Dec.append(w.wcs_pix2world(x_y, 0)[0][1])

    return RA, Dec


def makeWCS(refRA, refDec):
    """
    Makes simple WCS object.

    Parameters
    ----------
    refRA : float
        Reference RA in degrees
    refDec : float
        Reference Dec in degrees

    Returns
    -------
    w : astropy.wcs.WCS object
        A simple TAN-projection WCS object for specified reference position

    """
    from astropy.wcs import WCS
    import numpy as np

    w = WCS(naxis=2)
    w.wcs.crpix = [1000, 1000]
    w.wcs.cdelt = np.array([-0.0005, 0.0005])
    w.wcs.crval = [refRA, refDec]
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.set_pv([(2, 1, 45.0)])

    return w


def flag_outliers(weights, residual, nsigma, screen_type):
    """
    Flags outliers

    Parameters
    ----------
    weights : array
        Array of weights
    phase_residual : array
        Array of residual values from phase screen fitting (rad)
    nsigma : float
        Number of sigma above with outliers are clipped (= weight set to zero)
    screen_type : str
        Type of screen: 'phase' or 'amplitude'

    Returns
    -------
    weights : array
        array of weights, with flagged times set to 0


    """
    import numpy as np
    from losoto.operations.reweight import nancircstd

    # Find stddev of the screen
    stddev = np.zeros(weights.shape)
    flagged = np.where(weights == 0.0)
    nonflagged = np.where(weights > 0.0)
    if screen_type == 'phase':
        # Use circular stddev
        residual = normalize_phase(residual)
        residual_nan = residual.copy()
        residual_nan[flagged] = np.nan
        screen_stddev = nancircstd(residual_nan, axis=0)
    elif screen_type == 'amplitude':
        # Use log residuals
        screen_stddev = np.sqrt(np.average(residual[nonflagged]**2,
            weights=weights[nonflagged], axis=0))

    # Compare residuals to stddev of the screen
    outlier_ind = np.where(np.abs(residual) > nsigma*screen_stddev)
    weights[outlier_ind] = 0.0

    return weights


def circ_chi2(samples, weights):
    """
    Compute the circular chi^2

    Based on scipy.stats.circstd

    Parameters
    ----------
    samples : array_like
        Input array.
    weights : array_like
        Input array.

    Returns
    -------
    chi2 : float
        Circular chi^2.
    """
    import numpy as np

    unflagged = np.where(weights > 0.0)
    x1 = np.sin(samples[unflagged])
    x2 = np.cos(samples[unflagged])
    meanx1, sumw = np.average(x1**2, weights=weights[unflagged], returned=True)
    meanx2, sumw = np.average(x2**2, weights=weights[unflagged], returned=True)
    R = np.hypot(meanx1, meanx2)
    var = (1.0 - R)
    if np.isnan(var):
        0/0

    return var * sumw


def calculate_svd(pp, r_0, beta, N_piercepoints):
    """
    Returns result (U) of svd for K-L vectors

    Parameters
    ----------
    pp : array
        Array of piercepoint locations
    r_0: float
        Scale size of amp fluctuations (m)
    beta: float
        Power-law index for amp structure function (5/3 => pure Kolmogorov
        turbulence)
    N_piercepoints : int
        Number of piercepoints

    Returns
    -------
    C : array
        C matrix
    pinvC : array
        Inv(C) matrix
    U : array
        Unitary matrix

    """
    import numpy as np
    from pylab import kron, concatenate, pinv, norm, newaxis, find, amin, svd, eye

    D = np.resize(pp, (N_piercepoints, N_piercepoints, 3))
    D = np.transpose(D, (1, 0, 2)) - D
    D2 = np.sum(D**2, axis=2)
    C = -(D2 / r_0**2)**(beta / 2.0) / 2.0
    pinvC = pinv(C, rcond=1e-3)
    U, S, V = svd(C)

    return C, pinvC, U


def fit_screen(station_names, source_names, full_matrices, pp, rr, weights, order, r_0, beta,
    screen_type):
    """
    Fits a screen to amplitudes or phases using Karhunen-Lo`eve base vectors

    Parameters
    ----------
    station_names: array
        Array of station names
    source_names: array
        Array of source names
    full_matrices : list of arrays
        List of [C, pivC, U] matrices for all piercepoints
    pp: array
        Array of piercepoint locations
    airmass: array
        Array of airmass values (note: not currently used)
    rr: array
        Array of amp values to fit screen to
    weights: array
        Array of weights
    order: int
        Order of screen (i.e., number of KL base vectors to keep)
    r_0: float
        Scale size of amp fluctuations (m)
    beta: float
        Power-law index for amp structure function (5/3 => pure Kolmogorov
        turbulence)
    screen_type : str
        Type of screen: 'phase' or 'amplitude'

    Returns
    -------
    screen_fit_white_all, screen_residual_all : array, array
        Arrays of screen and residual (actual - screen) values

    """
    import numpy as np
    from pylab import kron, concatenate, pinv, norm, newaxis, find, amin, svd, eye

    # Identify flagged directions
    N_sources_all = len(source_names)
    unflagged = np.where(weights > 0.0)
    N_sources = len(source_names[unflagged])

    # Initialize arrays
    N_stations = len(station_names)
    N_piercepoints = N_sources * N_stations
    N_piercepoints_all = N_sources_all * N_stations
    screen_fit_all = np.zeros((N_sources_all, N_stations))
    pp_all = pp.copy()
    rr_all = rr.copy()
    pp = pp_all[unflagged[0], :]
    w = np.diag(weights[unflagged])

    # Calculate matrices
    if N_sources == N_sources_all:
        C, pinvC, U = full_matrices
    else:
        # Recalculate for unflagged directions
        C, pinvC, U = calculate_svd(pp, r_0, beta, N_piercepoints)
    invU = pinv(np.dot(np.transpose(U[:, :order]), np.dot(w, U)[:, :order]), rcond=1e-3)

    # Fit screen to unflagged directions
    if screen_type == 'phase':
        # Change phase to real/imag
        rr_real = np.cos(rr[unflagged])
        rr_imag = np.sin(rr[unflagged])

        # Calculate real screen
        rr1 = np.dot(np.transpose(U[:, :order]), np.dot(w, rr_real))
        real_fit = np.dot(pinvC, np.dot(U[:, :order], np.dot(invU, rr1)))

        # Calculate imag screen
        rr1 = np.dot(np.transpose(U[:, :order]), np.dot(w, rr_imag))
        imag_fit = np.dot(pinvC, np.dot(U[:, :order], np.dot(invU, rr1)))

        # Calculate phase screen
        screen_fit = np.arctan2(np.dot(C, imag_fit), np.dot(C, real_fit))
        screen_fit_white = np.dot(pinvC, screen_fit)
    else:
        # Calculate log(amp) screen
        rr = rr[unflagged]
        rr1 = np.dot(np.transpose(U[:, :order]), np.dot(w, np.log10(rr)))
        amp_fit_log = np.dot(pinvC, np.dot(U[:, :order], np.dot(invU, rr1)))

        # Calculate amp screen
        screen_fit = 10**(np.dot(C, amp_fit_log))
        screen_fit_white = np.dot(pinvC, screen_fit)

    # Calculate screen in all directions
    if N_sources != N_sources_all:
        screen_fit_all[unflagged[0], :] = screen_fit[:, newaxis]
        flagged = np.where(weights <= 0.0)
        for findx in flagged[0]:
            p = pp_all[findx, :]
            d2 = np.sum(np.square(pp - p), axis=1)
            c = -(d2 / ( r_0**2 ))**(beta / 2.0) / 2.0
            screen_fit_all[findx, :] = np.dot(c, screen_fit_white)
        C, pinvC, U = full_matrices
        screen_fit_white_all = np.dot(pinvC, screen_fit_all)
        screen_residual_all = rr_all - screen_fit_all.reshape(N_piercepoints_all)
    else:
        screen_fit_white_all = screen_fit_white
        screen_residual_all = rr_all - np.dot(C, screen_fit_white)
    screen_fit_white_all = screen_fit_white_all.reshape((N_sources_all, N_stations))
    screen_residual_all = screen_residual_all.reshape((N_sources_all, N_stations))

    return (screen_fit_white_all, screen_residual_all)


def run(soltab, outsoltab, order=12, beta=5.0/3.0, ncpu=0, niter=2, nsigma=5.0,
    refAnt=-1, scale_order=True, scale_dist=None, min_order=5, adjust_order=True):
    """
    Fits station screens to input soltab (type 'phase' or 'amplitude' only).

    The results of the fit are stored in the soltab parent solset in "outsoltab"
    and the residual values (actual - screen) are stored in "outsoltabresid".
    These values are the screen amplitude values per station per pierce point
    per solution interval. The pierce point locations are stored in an auxiliary
    array in the output soltabs.

    Screens can be plotted with the PLOTSCREEN operation.

    Parameters
    ----------
    soltab: solution table
        Soltab containing amplitude solutions
    outsoltab: str
        Name of output soltab
    order : int, optional
        Order of screen (i.e., number of KL base vectors to keep). If the order
        is scaled by dist (scale_order = True), the order is calculated as
        order * sqrt(dist/scale_dist)
    beta: float, optional
        Power-law index for amp structure function (5/3 => pure Kolmogorov
        turbulence)
    ncpu: int, optional
        Number of CPUs to use. If 0, all are used
    niter: int, optional
        Number of iterations to do when determining weights
    nsigma: float, optional
        Number of sigma above which directions are flagged
    refAnt: str or int, optional
        Index (if int) or name (if str) of reference station (-1 => no ref)
    scale_order : bool, optional
        If True, scale the screen order with sqrt of distance/scale_dist to the
        reference station
    scale_dist : float, optional
        Distance used to normalize the distances used to scale the screen order.
        If None, the max distance is used
    adjust_order : bool, optional
        If True, adjust the screen order to obtain a reduced chi^2 of approx.
        unity
    min_order : int, optional
        The minimum allowed order if adjust_order = True.

    """
    import numpy as np
    from numpy import newaxis
    import re
    import os
    try:
        import progressbar
    except ImportError:
        import losoto.progressbar as progressbar

    # input check
    if ncpu == 0:
        import multiprocessing
        ncpu = multiprocessing.cpu_count()

    # Get screen type
    screen_type = soltab.getType()
    if screen_type not in ['phase', 'amplitude']:
        logging.error('Screens can only be fit to soltabs of type "phase" or "amplitude".')
        return 1
    logging.info('Using solution table {0} to calculate {1} screens'.format(soltab.name, screen_type))

    # Load values, etc.
    r_full = np.array(soltab.val)
    weights_full = soltab.weight[:]
    times = np.array(soltab.time)
    freqs = soltab.freq[:]
    axis_names = soltab.getAxesNames()
    freq_ind = axis_names.index('freq')
    dir_ind = axis_names.index('dir')
    time_ind = axis_names.index('time')
    ant_ind = axis_names.index('ant')
    if 'pol' in axis_names:
        is_scalar = False
        pol_ind = axis_names.index('pol')
        N_pols = len(soltab.pol[:])
        r_full = r_full.transpose([dir_ind, time_ind, freq_ind, ant_ind, pol_ind])
        weights_full = weights_full.transpose([dir_ind, time_ind, freq_ind, ant_ind, pol_ind])
    else:
        is_scalar = True
        N_pols = 1
        r_full = r_full.transpose([dir_ind, time_ind, freq_ind, ant_ind])
        r_full = r_full[:, :, :, :, newaxis]
        weights_full = weights_full.transpose([dir_ind, time_ind, freq_ind, ant_ind])
        weights_full = weights_full[:, :, :, :, newaxis]

    # Collect station and source names and positions and times, making sure
    # that they are ordered correctly.
    solset = soltab.getSolset()
    source_names = soltab.dir[:]
    source_dict = solset.getSou()
    source_positions = []
    for source in source_names:
        source_positions.append(source_dict[source])
    station_names = soltab.ant[:]
    station_dict = solset.getAnt()
    station_positions = []
    for station in station_names:
        station_positions.append(station_dict[station])
    N_sources = len(source_names)
    N_times = len(times)
    N_stations = len(station_names)
    N_freqs = len(freqs)
    N_piercepoints = N_sources

    # Set ref station
    if type(refAnt) is str:
        if N_stations == 1:
            refAnt = -1
        elif refAnt in station_names:
            refAnt = station_names.index(refAnt)
        else:
            refAnt = -1

    if scale_order:
        dist = []
        if refAnt == -1:
            station_order = [order] * N_stations
        else:
            for s in range(len(station_names)):
                dist.append(get_ant_dist(station_positions[s], station_positions[refAnt]))
            if scale_dist is None:
                scale_dist = max(dist)
            logging.info('Using variable order (with max order = {0} '
                'and scaling dist = {1} m)'.format(order, scale_dist))
            station_order = []
            for s in range(len(station_names)):
                station_order.append(max(min_order, min(order, int(order * np.sqrt(dist[s] / scale_dist)))))
    else:
        station_order = [order] * len(station_names)
        logging.info('Using order = {0}'.format(order))

    # Initialize various arrays and parameters
    screen = np.zeros((N_sources, N_stations, N_times, N_freqs, N_pols))
    residual = np.zeros((N_sources, N_stations, N_times, N_freqs, N_pols))
    screen_order = np.zeros((N_stations, N_times, N_freqs, N_pols))
    r_0 = 100
    target_redchi2 = 1.0

    # Calculate full piercepoint arrays
    pp_list = []
    full_matrices = []
    for s in range(N_stations):
        pp_s, midRA, midDec = calculate_piercepoints(np.array([station_positions[s]]),
            np.array(source_positions))
        pp_list.append(pp_s)
        full_matrices.append(calculate_svd(pp_s, r_0, beta, N_piercepoints))

    # Fit station screens
    N_total = N_freqs * N_pols * N_stations * niter * N_times
    pbar = progressbar.ProgressBar(maxval=N_total).start()
    ipbar = 0
    for freq_ind in range(N_freqs):
        for pol_ind in range(N_pols):
            r = r_full[:, :, freq_ind, :, pol_ind] # order is now [dir, time, ant]
            r = r.transpose([0, 2, 1]) # order is now [dir, ant, time]
            weights = weights_full[:, :, freq_ind, :, pol_ind]
            weights = weights.transpose([0, 2, 1])

            # Fit screens
            for s, stat in enumerate(station_names):
                if s == refAnt and screen_type == 'phase':
                    # skip reference station (phase-type only)
                    continue
                screen_order[s, :, freq_ind, pol_ind] = order
                rr = np.reshape(r[:, s, :], [N_piercepoints, N_times])
                pp = pp_list[s]

                # Iterate:
                # 1. fit screens
                # 2. flag nsigma outliers
                # 3. refit with new weights
                # 4. repeat for niter
                station_weights = weights[:, s, :]
                init_station_weights = weights[:, s, :].copy() # preserve initial weights
                for iterindx in range(niter):
                    if iterindx > 0:
                        # Flag outliers
                        if screen_type == 'phase':
                            # Use circular stddev
                            screen_diff = residual[:, s, :, freq_ind, pol_ind]
                        elif screen_type == 'amplitude':
                            # Use log residuals
                            screen_diff = np.log10(rr) - np.log10(rr -
                                residual[:, s, :, freq_ind, pol_ind])
                        station_weights = flag_outliers(init_station_weights,
                                screen_diff, nsigma, screen_type)

                    # Fit the screens
                    norderiter = 1
                    if adjust_order:
                        if iterindx > 0:
                            norderiter = 4
                    for tindx, t in enumerate(times):
                        N_unflagged = np.where(station_weights[:, tindx] > 0.0)[0].size
                        if screen_order[s, tindx, freq_ind, pol_ind] > N_unflagged-1:
                            screen_order[s, tindx, freq_ind, pol_ind] = N_unflagged-1
                        hit_upper = False
                        hit_lower = False
                        hit_upper2 = False
                        hit_lower2 = False
                        sign = 1.0
                        for oindx in range(norderiter):
                            skip_fit = False
                            if iterindx > 0:
                                if np.all(station_weights[:, tindx] == prev_station_weights[:, tindx]):
                                    if not adjust_order:
                                        # stop fitting if weights did not change
                                        break
                                    elif oindx == 0:
                                        # Skip the fit for first iteration, as it is the same as the prev one
                                        skip_fit = True
                            if not np.all(station_weights[:, tindx] == 0.0) and not skip_fit:
                                scr, res = fit_screen([stat], source_names, full_matrices[s],
                                    pp[:, :], rr[:, tindx], station_weights[:, tindx],
                                    screen_order[s, tindx, freq_ind, pol_ind], r_0, beta, screen_type)
                                screen[:, s, tindx, freq_ind, pol_ind] = scr[:, 0]
                                residual[:, s, tindx, freq_ind, pol_ind] = res[:, 0]

                            if hit_lower2 or hit_upper2:
                                break

                            if adjust_order and iterindx > 0:
                                if screen_type == 'phase':
                                    redchi2 =  circ_chi2(residual[:, s, tindx, freq_ind, pol_ind],
                                        station_weights[:, tindx]) / (N_unflagged - screen_order[s, tindx, freq_ind, pol_ind])
                                else:
                                    redchi2 = np.sum(np.square(residual[:, s, tindx, freq_ind, pol_ind]) *
                                        station_weights[:, tindx]) / (N_unflagged - screen_order[s, tindx, freq_ind, pol_ind])
                                if oindx > 0:
                                    if redchi2 > 1.0 and prev_redchi2 < redchi2:
                                        sign *= -1
                                    if redchi2 < 1.0 and prev_redchi2 > redchi2:
                                        sign *= -1
                                prev_redchi2 = redchi2
                                order_factor = (N_unflagged - screen_order[s, tindx, freq_ind, pol_ind])**0.2
                                target_order = float(screen_order[s, tindx, freq_ind, pol_ind]) - sign * order_factor * (target_redchi2 - redchi2)
                                target_order = max(station_order[s], target_order)
                                target_order = min(int(round(target_order)), N_unflagged-1)
                                if target_order <= 0:
                                    target_order = min(station_order[s], N_unflagged-1)
                                if target_order == screen_order[s, tindx, freq_ind, pol_ind]:# don't fit again if order is the same as last one
                                    break
                                if target_order == N_unflagged-1:# check whether we've been here before. If so, break
                                    if hit_upper:
                                        hit_upper2 = True
                                    hit_upper = True
                                if target_order == station_order[s]:# check whether we've been here before. If so, break
                                    if hit_lower:
                                        hit_lower2 = True
                                    hit_lower = True
                                screen_order[s, tindx, freq_ind, pol_ind] = target_order
                        pbar.update(ipbar)
                        ipbar += 1
                    prev_station_weights = station_weights.copy()
                weights[:, s, :] = station_weights
            weights_full[:, :, freq_ind, :, pol_ind] = weights.transpose([0, 2, 1]) # order is now [dir, time, ant]
    pbar.finish()

    # Write the results to the output solset
    dirs_out = source_names
    times_out = times
    ants_out = station_names
    freqs_out = freqs

    # Store screen values
    vals = screen.transpose([2, 3, 1, 0, 4]) # order is now ['time', 'freq', 'ant', 'dir', 'pol']
    weights = weights_full.transpose([1, 2, 3, 0, 4]) # order is now ['time', 'freq', 'ant', 'dir', 'pol']
    if is_scalar:
        screen_st = solset.makeSoltab('{}screen'.format(screen_type), outsoltab,
            axesNames=['time', 'freq', 'ant', 'dir'], axesVals=[times_out, freqs_out,
            ants_out, dirs_out], vals=vals[:, :, :, :, 0], weights=weights[:, :, :, :, 0])
        vals = residual.transpose([2, 3, 1, 0, 4])
        weights = np.zeros(vals.shape)
        for d in range(N_sources):
            # Store the screen order as the weights of the residual soltab
            weights[:, :, :, d, :] = screen_order.transpose([1, 2, 0, 3]) # order is now [time, ant, freq, pol]
        resscreen_st = solset.makeSoltab('{}screenresid'.format(screen_type), outsoltab+'resid',
            axesNames=['time', 'freq', 'ant', 'dir'], axesVals=[times_out, freqs_out,
            ants_out, dirs_out], vals=vals[:, :, :, :, 0], weights=weights[:, :, :, :, 0])
    else:
        pols_out = soltab.pol[:]
        screen_st = solset.makeSoltab('{}screen'.format(screen_type), outsoltab,
            axesNames=['time', 'freq', 'ant', 'dir', 'pol'], axesVals=[times_out, freqs_out,
            ants_out, dirs_out, pols_out], vals=vals, weights=weights)
        vals = residual.transpose([2, 3, 1, 0, 4])
        weights = np.zeros(vals.shape)
        for d in range(N_sources):
            # Store the screen order as the weights of the residual soltab
            weights[:, :, :, d, :] = screen_order.transpose([1, 2, 0, 3]) # order is now [time, ant, freq, pol]
        resscreen_st = solset.makeSoltab('{}screenresid'.format(screen_type), outsoltab+'resid',
            axesNames=['time', 'freq', 'ant', 'dir', 'pol'], axesVals=[times_out, freqs_out,
            ants_out, dirs_out, pols_out], vals=vals, weights=weights)

    # Store beta, r_0, height, and order as attributes of the screen soltabs
    screen_st.obj._v_attrs['beta'] = beta
    screen_st.obj._v_attrs['r_0'] = r_0
    screen_st.obj._v_attrs['height'] = 0.0
    screen_st.obj._v_attrs['midra'] = midRA
    screen_st.obj._v_attrs['middec'] = midDec

    # Store piercepoint table. Note that it does not conform to the axis
    # shapes, so we cannot use makeSoltab()
    solset.obj._v_file.create_array('/'+solset.name+'/'+screen_st.obj._v_name,
        'piercepoint', obj=pp)

    screen_st.addHistory('CREATE (by STATIONSCREEN operation)')
    resscreen_st.addHistory('CREATE (by STATIONSCREEN operation)')

    return 0
