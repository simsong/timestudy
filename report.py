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
MAX_DOMAINS_REPORT = 10

usg_hosts_sql = " host in (select host from usg) "

def gen_report(conn,smin,smax,desc):
    c = conn.cursor()
    cmd = "select host,max(abs(delta)) as oset from times group by host having true "
    if args.usg:
        cmd += " and " + usg_hosts_sql + " "
    if smin:
        cmd += " and oset>={} ".format(smin)
    if smax:
        cmd += " and oset<{} ".format(smax)
    cmd += " order by host "
    print(cmd)
    c.execute(cmd)
    domains = [row[0] for row in c.fetchall()]
    print("Hosts where clocks are off {}: {}".format(desc,len(domains)))
    print("\n")
    if len(domains)>MAX_DOMAINS_REPORT:
        print("Representative domains:")
        domains = domains[0:MAX_DOMAINS_REPORT]

    fmt1 = "{:30}   {:10}"
    fmt2 = "{:30}   {:10} ({:.2f}%)"
    print(fmt1.format("Domain","Wrong Readings"))

    for domain in domains:
        c.execute("select sum(qcount),sum(wtcount) from dated where host=%s and ipaddr!=''",(domain,))
        (qcount,wtcount) = c.fetchone()
        print(fmt2.format(domain,qcount,wtcount*100/qcount))
    print("\n\n")
    
                                                                                      

if __name__=="__main__":
    import argparse
    from bs4 import BeautifulSoup, SoupStrainer
    import webtime

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--verbose",action="store_true",help="output to STDOUT")
    parser.add_argument("--mysql",action="store_true",help="output to MySQL DB",default=True)
    parser.add_argument("--mongo",action="store_true",help="output to MongoDB")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    parser.add_argument("--host",help="Specify a host")
    parser.add_argument("--usg",action="store_true",help="Only USG")

    args = parser.parse_args()
    config = webtime.get_config(args)

    # Make sure mySQL works
    w = webtime.WebLogger(args.debug)
    w.mysql_config = config["mysql"]
    conn = w.mysql_connect(cache=False)       # test it out
    c = conn.cursor()
    if args.debug: print("MySQL Connected")

    domains = webtime.usg_domains()
    #
    # 
    # Overall stats
    #
    cmd = "select count(distinct host), count(distinct ipaddr),min(qdate),max(qdate),sum(qcount) from dated "
    if args.usg:
        cmd += " where " + usg_hosts_sql 
    c.execute(cmd)
    (hostCount,ipaddrCount,date_min,date_max,sumQcount) = c.fetchone()


    print("Total number of hosts examined: {}  ({} IP addresses)".format(hostCount,ipaddrCount))
    print("Dates of study: {} to {}".format(date_min,date_max))
    print("Number of time measurements: {}".format(sumQcount))

    cmd = "select count(distinct host), count(distinct ipaddr) from dated where wtcount>0 "
    if args.usg:
        cmd += " and " + usg_hosts_sql 
    c.execute(cmd)
    (badHosts,badIpaddrs) = c.fetchone()

    print("Number of hosts with at least one incorrect time measurement: {} ({:.2f}%)".format(badHosts,badHosts*100.0/hostCount))
    print("Number of IP addresses with at least one incorrect time measurement: {} ({:.2f}%)".format(badIpaddrs,badIpaddrs*100.0/ipaddrCount))

    gen_report(conn,1,60,"1 to 59 seconds")
    gen_report(conn,60,3600,"1 minute to 1 hour")
    gen_report(conn,3600,60*60*24,"1 hour to 1 day")
    gen_report(conn,60*60*24,60*60*24*31,"1 day to 1 month")
    gen_report(conn,60*60*24*31,0,"more than a month")
