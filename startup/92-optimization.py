import time as ttime
import bluesky.plans as bp
import bluesky.plan_stubs as bps

import sirepo_bluesky.sirepo_flyer as sf

from collections import deque

from ophyd.sim import NullStatus, new_uid

import numpy as np
import random


class BlueskyFlyer:
    def __init__(self):
        self.name = 'bluesky_flyer'
        self._asset_docs_cache = deque()
        self._resource_uids = []
        self._datum_counter = None
        self._datum_ids = []

    def kickoff(self):
        return NullStatus()

    def complete(self):
        return NullStatus()

    def describe_collect(self):
        return {self.name: {}}

    def collect(self):
        now = ttime.time()
        data = {}
        yield {'data': data,
               'timestamps': {key: now for key in data},
               'time': now,
               'filled': {key: False for key in data}}

    def collect_asset_docs(self):
        items = list(self._asset_docs_cache)
        self._asset_docs_cache.clear()
        for item in items:
            yield item


class HardwareFlyer(BlueskyFlyer):
    def __init__(self, params_to_change, velocities, time_to_travel,
                 detector, motors):
        super().__init__()
        self.name = 'tes_hardware_flyer'

        # TODO: These 3 lists to be merged later
        self.params_to_change = params_to_change  # dict of dicts; {motor_name: {'position':...}}
        self.velocities = velocities  # dictionary with motor names as keys
        self.time_to_travel = time_to_travel  # dictionary with motor names as keys

        self.detector = detector
        self.motors = motors

        self.watch_positions = {name: {'position': []} for name in self.motors}
        self.watch_intensities = []
        self.watch_timestamps = []

        self.motor_move_status = None

    def kickoff(self):
        # get initial positions of each motor (done externally)
        # calculate distances to travel (done externally)
        # calculate velocities (done externally)
        # preset the velocities (done in the class)
        # start movement (done in the class)
        # motors status returned, use later in complete (done in the class)

        slowest_motor = sorted(self.time_to_travel,
                               key=lambda x: self.time_to_travel[x],
                               reverse=True)[0]

        start_detector(self.detector)

        # Call this function once before we start moving all motors to collect the first points.
        self._watch_function()

        for motor_name, field in self.motors.items():
            for field_name, motor_obj in field.items():
                motor_obj.velocity.put(self.velocities[motor_name])

        for motor_name, field in self.motors.items():
            for field_name, motor_obj in field.items():
                if motor_name == slowest_motor:
                    self.motor_move_status = motor_obj.set(self.params_to_change[motor_name][field_name])
                else:
                    motor_obj.set(self.params_to_change[motor_name][field_name])

        self.motor_move_status.watch(self._watch_function)

        return NullStatus()

    def complete(self):
        # all motors arrived
        stop_detector(self.detector)
        return self.motor_move_status

    def describe_collect(self):

        return_dict = {self.name:
                       {f'{self.name}_intensity':
                        {'source': f'{self.name}_intensity',
                         'dtype': 'number',
                         'shape': []},
                        }
                       }

        motor_dict = {}
        for motor_name in self.motors.keys():
             motor_dict[f'{self.name}_{motor_name}_velocity'] = {'source': f'{self.name}_{motor_name}_velocity',
                                                                 'dtype': 'number', 'shape': []}
             motor_dict[f'{self.name}_{motor_name}_position'] = {'source': f'{self.name}_{motor_name}_position',
                                                                 'dtype': 'number', 'shape': []}
        return_dict[self.name].update(motor_dict)

        return return_dict

    def collect(self):
        for ind in range(len(self.watch_intensities)):
            motor_dict = {}
            for motor_name, field in self.motors.items():
                for field_name, motor_obj in field.items():
                    motor_dict.update(
                        {f'{self.name}_{motor_name}_velocity': self.velocities[motor_name],
                         f'{self.name}_{motor_name}_position': self.watch_positions[motor_name][field_name][ind]}
                    )

            data = {f'{self.name}_intensity': self.watch_intensities[ind]}
            data.update(motor_dict)

            yield {'data': data,
                   'timestamps': {key: self.watch_timestamps[ind] for key in data},
                   'time': self.watch_timestamps[ind],
                   'filled': {key: False for key in data}}

        # # This will produce one event with dictionaries in the <...>_parameters field.
        # motor_params_dict = {}
        # for motor_name, motor_obj in self.motors.items():
        #     motor_parameters = {'timestamps': self.watch_timestamps,
        #                         'velocity': self.velocities[motor_name],
        #                         'positions': self.watch_positions[motor_name]}
        #     motor_params_dict[motor_name] = motor_parameters
        #
        # data = {f'{self.name}_{self.detector.channel1.rois.roi01.name}': self.watch_intensities,
        #         f'{self.name}_parameters': motor_params_dict}
        #
        # now = ttime.time()
        # yield {'data': data,
        #        'timestamps': {key: now for key in data}, 'time': now,
        #        'filled': {key: False for key in data}}

    def _watch_function(self, *args, **kwargs):
        self.watch_positions, self.watch_intensities,\
        self.watch_timestamps = watch_function(self.motors, self.detector)


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

