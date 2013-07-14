#!/usr/bin/python3
import sys, os
import logging

# set up logging
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)
fh = logging.FileHandler('iot.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter(fmt="%(asctime)s %(name)s [%(levelname)s]: %(message)s"))
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
rootLogger.addHandler(fh)
rootLogger.addHandler(ch)
logger = logging.getLogger(__name__)

from iot_db import *

##MAIN PROGRAM
init_db()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        logger.warning("No login given, running in test mode.")
    elif len(sys.argv) != 3:
        logger.critical("Usage: %s username password", os.path.basename(sys.argv[0]))
        exit(1)
    print("Not implemented")
    if db:
        db.close()
