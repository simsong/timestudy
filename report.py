#!/usr/bin/env python3
#https://support.alexa.com/hc/en-us/articles/200461990-Can-I-get-a-list-of-top-sites-from-an-API-
#http://s3.amazonaws.com/alexa-static/top-1m.csv.zip

import os
import csv
import time,datetime,pytz
import pymysql, pymysql.err
import MySQLdb, _mysql_exceptions
import subprocess
import sys
import math

CONFIG_INI = "config.ini"

def gen_report(conn,domains,smin,smax,desc):
    domains_str = ",".join(["'{}'".format(s) for s in domains])
    c = conn.cursor()
    c.execute("select host,max(delta) from times group by host having host in ("+domains_str+") and delta>=%s and delta<smax order by host,ipaddr;",
              (smin,smax))
    dlist = c.fetchall()
    for domain in dlist:
        print(row)
    
                                                                                      

if __name__=="__main__":
    import argparse
    from bs4 import BeautifulSoup, SoupStrainer
    import webtime

    parser = argparse.ArgumentParser()
    parser.add_argument('--usg',action='store_true')
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--verbose",action="store_true",help="output to STDOUT")
    parser.add_argument("--mysql",action="store_true",help="output to MySQL DB")
    parser.add_argument("--mongo",action="store_true",help="output to MongoDB")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    parser.add_argument("--host",help="Specify a host")

    args = parser.parse_args()
    config = webtime.get_config(args)

    # Make sure mySQL works
    if args.mysql:
        w = webtime.WebLogger(args.debug)
        w.mysql_config = config["mysql"]
        conn = w.mysql_connect(cache=False)       # test it out
        if args.debug: print("MySQL Connected")

    domains = webtime.usg_domains()
    #
    # 
    # Time in ranges
    gen_report(conn,domains,1,59,"< minute")
