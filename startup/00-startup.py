from nslsii import configure_base
from IPython import get_ipython

configure_base(get_ipython().user_ns, 'local',
               publish_documents_with_kafka=False)

bec.disable_plots()

# Optional: set any metadata that rarely changes.
RE.md['beamline_id'] = 'TES-opt'

############################# QAS logging tests ###############################
# See https://github.com/NSLS-II-QAS/profile_collection/pull/27.

import appdirs
import logging
import psutil
import subprocess
import sys

from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from pprint import pprint, pformat

logger_open_files = logging.getLogger("QAS")
logger_open_files.setLevel(logging.DEBUG)
# logger_open_files.setLevel(logging.INFO)
debug_log_file = str(Path(appdirs.user_log_dir(appname="bluesky")) / Path("debug-open-files.log"))
handler1 = TimedRotatingFileHandler(debug_log_file, when="M", backupCount=10)
handler1.setLevel(logging.DEBUG)
log_file_format = (
    "[%(levelname)1.1s %(asctime)s.%(msecs)03d %(name)s"
    "  %(module)s:%(lineno)d] %(message)s"
)
handler1.setFormatter(logging.Formatter(fmt=log_file_format))
logger_open_files.addHandler(handler1)
logger_open_files.propagate = False


def audit(event, args):
    if event == "open":
        logger_open_files.debug(f"Opening file: {args}")


def stop_callback(name, doc):
    res = subprocess.run("cat /proc/sys/fs/file-nr".split(), capture_output=True)
    nums = res.stdout.decode().split()

    proc = psutil.Process()

    logger_open_files.info(f"\nBluesky scan UID: {doc['run_start']}\n"
                           f"Current open files: {nums[0]}  |  Max open files: {nums[-1]}\n"
                           f"{pformat(proc.open_files())}")


# sys.addaudithook(audit)
RE.subscribe(stop_callback, name='stop')
