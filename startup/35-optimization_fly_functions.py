import bluesky.plans as bp
import bluesky.plan_stubs as bps


motor_dict = {sample_stage.x.name: {'position': sample_stage.x},
              sample_stage.y.name: {'position': sample_stage.y},
              sample_stage.z.name: {'position': sample_stage.z},
              }

bound_vals = [(75, 79), (37, 41), (19, 21)]
motor_bounds = {}
motor_dict_keys = list(motor_dict.keys())
for k in range(len(motor_dict_keys)):
    motor_bounds[motor_dict_keys[k]] = {'position': [bound_vals[k][0],
                                                     bound_vals[k][1]]}


def calc_velocity(motors, dists, velocity_limits, max_velocity=None, min_velocity=None):
    """
    Calculates velocities of all motors

    Velocities calculated will allow motors to approximately start and stop together

    Parameters
    ----------
    motors : dict
             In the format {motor_name: motor_object}
             Ex. {sample_stage.x.name: sample_stage.x}
    dists : list
            List of distances each motor has to move
    velocity_limits : list of dicts
                      list of dicts for each motor. Dictionary has keys of motor, low, high;
                      values are motor_name, velocity low limit, velocity high limit
    max_velocity : float
                   Set this to limit the absolute highest velocity of any motor
    min_velocity : float
                   Set this to limit the absolute lowest velocity of any motor

    Returns
    -------
    ret_vels : list
               List of velocities for each motor
    """
    ret_vels = []
    # check that max_velocity is not None if at least 1 motor doesn't have upper velocity limit
    if any([lim['high'] == 0 for lim in velocity_limits]) and max_velocity is None:
        vel_max_lim_0 = []
        for lim in velocity_limits:
            if lim['high'] == 0:
                vel_max_lim_0.append(lim['motor'])
        raise ValueError(f'The following motors have unset max velocity limits: {vel_max_lim_0}. '
                         f'max_velocity must be set')
    if all([d == 0 for d in dists]):
        # TODO: fix this to handle when motors don't need to move
        # if dists are all 0, set all motors to min velocity
        for i in range(len(velocity_limits)):
            ret_vels.append(velocity_limits[i]['low'])
        return ret_vels
    else:
        # check for negative distances
        if any([d < 0.0 for d in dists]):
            raise ValueError("Distances must be positive. Try using abs()")
        # create list of upper velocity limits for convenience
        upper_velocity_bounds = []
        for j in range(len(velocity_limits)):
            upper_velocity_bounds.append(velocity_limits[j]['high'])
        # find max distances to move and pick the slowest motor of those with max dists
        max_dist_lowest_vel = np.where(dists == np.max(dists))[0]
        max_dist_to_move = -1
        for j in max_dist_lowest_vel:
            if dists[j] >= max_dist_to_move:
                max_dist_to_move = dists[j]
                motor_index_to_use = j
        max_dist_vel = upper_velocity_bounds[motor_index_to_use]
        if max_velocity is not None:
            if max_dist_vel > max_velocity or max_dist_vel == 0:
                max_dist_vel = float(max_velocity)
        time_needed = dists[motor_index_to_use] / max_dist_vel
        for i in range(len(velocity_limits)):
            if i != motor_index_to_use:
                try_vel = np.round(dists[i] / time_needed, 5)
                if try_vel < min_velocity:
                    try_vel = min_velocity
                if try_vel < velocity_limits[i]['low']:
                    try_vel = velocity_limits[i]['low']
                elif try_vel > velocity_limits[i]['high']:
                    if upper_velocity_bounds[i] == 0:
                        pass
                    else:
                        break
                ret_vels.append(try_vel)
            else:
                ret_vels.append(max_dist_vel)
        if len(ret_vels) == len(motors):
            # if all velocities work, return velocities
            return ret_vels
        else:
            # use slowest motor that moves the most
            ret_vels.clear()
            lowest_velocity_motors = np.where(upper_velocity_bounds ==
                                              np.min(upper_velocity_bounds))[0]
            max_dist_to_move = -1
            for k in lowest_velocity_motors:
                if dists[k] >= max_dist_to_move:
                    max_dist_to_move = dists[k]
                    motor_index_to_use = k
            slow_motor_vel = upper_velocity_bounds[motor_index_to_use]
            if max_velocity is not None:
                if slow_motor_vel > max_velocity or slow_motor_vel == 0:
                    slow_motor_vel = float(max_velocity)
            time_needed = dists[motor_index_to_use] / slow_motor_vel
            for k in range(len(velocity_limits)):
                if k != motor_index_to_use:
                    try_vel = np.round(dists[k] / time_needed, 5)
                    if try_vel < min_velocity:
                        try_vel = min_velocity
                    if try_vel < velocity_limits[k]['low']:
                        try_vel = velocity_limits[k]['low']
                    elif try_vel > velocity_limits[k]['high']:
                        if upper_velocity_bounds[k] == 0:
                            pass
                        else:
                            print("Don't want to be here")
                            raise ValueError("Something terribly wrong happened")
                    ret_vels.append(try_vel)
                else:
                    ret_vels.append(slow_motor_vel)
            return ret_vels