# TODO: merge "params_to_change" and "velocities" lists of dictionaries to become lists of dicts of dicts.


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
    print(f'LEN OF FLYERS {len(flyers)}')
    for flyer in flyers:
        yield from bp.fly([flyer])
    for i in range(-len(flyers), 0):
        uid_list.append(i)
    # uid = (yield from bp.fly([hf]))
    # uid_list.append(uid)
    return uid_list


def run_fly_sim(population, num_interm_vals, num_scans_at_once,
                sim_id, server_name, root_dir, watch_name, run_parallel):
    uid_list = []
    flyers = generate_sim_flyers(population=population, num_between_vals=num_interm_vals,
                             sim_id=sim_id, server_name=server_name, root_dir=root_dir,
                             watch_name=watch_name, run_parallel=run_parallel)
    # make list of flyers into list of list of flyers
    # pass 1 sublist of flyers at a time
    flyers = [flyers[i:i+num_scans_at_once] for i in range(0, len(flyers), num_scans_at_once)]
    for i in range(len(flyers)):
        # uids = (yield from bp.fly(flyers[i]))
        yield from bp.fly(flyers[i])
        # uid_list.append(uids)
    for i in range(-len(flyers), 0):
        uid_list.append(i)
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

    print('VELOCITY LIMITS', velocity_limits)

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


def generate_sim_flyers(population, num_between_vals,
                    sim_id, server_name, root_dir, watch_name, run_parallel):
    flyers = []
    params_to_change = []
    for i in range(len(population) - 1):
        between_param_linspaces = []
        if i == 0:
            params_to_change.append(population[i])
        for elem, param in population[i].items():
            for param_name, pos in param.items():
                between_param_linspaces.append(np.linspace(pos, population[i + 1][elem][param_name],
                                                           (num_between_vals + 2))[1:-1])

        for j in range(len(between_param_linspaces[0])):
            ctr = 0
            indv = {}
            for elem, param in population[0].items():
                indv[elem] = {}
                for param_name in param.keys():
                    indv[elem][param_name] = between_param_linspaces[ctr][j]
                    ctr += 1
            params_to_change.append(indv)
        params_to_change.append(population[i + 1])
    for param in params_to_change:
        sim_flyer = sf.SirepoFlyer(sim_id=sim_id, server_name=server_name,
                                   root_dir=root_dir, params_to_change=[param],
                                   watch_name=watch_name, run_parallel=run_parallel)
        flyers.append(sim_flyer)
    return flyers


