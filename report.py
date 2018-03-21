#!/usr/bin/env python3
#https://support.alexa.com/hc/en-us/articles/200461990-Can-I-get-a-list-of-top-sites-from-an-API-
#http://s3.amazonaws.com/alexa-static/top-1m.csv.zip

import sys
if sys.version < '3':
    raise RuntimeError("Requires Python 3")

import db
import os
import csv
import time,datetime,pytz
import subprocess
import math
import hosts_usg

MAX_HOST_REPORT = 10
MAX_IP_REPORT = 10

def gen_report(dbc,smin,smax,desc):
    """Given a database connection, generate a report for those with an offset of smin..smax"""

    # This query appears to need to use HAVING instead of WHERE because it is based on MAX(ABS(offset))
    cmd = "SELECT host,MAX(ABS(offset)) AS oset FROM times " \
          "WHERE abs(offset)>={} and abs(offset)<={} GROUP BY host HAVING TRUE ".format(smin,smax)
    cmd += " order by host "
    cmd += " LIMIT {}".format(MAX_HOST_REPORT)
    cursor = dbc.execute(cmd)
    hosts = [row[0] for row in cursor.fetchall()]
    print("Negative time delta means that the remote host thinks that it is in the past.")
    print("Hosts where clocks are off {}: {}".format(desc,len(hosts)))
    print(cmd)
    print("time: {:.1f} sec".format(dbc.execute_last))
    print("\n")
    if len(hosts)==MAX_HOST_REPORT:
        print("(Only {} hosts are reported)".format(MAX_HOST_REPORT))

    fmt1 = "{:38}   {:>10} {:>10}        {:>10}"
    fmt2 = "{:38}   {:10} {:10} ({:3.0f}%) {:10} "
    fmt3 = "   {:38}{:10} {:10}        {:10} "
    print(fmt1.format("Host","Total","Wrong","Max Offset"))

    for host in hosts:
        # Print the summary
        (qcount,wtcount) = dbc.select1("SELECT SUM(qcount),SUM(wtcount) FROM dated WHERE host=%s AND ipaddr!=''",(host,))

        # Find the most wrong
        cmd = "SELECT offset,host,ipaddr FROM times WHERE host=%s AND ipaddr!='' "+\
              "ORDER BY offset desc limit 1"
        (offset,host,ipaddr) = dbc.select1(cmd, (host,))
        print(fmt2.format(host,qcount,wtcount,wtcount*100/qcount,webtime.s_to_hms(offset)))

        # Get the list of IP addresses and loop for each
        cursor = dbc.execute("SELECT distinct ipaddr FROM dated where host=%s and ipaddr!='' LIMIT {}".format(MAX_IP_REPORT),(host,))
        ipaddrs = [row[0] for row in cursor]

        if len(ipaddrs)==MAX_IP_REPORT:
            print("(Only {} IP addresses are reported)".format(MAX_IP_REPORT))
        for ipaddr in ipaddrs:
            qcount = dbc.select1("select sum(qcount) from dated where host=%s and ipaddr=%s",(host,ipaddr))[0]
            (offset_max,offset_count) = dbc.select1("select max(offset),count(offset) from times where host=%s and ipaddr=%s",(host,ipaddr))
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

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--verbose",action="store_true",help="output to STDOUT")
    parser.add_argument("--config",help="config file",required=True)
    parser.add_argument("--host",help="Specify a host")
    parser.add_argument("report",nargs="*",help="Specify which reports are requested. options: counts hosts size offset all")

    args = parser.parse_args()
    config = db.get_mysql_config(args.config)
    dbc    = db.mysql(config,mode='ro')

    if args.debug:
        dbc.debug = args.debug
        print("debug mode")

    print("Report generated: {}".format(datetime.datetime.now().isoformat()))

    if not args.report:
        print("No report specified; running counts")
        args.report = ['counts']


    if 'counts' in args.report:
        cmd = "select min(qdate),max(qdate) from dated "
        (date_min,date_max) = dbc.select1(cmd)

        print("Dates of study: {} to {} ({})".format(date_min,date_max,date_max-date_min))

        cmd = "select host,qdatetime,now()-qdatetime from times order by qdatetime desc limit 1"
        (host,most_recent,seconds) = dbc.select1(cmd)
        print("Most recent wrong measurement: {}  ({} seconds ago) ({})".format(most_recent,seconds,host))

        for level in ['INFO','ERR']:
            import tabulate
            print("Last 10 {} log messages:".format(level))
            print(tabulate.tabulate(dbc.execute("select modified,cpu,memfree,value from log where level=%s order by modified desc limit 10",(level,)).fetchall(),
                                    headers=['date','cpu','memfree','message']))
            print("\n")

    if 'hosts' in args.report:
        cmd = "select count(distinct host), count(distinct ipaddr), sum(qcount) from dated "
        (hostCount,ipaddrCount,sumQcount) = dbc.select1(cmd)

        print("Total number of distinct hosts examined: {:,}  ({:,} IP addresses)".format(hostCount,ipaddrCount))
        print("Number of time measurements: {:,}".format(sumQcount))
      

    if 'size' in args.report:
        print("Database size:")
        for (table,) in dbc.execute("show tables").fetchall():
            (count,) = dbc.select1("select count(1) from {}".format(table))
            print("Table {:20} {:10,} rows".format(table,count))
        print("\n")


    if 'offset' in args.report:
        cmd = "select count(distinct host), count(distinct ipaddr) from dated where wtcount>0 "

        (badHosts,badIpaddrs) = dbc.select1(cmd)

        print("Number of hosts with at least one incorrect time measurement: {:,} ({:.2f}%)".
              format(badHosts,badHosts*100.0/hostCount))
        print("Number of IP addresses with at least one incorrect time measurement: {:,} ({:.2f}%)".
              format(badIpaddrs,badIpaddrs*100.0/ipaddrCount))

        gen_report(dbc,1,60,"1 to 59 seconds")
        gen_report(dbc,60,3600,"1 minute to 1 hour")
        gen_report(dbc,3600,60*60*24,"1 hour to 1 day")
        gen_report(dbc,60*60*24,60*60*24*31,"1 day to 1 month")
        gen_report(dbc,60*60*24*31,0,"more than a month")
