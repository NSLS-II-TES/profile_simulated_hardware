import random
import numpy as np


# start detector
def start_detector(detector):
    pass


# read detector
def read_detector(detector, x):
    x_list = [.2 * elm for elm in x]
    x = sum(x_list)
    cen = 219.8
    wid = 10
    amp = 10
    return np.exp(-((x - cen) ** 2) / (2. * wid ** 2)) * amp
    # return random.randint(0, 100)


# stop detector
def stop_detector(detector):
    pass
