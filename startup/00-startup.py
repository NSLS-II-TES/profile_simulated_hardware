print(f'Loading {__file__}...')

import time as ttime

durations = {}

start = ttime.monotonic()

from nslsii import configure_base
from IPython import get_ipython

configure_base(get_ipython().user_ns, 'local',
               publish_documents_with_kafka=True)

bec.disable_plots()

# Optional: set any metadata that rarely changes.
RE.md['beamline_id'] = 'TES-opt'

duration = ttime.monotonic() - start  # seconds
durations[__file__] = duration