def omea_evaluation(motors, bounds, popsize, num_interm_vals, num_scans_at_once,
                    uids, flyer_name, intensity_name):
    if motors is not None:
        # hardware
        # get the data from databroker
        current_fly_data = []
        pop_intensity = []
        pop_positions = []
        max_intensities = []
        max_int_pos = []
        for uid in uids:
            current_fly_data.append(db[uid].table(flyer_name))
        for i, t in enumerate(current_fly_data):
            pop_pos_dict = {}
            positions_dict = {}
            max_int_index = t[f'{flyer_name}_{intensity_name}'].idxmax()
            for elem, param in motors.items():
                positions_dict[elem] = {}
                pop_pos_dict[elem] = {}
                for param_name in param.keys():
                    positions_dict[elem][param_name] = t[f'{flyer_name}_{elem}_{param_name}'][max_int_index]
                    pop_pos_dict[elem][param_name] = t[f'{flyer_name}_{elem}_{param_name}'][len(t)]
            pop_intensity.append(t[f'{flyer_name}_{intensity_name}'][len(t)])
            max_intensities.append(t[f'{flyer_name}_{intensity_name}'][max_int_index])
            pop_positions.append(pop_pos_dict)
            max_int_pos.append(positions_dict)
        # compare max of each fly scan to population
        # replace population/intensity with higher vals, if they exist
        for i in range(len(max_intensities)):
            if max_intensities[i] > pop_intensity[i]:
                pop_intensity[i] = max_intensities[i]
                for elem, param in max_int_pos[i].items():
                    for param_name, pos in param.items():
                        pop_positions[i][elem][param_name] = pos
        return pop_positions, pop_intensity
    elif bounds is not None and popsize is not None and num_interm_vals is\
        not None and num_scans_at_once is not None and motors is None:
        # sirepo simulation
        pop_positions = []
        pop_intensities = []
        # get data from databroker
        fly_data = []
        # for i in range(-int(num_records), 0):
        for uid in uids:
            fly_data.append(db[uid].table(flyer_name))
        interm_pos = []
        interm_int = []
        for i in fly_data:
            print(i)
        # Create all sets of indices for population values first
        pop_indxs = [[0, 1]]
        while len(pop_indxs) < popsize:
            i_index = pop_indxs[-1][0]
            j_index = pop_indxs[-1][1]
            pre_mod_val = j_index + num_interm_vals + 1
            mod_res = pre_mod_val % num_scans_at_once
            int_div_res = pre_mod_val // num_scans_at_once
            if mod_res == 0:
                i_index = i_index + (int_div_res - 1)
                j_index = pre_mod_val
            else:
                i_index = i_index + int_div_res
                j_index = mod_res
            pop_indxs.append([i_index, j_index])
        curr_pop_index = 0
        for i in range(len(fly_data)):
            curr_interm_pos = []
            curr_interm_int = []
            for j in range(1, len(fly_data[i]) + 1):
                if (i == pop_indxs[curr_pop_index][0] and
                        j == pop_indxs[curr_pop_index][1]):
                    pop_intensities.append(fly_data[i][f'{flyer_name}_{intensity_name}'][j])
                    indv = {}
                    for elem, param in bounds.items():
                        indv[elem] = {}
                        for param_name in param.keys():
                            indv[elem][param_name] = fly_data[i][f'{flyer_name}_{elem}_{param_name}'][j]
                    pop_positions.append(indv)
                    curr_pop_index += 1
                else:
                    curr_interm_int.append(fly_data[i][f'{flyer_name}_{intensity_name}'][j])
                    indv = {}
                    for elem, param in bounds.items():
                        indv[elem] = {}
                        for param_name in param.keys():
                            indv[elem][param_name] = fly_data[i][f'{flyer_name}_{elem}_{param_name}'][j]
                    curr_interm_pos.append(indv)
            interm_pos.append(curr_interm_pos)
            interm_int.append(curr_interm_int)
        # picking best positions
        interm_max_idx = []
        print('OMEA: LEN OF INTERM_INT', len(interm_int))
        for i in range(len(interm_int)):
            curr_max_int = np.max(interm_int[i])
            interm_max_idx.append(interm_int[i].index(curr_max_int))
        print('OMEA: LEN OF interm_max_idx', len(interm_max_idx))
        print('OMEA: LEN OF pop_intensities', len(pop_intensities))
        for i in range(len(interm_max_idx)):
            if interm_int[i][interm_max_idx[i]] > pop_intensities[i + 1]:
                pop_intensities[i + 1] = interm_int[i][interm_max_idx[i]]
                pop_positions[i + 1] = interm_pos[i][interm_max_idx[i]]
        return pop_positions, pop_intensities


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


