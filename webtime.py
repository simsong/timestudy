#!/usr/bin/env python3
#https://support.alexa.com/hc/en-us/articles/200461990-Can-I-get-a-list-of-top-sites-from-an-API-
#http://s3.amazonaws.com/alexa-static/top-1m.csv.zip

import os
import csv
import time

MIN_TIME = 0.001
CONFIG_INI = "config.ini"

mysql_schema = """
create table times (id int not null auto_increment,host varchar(255),ipaddr varchar(15),qdatetime datetime,qduration float,rdatetime datetime,delta float,primary key (id));
create table dated (id int not null auto_increment,host varchar(255),ipaddr varchar(15),qdate date,qfirst time,qlast time,qcount int,primary key (id),unique key (host,ipaddr,qdate));
"""

def ip2long(ip):
    import socket,struct
    """
    Convert an IP string to long
    """
    packedIP = socket.inet_aton(ip)
    return struct.unpack("!L", packedIP)[0]


class WebTime():
    def __init__(self,qhost=None,qipaddr=None,qdatetime=None,qduration=None,rdatetime=None,rcode=None,delta=None):
        self.qhost = qhost
        self.qipaddr= qipaddr
        self.qdatetime  = qdatetime
        self.qduration = qduration
        self.rdatetime  = rdatetime
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
        return "<WebTime {} {} {}>".format(self.qhost,self.qdatetime,self.delta)

class WebLogger:
    def __init__(self):
        self.mysql_config = False
        self.connected = False

    def mysql_connect(self):
        mc = self.mysql_config
        try:
            return pymysql.connect(host=mc["host"],port=int(mc["port"]),user=mc["user"],
                                              passwd=mc['passwd'],db=mc['db'])
        except pymysql.err.OperationalError as e:
            print("Cannot connect to mysqld. host={} user={} passwd={} port={} db={}".format(
                mc['host'],mc['user'],mc['passwd'],mc['port'],mc['db']))
            raise e
        

    def webtime_ip(self,domain,ipaddr):
        import http,socket,email,sys
        """Find the webtime of a particular domain and IP address"""
        RemoteDisconnected = http.client.BadStatusLine
        if sys.version>'3.5':
            RemoteDisconnected = http.client.RemoteDisconnected
        connection = http.client.HTTPConnection(ipaddr,timeout=5)
        try:
            url = "http://{}/".format(domain)
            connection.request("HEAD",url)
            r = connection.getresponse()
        except socket.gaierror:
            if args.debug: print("ERROR socket.gaierror {} {}".format(domain,ipaddr))
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
            qdatetime = t0+qduration/2
            return WebTime(qhost=domain,qipaddr=ipaddr,qdatetime=qdatetime,qduration=qduration,
                           rdatetime=date,rcode=r.code,delta=date.timestamp()-qdatetime)
        # No date

    def webtime(self,domain):
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
            qhost = prefix+domain
            try:
                if args.debug: print("DEBUG qhost={}".format(qhost))
                a = socket.gethostbyname_ex(qhost)
                ipaddrs = a[2]
                if args.debug: print("DEBUG   qhost={} ipaddrs={}".format(qhost,ipaddrs))
            except socket.gaierror:
                print("ERROR socket.aierror {} ".format(qhost))
                return
            except socket.herror:
                print("ERROR socket.herror {}".format(qhost))
                return
            for ipaddr in ipaddrs:
                for i in range(args.retry):
                    w = self.webtime_ip(qhost, ipaddr)
                    if args.debug: print("DEBUG   qhost={} ipaddr={:15} w={}".format(qhost,ipaddr,w))
                    if w:
                        yield w
                        break


    def queryhost(self,host):
        """Query the host and store them in a database if they are interesting. Update the database to indicate when the host was surveyed"""
        import os,math
        if self.mysql_config and not self.connected:
            self.mysql_conn = self.mysql_connect()
            self.connected = True
            print("Connected in PID {}".format(os.getpid()))

        for wt in self.webtime(host):
            if math.fabs(wt.delta) > args.mintime:
                if args.verbose: 
                    print("{:30} {:20} {:30} {}".format(wt.qhost,wt.qipaddr,wt.ptime(),wt.rdatetime))
                if self.connected:
                    c = self.mysql_conn.cursor()
                    c.execute("insert into times (host,ipaddr,qdatetime,qduration,rdatetime,delta) values (%s,%s,from_unixtime(%s),%s,%s,%s)",
                              (wt.qhost,wt.qipaddr,wt.qdatetime,wt.qduration,wt.rdatetime,wt.delta))
                    # Update the dated table
                    c.execute("insert ignore into dated (host,ipaddr,qdate,qfirst,qcount) values (%s,%s,date(from_unixtime(%s)),time(from_unixtime(%s)),0)",
                              (wt.qhost,wt.qipaddr,wt.qdatetime,wt.qdatetime))
                    c.execute("select id from dated where host=%s and ipaddr=%s and qdate=date(from_unixtime(%s))",
                              (wt.qhost,wt.qipaddr,wt.qdatetime))
                    i = c.fetchone()
                    c.execute("update dated set qlast=time(from_unixtime(%s)),qcount=qcount+1 where id=%s",(wt.qdatetime,i))
                    self.mysql_conn.commit()




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
    parser.add_argument("--threads","-j",type=int,default=None)
    parser.add_argument("--count",type=int,default=10000,help="The number of domains to count")
    parser.add_argument("--verbose",action="store_true",help="output to STDOUT")
    parser.add_argument("--retry",type=int,default=2,help="Times to retry each web server")
    parser.add_argument("--mintime",type=float,default=MIN_TIME,help="Don't report times shorter than this.")
    parser.add_argument("--host",help="Specify a host")

    args = parser.parse_args()

    config = configparser.ConfigParser()
    config["mysql"] = {"host":"localhost",
                       "user":"user",
                       "passwd":"",
                       "port":3306,
                       "db":"timedb"}
    config.read(args.config)

    w = WebLogger()

    if args.mysql:
        w.mysql_config = config["mysql"]
        w.mysql_connect()       # test it out
        print("MySQL works")
    lookups = 0
    domains = []

    if args.host:
        domains.append(args.host)

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
                if o.netloc: domains.append(o.netloc)
            except AttributeError:
                pass

    if not domains:
        for line in csv.reader(open("top-1m.csv"),delimiter=','):
            domains.append(line[1])
            if len(domains)>args.count:
                break

    # do the study

    time_start = time.time()
    if args.threads==1:
        for u in domains: 
            w.queryhost(u)
    else:
        from multiprocessing import Pool
        pool = Pool(args.threads)
        results = pool.map(w.queryhost, domains)
    time_end = time.time()
    print("Total lookups: {}  lookups/sec: {}".format(args.count,args.count/(time_end-time_start)))
    

        
