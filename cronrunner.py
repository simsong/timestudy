#!/usr/bin/python3
#
# cronrunner.py:
# meant to be called from cron. Automatically runs webtime if another one is not running

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


MIN_TIME = 1.0                # Resolution of remote websites
CONFIG_INI = "config.ini"
DEFAULT_DELAY = 300

if __name__=="__main__":
    import argparse
    import configparser
    import fcntl
    import sys

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--debug",action="store_true",help="actually run subprocess")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)

    args   = parser.parse_args()
    config = db.get_config(args)

    # Running from cron. Make sure only one of us is running. If another is running, exit
    fd = os.open(__file__,os.O_RDONLY)
    if fd>0:
        try:
            fcntl.flock(fd,fcntl.LOCK_EX)
        except IOError:
            print("Could not acquire lock")
            exit(0)
            

    # Make sure mySQL works. We do this here so that we don't report that we can't connect to MySQL after the loop starts.
    # We cache the results in w to avoid reundent connections to the MySQL server.
    
    mysql_connection = db.mysql_connect(config)
    c = mysql_connection.cursor()
    if args.debug:
        print("MySQL Connected")

    # If we are repeating, run self recursively (remove repeat args)
    while True and not args.debug:
        try:
            delay = int(config['cron']['repeat'])
        except RuntimeError as e:
            delay = DEFAULT_DELAY
            
        t0 = time.time()
        res = subprocess.call([sys.executable,'webtime.py'])
        t1 = time.time()
        took = t1-t0
        if took < DEFAULT_DELAY:
            time.sleep(DEFAULT_DELAY - took)

    # finally, release our lock. But this will never happen
    fcntl.flock(fd,fcntl.LOCK_UN)
