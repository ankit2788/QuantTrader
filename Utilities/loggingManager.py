import os
import logging
from datetime import datetime

from Utilities import Constants

logger = logging

_date = datetime.now().strftime("%Y%m%d")

logname = os.path.join(Constants.LOG_PATH, f"Logging_{_date}.log")

logging.basicConfig(filename=logname, filemode="w", \
                    format='%(asctime)s: %(name)s - %(levelname)s: %(message)s', \
                    datefmt = "%Y-%m-%d %H:%M:%S", \
                    level = logging.INFO)