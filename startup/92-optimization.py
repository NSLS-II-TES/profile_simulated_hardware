from bloptools.DE_opt_utils import run_hardware_fly
from bloptools.DE_optimization import optimization_plan


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

# run with:
# RE(optimization_plan(fly_plan=run_hardware_fly, bounds=motor_bounds, db=db, motors=motor_dict,
# detector=None, max_velocity=5, start_det=start_detector, read_det=read_detector,
# stop_det=stop_detector, watch_func=watch_function, threshold=4.5))