def ensure_bounds(vec, bounds):
    # Makes sure each individual stays within bounds and adjusts them if they aren't
    vec_new = {}
    # cycle through each variable in vector
    for elem, param in vec.items():
        vec_new[elem] = {}
        for param_name, pos in param.items():
            # variable exceeds the minimum boundary
            if pos < bounds[elem][param_name][0]:
                vec_new[elem][param_name] = bounds[elem][param_name][0]
            # variable exceeds the maximum boundary
            if pos > bounds[elem][param_name][1]:
                vec_new[elem][param_name] = bounds[elem][param_name][1]
            # the variable is fine
            if bounds[elem][param_name][0] <= pos <= bounds[elem][param_name][1]:
                vec_new[elem][param_name] = pos
    return vec_new


def rand_1(pop, popsize, target_indx, mut, bounds):
    # mutation strategy
    # v = x_r1 + F * (x_r2 - x_r3)
    idxs = [idx for idx in range(popsize) if idx != target_indx]
    a, b, c = np.random.choice(idxs, 3, replace=False)
    x_1 = pop[a]
    x_2 = pop[b]
    x_3 = pop[c]

    v_donor = {}
    for elem, param in x_1.items():
        v_donor[elem] = {}
        for param_name in param.keys():
            v_donor[elem][param_name] = x_1[elem][param_name] + mut *\
                                        (x_3[elem][param_name] - x_3[elem][param_name])
    v_donor = ensure_bounds(vec=v_donor, bounds=bounds)
    return v_donor


def best_1(pop, popsize, target_indx, mut, bounds, ind_sol):
    # mutation strategy
    # v = x_best + F * (x_r1 - x_r2)
    x_best = pop[ind_sol.index(np.max(ind_sol))]
    idxs = [idx for idx in range(popsize) if idx != target_indx]
    a, b = np.random.choice(idxs, 2, replace=False)
    x_1 = pop[a]
    x_2 = pop[b]

    v_donor = {}
    for elem, param in x_best.items():
        v_donor[elem] = {}
        for param_name in param.items():
            v_donor[elem][param_name] = x_best[elem][param_name] + mut * \
                                        (x_1[elem][param_name] - x_2[elem][param_name])
    v_donor = ensure_bounds(vec=v_donor, bounds=bounds)
    return v_donor


def mutate(population, strategy, mut, bounds, ind_sol):
    mutated_indv = []
    for i in range(len(population)):
        if strategy == 'rand/1':
            v_donor = rand_1(pop=population, popsize=len(population), target_indx=i,
                             mut=mut, bounds=bounds)
        elif strategy == 'best/1':
            v_donor = best_1(pop=population, popsize=len(population), target_indx=i,
                             mut=mut, bounds=bounds, ind_sol=ind_sol)
        # elif strategy == 'current-to-best/1':
        #     v_donor = current_to_best_1(population, len(population), i, mut, bounds, ind_sol)
        # elif strategy == 'best/2':
        #     v_donor = best_2(population, len(population), i, mut, bounds, ind_sol)
        # elif strategy == 'rand/2':
        #     v_donor = rand_2(population, len(population), i, mut, bounds)
        mutated_indv.append(v_donor)
    return mutated_indv


def crossover(population, mutated_indv, crosspb):
    crossover_indv = []
    for i in range(len(population)):
        x_t = population[i]
        v_trial = {}
        for elem, param in x_t.items():
            v_trial[elem] = {}
            for param_name, pos in param.items():
                crossover_val = random.random()
                if crossover_val <= crosspb:
                    v_trial[elem][param_name] = mutated_indv[i][elem][param_name]
                else:
                    v_trial[elem][param_name] = x_t[elem][param_name]
        crossover_indv.append(v_trial)
    return crossover_indv


def create_selection_params(motors, population, cross_indv):
    if motors is not None and population is None:
        # hardware
        positions = [elm for elm in cross_indv]
        indv = {}
        for elem, field in motors.items():
            indv[elem] = {}
            for field_name, elem_obj in field.items():
                indv[elem][field_name] = elem_obj.user_readback.get()
        positions.insert(0, indv)
        return positions
    if motors is None and population is not None:
        # sirepo simulation
        positions = [elm for elm in cross_indv]
        positions.insert(0, population[0])
        return positions


