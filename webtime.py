#!/usr/bin/env python3
#https://support.alexa.com/hc/en-us/articles/200461990-Can-I-get-a-list-of-top-sites-from-an-API-
#http://s3.amazonaws.com/alexa-static/top-1m.csv.zip

import csv
import time
MP=10

MIN_TIME = 0.001
CONFIG_INI = "config.ini"

def ip2long(ip):
    import socket,struct
    """
    Convert an IP string to long
    """
    packedIP = socket.inet_aton(ip)
    return struct.unpack("!L", packedIP)[0]


class WebTime():
    def __init__(self,qhost=None,qipaddr=None,qtime=None,qduration=None,rdate=None,rcode=None,delta=None):
        self.qhost = qhost
        self.qipaddr= qipaddr
        self.qtime  = qtime
        self.qduration = qduration
        self.rdate  = rdate
        self.rcode  = rcode
        self.delta  = delta
    def ptime(self):
        if self.delta < 0:
            sign = "-"
            dt = -self.delta
        else:
            sign = " "
            dt = self.delta
        sec  = int(dt % 60)
        min  = int((dt/60) % 60)
        hour = int(dt / 3600)
        return "{:1}{:02}:{:02}:{:02}".format(sign,hour,min,sec)
    def __repr__(self):
        return "<WebTime {} {} {}>".format(self.qhost,self.qtime,self.delta)

def webtime_ip(host,ipaddr):
    import http,socket,email,sys
    """Find the webtime of a particular host and IP address"""
    RemoteDisconnected = http.client.BadStatusLine
    if sys.version>'3.5':
        RemoteDisconnected = http.client.RemoteDisconnected
    connection = http.client.HTTPConnection(ipaddr,timeout=5)
    try:
        url = "http://{}/".format(host)
        connection.request("HEAD",url)
        r = connection.getresponse()
    except socket.gaierror:
        return
    except socket.timeout:
        return
    except http.client.BadStatusLine:
        return
    except ConnectionResetError:
        return
    except OSError:
        return
    except RemoteDisconnected:
        return
    t0 = time.time()
    val = r.getheader("Date")
    t1 = time.time()
    if val:
        date = email.utils.parsedate_to_datetime(val)
        qduration = t1-t0
        return WebTime(qhost=host,qipaddr=ipaddr,qtime=t0+qduration/2,qduration=qduration,
                       rdate=val,rcode=r.code,delta=date.timestamp()-t)
    else:
        print("No date for {} {}".format(host,ipaddr))
        print(r.getheaders())


def webtime(host):
    import time
    import http
    from http import client
    import email
    import datetime
    import socket
    import sys

    prefixes = ["","","","www.","www.","www.","www1.","www2.","www3."]
    prefixes = [""]

    for prefix in prefixes:
        qhost = prefix+host
        try:
            if args.debug: print("DEBUG qhost={}".format(qhost))
            a = socket.gethostbyname_ex(qhost)
            ipaddrs = a[2]
            if args.debug: print("DEBUG   qhost={} ipaddrs={}".format(qhost,ipaddrs))
        except socket.gaierror:
            print("No address for ",qhost)
            return
        for ipaddr in ipaddrs:
            for i in range(3):
                w = webtime_ip(qhost, ipaddr)
                if args.debug: print("DEBUG   qhost={} ipaddr={:15} w={}".format(qhost,ipaddr,w))
                if not w or w.delta < MIN_TIME:
                    break
                yield w

def queryhost(host):
    import os
    for wt in webtime(host):
        print(wt.delta,MIN_TIME)
        if wt.delta > MIN_TIME:
            print("{:30} {:20} {:30} {}".format(wt.qhost,wt.qipaddr,wt.ptime(),wt.rdate))



if __name__=="__main__":
    import argparse
    from bs4 import BeautifulSoup, SoupStrainer
    import configparser
    import pymysql


    parser = argparse.ArgumentParser()
    parser.add_argument('--usg',action='store_true')
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--mysql",action="store_true",help="output to MySQL DB")
    parser.add_argument("--mongo",action="store_true",help="output to MongoDB")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    parser.add_argument("--threads","-j",type=int,default=1)
    parser.add_argument("--count",type=int,default=10000,help="The number of domains to count")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config["mysql"] = {"host":"localhost",
                       "user":"user",
                       "passwd":"",
                       "port":3306,
                       "db":"timedb"}
    config.read(args.config)


    if args.mysql:
        mysql = config["mysql"]
        try:
            conn = pymysql.connect(host=mysql["host"],port=int(mysql["port"]),user=mysql["user"],
                                   passwd=mysql['passwd'],db=mysql['db'])
        except pymysql.err.OperationalError as e:
            print("Cannot connect to mysqld. host={} user={} passwd={} port={} db={}".format(
                mysql['host'],mysql['user'],mysql['passwd'],mysql['port'],mysql['db']))
            raise e
            exit(1)

    lookups = 0
    domains = []

    #
    # Get the list of URLs to check
    #
    if args.usg:
        import urllib, urllib.request
        page = urllib.request.urlopen("http://usgv6-deploymon.antd.nist.gov/cgi-bin/generate-gov.v4").read()
        for link in BeautifulSoup(page, "lxml", parse_only=SoupStrainer('a')):
            try:
                import urllib
                o = urllib.parse.urlparse(link.attrs['href'])
                domains.append(o.netloc)
            except AttributeError:
                pass

    if not domains:
        for line in csv.reader(open("top-1m.csv"),delimiter=','):
            domains.append(line[1])
            if len(domains)>args.count:
                break

    # do the study

    start = time.time()
    if args.threads==1:
        for u in domains: queryhost(u)
    else:
        from multiprocessing import Pool
        pool = Pool(MP)
        results = pool.map(queryhost, domains)
    time_end = time.time()
    print("Total lookups: {}  lookups/sec: {}".format(count,count/(time_end-time_start)))
    

        
