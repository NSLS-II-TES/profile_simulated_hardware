from nslsii import configure_base
from IPython import get_ipython

try:
    configure_base(get_ipython().user_ns, 'local')
except FileNotFoundError:
    # This is needed for older nslsii.
    configure_base(get_ipython().user_ns, 'local',
                   configure_logging=False,
                   ipython_exec_logging=False)

bec.disable_plots()

# Optional: set any metadata that rarely changes.
RE.md['beamline_id'] = 'TES-opt'
