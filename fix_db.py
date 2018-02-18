#https://support.alexa.com/hc/en-us/articles/200461990-Can-I-get-a-list-of-top-sites-from-an-API-
#http://s3.amazonaws.com/alexa-static/top-1m.csv.zip

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
import json
import ipaddress

CONFIG_INI = "config.ini"

def fix_ipv6(addr):
    _str = socket.inet_pton(socket.AF_INET6, addr)
    a, b = struct.unpack('!2Q', _str)
    return ipaddress.ip_address(socket.inet_ntop(socket.AF_INET6, struct.pack('!2Q', a, b))).exploded


if __name__=="__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--verbose",action="store_true",help="Be more verbose")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    parser.add_argument("--db",action="store_true",help="When running interactive, write to the database")

    args = parser.parse_args()
    config = db.get_mysql_config(args.config)       # prep it with default MySQL parameters

    dbc = db.mysql(config)
    ver = dbc.mysql_version()
    if args.debug:
        print("MySQL Version {}".format(ver))

    #table='times'
    #for c in dbc.execute("select distinct ipaddr from "+table+" where ipaddr RLIKE ':.{1,3}:' LIMIT 1000").fetchall():
    #    print("{}: {:40} -> {:40}".format(table,c[0],fix_ipv6(c[0])))
    #    dbc.execute("update "+table+" set ipaddr=%s where ipaddr=%s",(fix_ipv6(c[0]),c[0]))

    # dated need to be automatically for 2017-11-03
    #table='dated';
    #for c in dbc.execute("select distinct ipaddr from "+table+" where ipaddr RLIKE ':.{1,3}:' and qdate!='2017-11-03' LIMIT 1000").fetchall():
    #    print("{}: {:40} -> {:40}".format(table,c[0],fix_ipv6(c[0])))
    #    dbc.execute("update "+table+" set ipaddr=%s where ipaddr=%s",(fix_ipv6(c[0]),c[0]))

    # Now fix the troublesome date
    table='dated'
    for (id,ipaddr) in dbc.execute("select distinct id,ipaddr from "+table+" where ipaddr RLIKE ':.{1,3}:' LIMIT 1000").fetchall():
        print("{} {}: {:40} -> {:40}".format(table,id,ipaddr,fix_ipv6(ipaddr)))