def create_rand_selection_params(motors, population, intensities, bounds):
    if motors is not None and population is None:
        # hardware
        positions = []
        change_indx = intensities.index(np.min(intensities))
        indv = {}
        for elem, param in motors.items():
            indv[elem] = {}
            for param_name, elem_obj in param.items():
                indv[elem][param_name] = elem_obj.user_readback.get()
        positions.append(indv)
        indv = {}
        for elem, param in bounds.items():
            indv[elem] = {}
            for param_name, bound in param.items():
                indv[elem][param_name] = random.uniform(bound[0], bound[1])
        positions.append(indv)
        return positions, change_indx
    elif motors is None and population is not None:
        # sirepo simulation
        positions = []
        change_indx = intensities.index(np.min(intensities))
        positions.append(population[0])
        indv = {}
        for elem, param in bounds.items():
            indv[elem] = {}
            for param_name, bound in param.items():
                indv[elem][param_name] = random.uniform(bound[0], bound[1])
        positions.append(indv)
        return positions, change_indx


def select(population, intensities, motors, bounds, num_interm_vals,
           num_scans_at_once, uids, flyer_name, intensity_name):
    if motors is not None:
        # hardware
        new_population, new_intensities = omea_evaluation(motors=motors, bounds=bounds, popsize=None,
                                                          num_interm_vals=None, num_scans_at_once=None,
                                                          uids=uids, flyer_name=flyer_name,
                                                          intensity_name=intensity_name)
    else:
        new_population, new_intensities = omea_evaluation(motors=None, bounds=bounds, popsize=len(population) + 1,
                                                          num_interm_vals=num_interm_vals,
                                                          num_scans_at_once=num_scans_at_once,
                                                          uids=uids, flyer_name=flyer_name,
                                                          intensity_name=intensity_name)
    del new_population[0]
    del new_intensities[0]
    assert len(new_population) == len(population)
    for i in range(len(new_intensities)):
        if new_intensities[i] > intensities[i]:
            population[i] = new_population[i]
            intensities[i] = new_intensities[i]
    if motors is None:
        population.reverse()
        intensities.reverse()
    return population, intensities


def move_to_optimized_positions(motors, opt_pos):
    """Move motors to best positions"""
    mv_params = []
    for elem, param in motors.items():
        for param_name, elem_obj in param.items():
            mv_params.append(elem_obj)
            mv_params.append(opt_pos[elem][param_name])
    yield from bps.mv(*mv_params)


