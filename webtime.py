#!/usr/bin/env python3
#https://support.alexa.com/hc/en-us/articles/200461990-Can-I-get-a-list-of-top-sites-from-an-API-
#http://s3.amazonaws.com/alexa-static/top-1m.csv.zip

import csv
import time

MIN_TIME = 3

def ip2long(ip):
    import socket,struct
    """
    Convert an IP string to long
    """
    packedIP = socket.inet_aton(ip)
    return struct.unpack("!L", packedIP)[0]


class WebTime():
    def __init__(self,qhost=None,qtime=None,delta=None,qipaddr=None,rdate=None,code=None):
        self.qhost = qhost
        self.qtime = qtime
        self.qipaddr = qipaddr
        self.rdate  = rdate
        self.delta = delta
        self.code  = code
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
    t = time.time()
    val = r.getheader("Date")
    if val:
        date = email.utils.parsedate_to_datetime(val)
        return WebTime(qhost=host,qtime=t,qipaddr=ipaddr,
                      rdate=val,delta=date.timestamp()-t,code=r.code)
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
    import dns.resolver
    import sys

    prefixes = ["","","","www.","www.","www.","www1.","www2.","www3."]
    prefixes = [""]

    for prefix in prefixes:
        qhost = prefix+host
        try:
            a = dns.resolver.query(qhost,"A")
        except dns.resolver.NoAnswer:
            continue
        for r in a:
            ipaddr = r.to_text()
            print(qhost,ipaddr)
            for i in range(3):
                w = webtime_ip(qhost, ipaddr)
                print(w)
                if not w or w.delta < MIN_TIME:
                    break
                yield w

def queryhost(host):
    for wt in webtime(host):
        print("{:4} {:30} {:20} {:30} {}".format(rank,wt.qhost,wt.qipaddr,wt.ptime(),wt.rdate))



if __name__=="__main__":
    #for i in range(10000):
    #    queryhost(45,"blogspot.com")
    import argparse
    from bs4 import BeautifulSoup, SoupStrainer


    parser = argparse.ArgumentParser()
    parser.add_argument('--usg',action='store_true')
    args = parser.parse_args()
    from multiprocessing import Pool

    count = 100
    start = time.time()
    lookups = 0
    domains = []

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
            if len(domains)>count:
                break
    print(domains)
    for u in domains: queryhost(u)
    exit(0)


    pool = Pool(15)
    results = pool.map(queryhost, domains)
    end = time.time()
    print("Total lookups: {}  lookups/sec: {}".format(count,count/(end-start)))
    

        
