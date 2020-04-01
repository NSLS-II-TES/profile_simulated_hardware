# import random
import numpy as np


# start detector
def start_detector(detector):
    """Set-up and start detector"""
    pass


# read detector
def read_detector(detector, pos):
    """
    Read detector

    Uses motor positions to create a gaussian type signal. Gaussian center is 48.2,
    width is 10, and amplitude is 10

    Parameters
    ----------
    detector : detector object
    pos : array_like
          Positions of motors

    Returns
    -------
    intensity : float
                Gaussian curve signal

    """
    pos_list = [.2 * elm for elm in pos]
    pos = sum(pos_list)
    cen = 48.2
    wid = 10
    amp = 10
    intensity = np.exp(-((pos - cen) ** 2) / (2. * wid ** 2)) * amp
    return intensity
    # return random.randint(0, 100)


def stop_detector(detector):
    """Stop detector"""
    pass
