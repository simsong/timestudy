#!/usr/bin/env python3
#
# report_html.py:
# output a report with a templating engine

#
import sys
if sys.version < '3':
    raise RuntimeError("Requires Python 3")

import os
import csv
import time,datetime,pytz
import subprocess
import math
import db
import configparser
import socket
import struct

if __name__=="__main__":
    import argparse
    import sys


    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--verbose",action="store_true",help="output to STDOUT")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    parser.add_argument("--host",help="Specify a host")
    parser.add_argument("--usg",action="store_true",help="Only USG")
