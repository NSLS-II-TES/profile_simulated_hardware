import bluesky.plans as bp


sample_stage.x.user_setpoint.kind = 'hinted'

RE(bp.scan([], sample_stage.x, -5, 5, 11))
