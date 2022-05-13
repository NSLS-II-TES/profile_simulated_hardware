print(f'Loading {__file__}...')

start = ttime.monotonic()

import numpy as np
import time as ttime


# start detector
def start_detector(detector):
    """Set-up and start detector"""
    pass


# read detector
def read_detector(detector, pos):
    """
    Read detector

    Uses motor positions to create a gaussian type signal. Gaussian center is 27.2,
    width is .2, and amplitude is 10

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
    cen = 27
    wid = .3
    amp = 5
    intensity = np.exp(-((pos - cen) ** 2) / (2. * wid ** 2)) * amp
    return intensity


def watch_function(motors, detector, *args, **kwargs):
    watch_positions = {name: {'position': []} for name in motors}
    watch_intensities = []
    watch_timestamps = []
    pos_list = []
    for motor_name, field in motors.items():
        for field_name, motor_obj in field.items():
            pos_list.append(motor_obj.user_readback.get())
            watch_positions[motor_name][field_name].append(motor_obj.user_readback.get())
    watch_intensities.append(read_detector(detector, pos_list))
    watch_timestamps.append(ttime.time())
    return watch_positions, watch_intensities, watch_timestamps


def stop_detector(detector):
    """Stop detector"""
    pass

duration = ttime.monotonic() - start  # seconds
durations[__file__] = duration