def optimize(fly_plan, bounds, motors=None, detector=None, max_velocity=0.2, min_velocity=0,
             run_parallel=None, num_interm_vals=None, num_scans_at_once=None, sim_id=None,
             server_name=None, root_dir=None, watch_name=None, popsize=5, crosspb=.8, mut=.1,
             mut_type='rand/1', threshold=0, max_iter=100, flyer_name='tes_hardware_flyer',
             intensity_name='intensity', opt_type='hardware'):
    """
    Optimize beamline using hardware flyers and differential evolution

    Custom plan to optimize motor positions of the TES beamline using differential evolution

    Parameters
    ----------
    fly_plan : callable
               Fly scan plan for current type of flyer.
               Currently the only option is `run_hardware_fly`, but another will be added for sirepo simulations
    motors : dict
             Keys are motor names and values are motor objects
    detector : detector object or None
               Detector to use, or None if no detector will be used
    bounds : dict of dicts
             Keys are motor names and values are dicts of low and high bounds. See format below.
             {'motor_name': {'low': lower_bound, 'high': upper_bound}}
    max_velocity : float, optional
                   Absolute maximum velocity for all motors
                   Default is 0.2
    min_velocity : float, optional
                   Absolute minumum velocity for all motors
    popsize : int, optional
              Size of population
    crosspb : float, optional
              Probability of crossover. Must be in range [0, 1]
    mut : float, optional
          Mutation factor. Must be in range [0, 1]
    mut_type : {'rand/1', 'best/1'}, optional
               Mutation strategy to use. 'rand/1' chooses random individuals to compare to.
               'best/1' uses the best individual to compare to.
               Default is 'rand/1'
    threshold : float, optional
                Threshold that intensity must be greater than or equal to to stop execution
    max_iter : int, optional
               Maximum iterations to allow
    flyer_name : str, optional
                 Name of flyer. DataBroker stream name
                 Default is 'tes_hardware_flyer'
    intensity_name : {'intensity', 'mean'}, optional
                     Hardware optimization would use 'intensity'. Sirepo optimization would use 'mean'
                     Default is 'intensity'
    """
    global optimized_positions
    if opt_type == 'hardware':
        # make sure all parameters needed for hardware optimization aren't None
        needed_params = [motors]
        if any(p is None for p in needed_params):
            invalid_params = []
            for p in range(len(needed_params)):
                if needed_params[p] is None:
                    invalid_params.append(needed_params[p])
            raise ValueError(f'The following parameters are set to None, but '
                             f'need to be set: {invalid_params}')
        # check if bounds passed in are within the actual bounds of the motors
        check_opt_bounds(motors, bounds)
        # create initial population
        initial_population = []
        for i in range(popsize):
            indv = {}
            if i == 0:
                for elem, param in motors.items():
                    indv[elem] = {}
                    for param_name, elem_obj in param.items():
                        indv[elem][param_name] = elem_obj.user_readback.get()
            else:
                for elem, param in bounds.items():
                    indv[elem] = {}
                    for param_name, bound in param.items():
                        indv[elem][param_name] = random.uniform(bound[0], bound[1])
            initial_population.append(indv)
        uid_list = (yield from fly_plan(motors=motors, detector=detector, population=initial_population,
                                        max_velocity=max_velocity, min_velocity=min_velocity))
        pop_positions, pop_intensity = omea_evaluation(motors=motors, bounds=None, popsize=None, num_interm_vals=None,
                                                       num_scans_at_once=None, uids=uid_list, flyer_name=flyer_name,
                                                       intensity_name=intensity_name)
    elif opt_type == 'sirepo':
        # make sure all parameters needed for hardware optimization aren't None
        needed_params = [run_parallel, num_interm_vals, num_scans_at_once, sim_id, server_name, root_dir, watch_name]
        if any(p is None for p in needed_params):
            invalid_params = []
            for p in range(len(needed_params)):
                if needed_params[p] is None:
                    invalid_params.append(needed_params[p])
            raise ValueError(f'The following parameters are set to None, but '
                             f'need to be set: {invalid_params}')
        # Initial population
        initial_population = []
        for i in range(popsize):
            indv = {}
            for elem, param in bounds.items():
                indv[elem] = {}
                for param_name, bound in param.items():
                    indv[elem][param_name] = random.uniform(bound[0], bound[1])
            initial_population.append(indv)
        first_optic = list(bounds.keys())[0]
        first_param_name = list(bounds[first_optic].keys())[0]
        initial_population = sorted(initial_population, key=lambda kv: kv[first_optic][first_param_name])
        uid_list = (yield from fly_plan(population=initial_population, num_interm_vals=num_interm_vals,
                                        num_scans_at_once=num_scans_at_once, sim_id=sim_id, server_name=server_name,
                                        root_dir=root_dir, watch_name=watch_name, run_parallel=run_parallel))
        pop_positions, pop_intensity = omea_evaluation(motors=None, bounds=bounds, popsize=len(initial_population),
                                                       num_interm_vals=num_interm_vals,
                                                       num_scans_at_once=num_scans_at_once, uids=uid_list,
                                                       flyer_name=flyer_name, intensity_name=intensity_name)
        pop_positions.reverse()
        pop_intensity.reverse()
    else:
        raise ValueError(f'Opt_type {opt_type} is invalid. Choose either hardware or sirepo')
    # Termination conditions
    v = 0  # generation number
    consec_best_ctr = 0  # counting successive generations with no change to best value
    old_best_fit_val = 0
    best_fitness = [0]
    while not ((v > max_iter) or (consec_best_ctr >= 5 and old_best_fit_val >= threshold)):
        print(f'GENERATION {v + 1}')
        best_gen_sol = []
        # mutate
        mutated_trial_pop = mutate(population=pop_positions, strategy=mut_type, mut=mut,
                                   bounds=bounds, ind_sol=pop_intensity)
        # crossover
        cross_trial_pop = crossover(population=pop_positions, mutated_indv=mutated_trial_pop,
                                    crosspb=crosspb)
        # select
        if opt_type == 'hardware':
            select_positions = create_selection_params(motors=motors, population=None,
                                                       cross_indv=cross_trial_pop)
            uid_list = (yield from fly_plan(motors=motors, detector=detector, population=select_positions,
                                            max_velocity=max_velocity, min_velocity=min_velocity))

            pop_positions, pop_intensity = select(population=pop_positions, intensities=pop_intensity,
                                                  motors=motors, bounds=None, num_interm_vals=None,
                                                  num_scans_at_once=None, uids=uid_list,
                                                  flyer_name=flyer_name, intensity_name=intensity_name)
        else:
            select_positions = create_selection_params(motors=None, population=pop_positions,
                                                       cross_indv=cross_trial_pop)
            uid_list = (yield from fly_plan(population=select_positions, num_interm_vals=num_interm_vals,
                                            num_scans_at_once=num_scans_at_once, sim_id=sim_id,
                                            server_name=server_name, root_dir=root_dir,
                                            watch_name=watch_name, run_parallel=run_parallel))
            pop_positions, pop_intensity = select(population=pop_positions, intensities=pop_intensity,
                                                  motors=None, bounds=bounds, num_interm_vals=num_interm_vals,
                                                  num_scans_at_once=num_scans_at_once, uids=uid_list,
                                                  flyer_name=flyer_name, intensity_name=intensity_name)
        # get best solution
        gen_best = np.max(pop_intensity)
        best_indv = pop_positions[pop_intensity.index(gen_best)]
        best_gen_sol.append(best_indv)
        best_fitness.append(gen_best)

        print('      > FITNESS:', gen_best)
        print('         > BEST POSITIONS:', best_indv)

        v += 1
        if np.round(gen_best, 6) == np.round(old_best_fit_val, 6):
            consec_best_ctr += 1
            print('Counter:', consec_best_ctr)
        else:
            consec_best_ctr = 0
        old_best_fit_val = gen_best

        if consec_best_ctr >= 5 and old_best_fit_val >= threshold:
            print('Finished')
            break
        else:
            if opt_type == 'hardware':
                positions, change_indx = create_rand_selection_params(motors=motors, population=None,
                                                                      intensities=pop_intensity, bounds=bounds)
                uid_list = (yield from fly_plan(motors=motors, detector=detector, population=positions,
                                                max_velocity=max_velocity, min_velocity=min_velocity))
                rand_pop, rand_int = select(population=[pop_positions[change_indx]],
                                            intensities=[pop_intensity[change_indx]],
                                            motors=motors, bounds=bounds, num_interm_vals=None, num_scans_at_once=None,
                                            uids=uid_list, flyer_name=flyer_name, intensity_name=intensity_name)
            else:
                positions, change_indx = create_rand_selection_params(motors=None, population=pop_positions,
                                                                      intensities=pop_intensity, bounds=bounds)
                uid_list = (yield from fly_plan(population=positions, num_interm_vals=num_interm_vals,
                                                num_scans_at_once=num_scans_at_once, sim_id=sim_id,
                                                server_name=server_name, root_dir=root_dir, watch_name=watch_name,
                                                run_parallel=run_parallel))
                rand_pop, rand_int = select(population=[pop_positions[change_indx]],
                                            intensities=[pop_intensity[change_indx]], motors=None, bounds=bounds,
                                            num_interm_vals=num_interm_vals, num_scans_at_once=num_scans_at_once,
                                            uids=uid_list, flyer_name=flyer_name, intensity_name=intensity_name)
            assert len(rand_pop) == 1 and len(rand_int) == 1
            pop_positions[change_indx] = rand_pop[0]
            pop_intensity[change_indx] = rand_int[0]

    # best solution overall should be last one
    x_best = best_gen_sol[-1]
    optimized_positions = x_best
    print('\nThe best individual is', x_best, 'with a fitness of', gen_best)
    print('It took', v, 'generations')

    if opt_type == 'hardware':
        print('Moving to optimal positions')
        yield from move_to_optimized_positions(motors, optimized_positions)
        print('Done')

    plot_index = np.arange(len(best_fitness))
    plt.figure()
    plt.plot(plot_index, best_fitness)