def run_hardware_fly(motors, detector, population, max_velocity, min_velocity):
    uid_list = []
    flyers = generate_hardware_flyers(motors=motors, detector=detector, population=population,
                             max_velocity=max_velocity, min_velocity=min_velocity)
    for flyer in flyers:
        yield from bp.fly([flyer])
    for i in range(-len(flyers), 0):
        uid_list.append(i)
    # TODO: update later for use with newer bluesky
    # uid = (yield from bp.fly([hf]))
    # uid_list.append(uid)
    return uid_list


def generate_hardware_flyers(motors, detector, population, max_velocity, min_velocity):
    hf_flyers = []
    velocities_list = []
    distances_list = []
    for i, pparam in enumerate(population):
        velocities_dict = {}
        distances_dict = {}
        dists = []
        velocity_limits = []
        if i == 0:
            for elem, param in motors.items():
                for param_name, elem_obj in param.items():
                    velocity_limit_dict = {'motor': elem,
                                           'low': elem_obj.velocity.low_limit,
                                           'high': elem_obj.velocity.high_limit}
                    velocity_limits.append(velocity_limit_dict)
                    dists.append(0)
        else:
            for elem, param in motors.items():
                for param_name, elem_obj in param.items():
                    velocity_limit_dict = {'motor': elem,
                                           'low': elem_obj.velocity.low_limit,
                                           'high': elem_obj.velocity.high_limit}
                    velocity_limits.append(velocity_limit_dict)
                    dists.append(abs(pparam[elem][param_name] - population[i - 1][elem][param_name]))
        velocities = calc_velocity(motors=motors.keys(), dists=dists, velocity_limits=velocity_limits,
                                   max_velocity=max_velocity, min_velocity=min_velocity)
        for motor_name, vel, dist in zip(motors, velocities, dists):
            velocities_dict[motor_name] = vel
            distances_dict[motor_name] = dist
        velocities_list.append(velocities_dict)
        distances_list.append(distances_dict)

    # Validation
    times_list = []
    for dist, vel in zip(distances_list, velocities_list):
        times_dict = {}
        for motor_name in motors.keys():
            if vel[motor_name] == 0:
                time_ = 0
            else:
                time_ = dist[motor_name] / vel[motor_name]
            times_dict[motor_name] = time_
        times_list.append(times_dict)

    for param, vel, time_ in zip(population, velocities_list, times_list):
        hf = HardwareFlyer(params_to_change=param,
                           velocities=vel,
                           time_to_travel=time_,
                           detector=detector,
                           motors=motors)
        hf_flyers.append(hf)
    return hf_flyers


def check_opt_bounds(motors, bounds):
    for elem, param in bounds.items():
        for param_name, bound in param.items():
            if bound[0] > bound[1]:
                raise ValueError(f"Invalid bounds for {elem}. Current bounds are set to "
                                 f"{bound[0], bound[1]}, but lower bound is greater than "
                                 f"upper bound")
            if bound[0] < motors[elem][param_name].low_limit or bound[1] >\
                    motors[elem][param_name].high_limit:
                raise ValueError(f"Invalid bounds for {elem}. Current bounds are set to "
                                 f"{bound[0], bound[1]}, but {elem} has bounds of "
                                 f"{motors[elem][param_name].limits}")


def move_to_optimized_positions(motors, opt_pos):
    """Move motors to best positions"""
    mv_params = []
    for elem, param in motors.items():
        for param_name, elem_obj in param.items():
            mv_params.append(elem_obj)
            mv_params.append(opt_pos[elem][param_name])
    yield from bps.mv(*mv_params)
