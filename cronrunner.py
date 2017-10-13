#!/usr/bin/python3
#
# cronrunner.py:
# meant to be called from cron every 5 minutes...
# Attempts to get a lock on __file__.
# IF LOCKS: another copy isn't running.
#      - run webtime.py
# IF DOESN"T LOCK: another copy is running
#      - exit gracefully


import sys
if sys.version < '3':
    raise RuntimeError("Requires Python 3")


import os
import csv
import time,datetime
import subprocess
import sys
import math
import db
import fcntl


MIN_TIME = 1.0                # Resolution of remote websites
CONFIG_INI = "config.ini"
DEFAULT_DELAY = 300

def getlock(fname):
    fd = os.open(fname,os.O_RDONLY)
    if fd>0:
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB) # non-blocking
        except IOError:
            raise RuntimeError("Could not acquire lock")
    return fd
    
if __name__=="__main__":
    import argparse
    import configparser
    import fcntl
    import sys

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--debug",action="store_true",help="actually run subprocess")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)

    args   = parser.parse_args()
    config = db.get_mysql_config(args.config)

    # Running from cron. Make sure only one of us is running. If another is running, exit
    fd = getlock(__file__)
            
    # Make sure mySQL works. We do this here so that we don't report
    # that we can't connect to MySQL after the loop starts.  We cache
    # the results in w to avoid reundent connections to the MySQL
    # server.
    

    mysql_connection = db.mysql_connect(config)
    c = mysql_connection.cursor()
    if args.debug:
        print("MySQL Connected")

    t0 = time.time()
    res = subprocess.call([sys.executable,'webtime.py','--cron','--config',args.config])
    t1 = time.time()
    took = t1-t0

    # TODO: Log in the database our start and end time

    import logging
    import logging.handlers

    my_logger = logging.getLogger(__file__)
    my_logger.setLevel(logging.DEBUG)

    handler = logging.handlers.SysLogHandler(address = '/dev/log')

    my_logger.addHandler(handler)
    my_logger.info('Completed. took={}'.format(took))

    # finally, release our lock, so we can catch it again
    fcntl.flock(fd,fcntl.LOCK_UN)
