from nslsii import configure_base
from IPython import get_ipython

configure_base(get_ipython().user_ns, 'local',
               publish_documents_with_kafka=True)

bec.disable_plots()

# Optional: set any metadata that rarely changes.
RE.md['beamline_id'] = 'TES-opt'
