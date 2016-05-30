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
MAX_HOSTS_REPORT = 10

usg_hosts_sql = " host in (select host from hosts where usg=1) "

def gen_report(conn,smin,smax,desc):
    c = conn.cursor()
    cmd = "select host,max(offset) as oset from times group by host having true "
    if args.usg:
        cmd += " and " + usg_hosts_sql + " "
    if smin:
        cmd += " and oset>={} ".format(smin)
    if smax:
        cmd += " and oset<{} ".format(smax)
    cmd += " order by host "
    c.execute(cmd)
    hosts = [row[0] for row in c.fetchall()]
    print("Hosts where clocks are off {}: {}".format(desc,len(hosts)))
    print("\n")
    if len(hosts)>MAX_HOSTS_REPORT:
        print("Representative hosts:")
        hosts = hosts[0:MAX_HOSTS_REPORT]

    fmt1 = "{:36}   {:>10} {:>10}        {:>10}"
    fmt2 = "{:36}   {:10} {:10} ({:3.0f}%) {:10} "
    fmt3 = "   {:36}{:10} {:10}        {:10} "
    print(fmt1.format("Host","Total","Wrong","Max Offset"))

    for host in hosts:
        # Print the summary
        c.execute("select sum(qcount),sum(wtcount) from dated where host=%s and ipaddr!=''",(host,))
        (qcount,wtcount) = c.fetchone()

        # Find the most wrong
        cmd = "select offset,host,ipaddr from times having host=%s and ipaddr!='' "+\
              "order by offset desc limit 1"
        c.execute(cmd, (host,))
        (offset,host,ipaddr)  = c.fetchone()
        print(fmt2.format(host,qcount,wtcount,wtcount*100/qcount,webtime.s_to_hms(offset)))

        # Get the list of IP addresses and loop for each
        c.execute("select distinct ipaddr from dated where host=%s and ipaddr!=''",(host,))
        ipaddrs = [row[0] for row in c.fetchall()]

        for ipaddr in ipaddrs:
            c.execute("select sum(qcount) from dated where host=%s and ipaddr=%s",(host,ipaddr))
            qcount = c.fetchone()[0]
            cmd = "select max(offset),count(offset) from times where host=%s and ipaddr=%s"
            c.execute(cmd,(host,ipaddr))
            (offset_max,offset_count) = c.fetchone()
            if offset_max==None:
                offset_max = 0
            if offset_count==None:
                offset_count = 0
            print(fmt3.format(ipaddr,qcount,offset_count,webtime.s_to_hms(offset_max)))

        print("")
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

    hosts = webtime.usg_hosts()
    #
    # 
    # Overall stats
    #
    cmd = "select count(distinct host), count(distinct ipaddr),min(qdate),max(qdate),sum(qcount)"+\
          "from dated "
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
