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

MIN_TIME = 1.0                # Resolution of remote websites
CONFIG_INI = "config.ini"

mysql_schema = """
"""

prefixes = ["","","","www.","www.","www.","www1.","www2.","www3."]

def get_config(args):
    import configparser
    config = configparser.ConfigParser()
    config["mysql"] = {"host":"localhost",
                       "user":"user",
                       "passwd":"",
                       "port":3306,
                       "db":"timedb",
                       "mysqldump":"mysqldump" }
    config.read(args.config)
    return config


def ip2long(ip):
    import socket,struct
    """
    Convert an IP string to long
    """
    packedIP = socket.inet_aton(ip)
    return struct.unpack("!L", packedIP)[0]


class WebTime():
    """Webtime class. qdatetime is a datetime object when the query was made, rdatetime is the datetime returned by the remote system."""
    def __init__(self,qhost=None,qipaddr=None,qdatetime=None,qduration=None,rdatetime=None,rcode=None,dateline=None):
        def fixtime(dt):
            try:
                return dt.astimezone(pytz.utc)
            except ValueError:
                return dt.replace(tzinfo=pytz.utc)
        self.qhost      = qhost
        self.qipaddr    = qipaddr
        self.qdatetime  = fixtime(qdatetime)
        self.qduration  = qduration
        self.rdatetime  = fixtime(rdatetime)
        self.rcode      = rcode
        self.dateline   = dateline

        # Make sure that datetimes are aware

    def delta(self):
        try:
            return self.qdatetime - self.rdatetime
        except TypeError as e:
            print("Bad wt: {}".format(self))
            raise e

    def delta_seconds(self):
        return self.delta().total_seconds()

    def qdatetime_iso(self):
        return self.qdatetime.isoformat().replace("+00:00","")

    def rdatetime_iso(self):
        return self.rdatetime.isoformat().replace("+00:00","")

    def pdiff(self):
        """Print the delta in an easy to read format"""
        sign  = " "
        delta = self.delta_seconds()
        if delta < 0:
            sign = "-"
            delta = -delta
        sec  = int(delta % 60)
        min  = int((delta/60) % 60)
        hour = int(delta / 3600)
        return "{:1}{:02}:{:02}:{:02}".format(sign,hour,min,sec)
    def qdate(self):
        return self.qdatetime.date().isoformat()
    def qtime(self):
        return self.qdatetime.time().isoformat()
    def __repr__(self):
        return "<WebTime {} {} {} {}>".format(self.qhost,self.qipaddr,self.qdatetime,self.rdatetime)

#
# Do we record?
#
def webtime_wrong_time(wt):
    return math.fabs(wt.delta_seconds()) > args.mintime if wt else None

def webtime_record(wt):
    if "time" in wt.qhost.lower():
        return True
    return webtime_wrong_time(wt)

def usg_domains():
    from bs4 import BeautifulSoup, SoupStrainer
    domains = set()
    import urllib, urllib.request
    page = urllib.request.urlopen("http://usgv6-deploymon.antd.nist.gov/cgi-bin/generate-gov.v4").read()
    for link in BeautifulSoup(page, "lxml", parse_only=SoupStrainer('a')):
        try:
            import urllib
            o = urllib.parse.urlparse(link.attrs['href'])
            if o.netloc: domains.add(o.netloc)
        except AttributeError:
            pass
    return domains
    

class WebLogger:
    def __init__(self,debug=False):
        self.mysql_config = None
        self.connected = None
        self.debug     = debug

    def mysql_connect(self,cache=False):
        if self.connected:
            return self.connected
        mc = self.mysql_config
        try:
            if self.debug: print("Connected in PID {}".format(os.getpid()))
            conn = pymysql.connect(host=mc["host"],port=int(mc["port"]),user=mc["user"],
                                   passwd=mc['passwd'],db=mc['db'])
            #conn = MySQLdb.connect(host=mc["host"],port=int(mc["port"]),user=mc["user"],
            #                       passwd=mc['passwd'],db=mc['db'])
            conn.cursor().execute("set innodb_lock_wait_timeout=20")
            conn.cursor().execute("SET tx_isolation='READ-COMMITTED'")
            conn.cursor().execute("SET time_zone = 'UTC'")
            self.mysql_execute_count = 0
            if cache:
                self.connected = conn
            return conn
        except pymysql.err.OperationalError as e:
            print("Cannot connect to mysqld. host={} user={} passwd={} port={} db={}".format(
                mc['host'],mc['user'],mc['passwd'],mc['port'],mc['db']))
            raise e
        
    def mysql_reconnect(self):
        if self.connected:
            self.connected.close() # close the current connection
            self.connected = None  # delete the object
            self.mysql_connect(cache=True)

    def mysql_execute(self,c,cmd,args):
        if not c: return        # no MySQL connection
        try:
            c.execute(cmd,args)
            self.mysql_execute_count += 1
        except pymysql.err.InternalError as e:
            print("ERROR: pymysql.err.InternalError: {}".format(cmd % args))
            self.mysql_reconnect()
            
        except pymysql.err.ProgrammingError as e:
            print("ERROR: pymysql.err.ProgrammingError: {}".format(cmd % args))
            self.mysql_reconnect()
            
        except _mysql_exceptions.OperationalError as e:
            print("Error: _mysql_exceptions.OperationalError: {}".format(cmd % args))
            print(repr(e))
            self.mysql_reconnect()

        except Exception as e:
            print("ERROR: {}:\n {}".format(repr(e),cmd % args))
            self.mysql_reconnect()

    def webtime_ip(self,domain,ipaddr):
        """Find the webtime of a particular domain and IP address"""
        import http,socket,email,sys
        RemoteDisconnected = http.client.BadStatusLine
        if sys.version>'3.5':
            RemoteDisconnected = http.client.RemoteDisconnected
        url = "http://{}/".format(domain)
        for i in range(args.retry):
            connection = http.client.HTTPConnection(ipaddr,timeout=args.timeout)
            try:
                connection.request("HEAD",url)
                t0 = time.time()
                r = connection.getresponse()
                t1 = time.time()
            except socket.gaierror:
                if self.debug: print("ERROR socket.gaierror {} {}".format(domain,ipaddr))
                continue
            except socket.timeout:
                if self.debug: print("ERROR socket.timeout {} {}".format(domain,ipaddr))
                continue
            except http.client.BadStatusLine:
                if self.debug: print("ERROR http.client.BadStatusLine {} {}".format(domain,ipaddr))
                continue
            except ConnectionResetError:
                if self.debug: print("ERROR ConnectionResetError {} {}".format(domain,ipaddr))
                continue
            except OSError:
                continue
            except RemoteDisconnected:
                continue
            except http.client.HTTPException:
                continue        # typically "got more than 100 headers"
            val = r.getheader("Date")
            try:
                date = email.utils.parsedate_to_datetime(val)
            except TypeError:
                continue        # no date!
            qduration = t1-t0
            qdatetime = datetime.datetime.fromtimestamp(t0+qduration/2,pytz.utc)
            return WebTime(qhost=domain,qipaddr=ipaddr,qdatetime=qdatetime,qduration=qduration,
                           rdatetime=date,rcode=r.code,dateline=date)
        # Too many retries
        if self.debug: print("ERROR too many retries")
        return None
        

    def webtime(self,qhost,c):
        """
        Given the domain, get the IP addresses and query each one. 
        Updates the dated table.
        Return the web time for each IP address.
        """
        import time
        import http
        from http import client
        import email
        import datetime
        import socket
        import sys

        # Indicate that we are querying this host today
        tq = datetime.datetime.fromtimestamp(time.time(),pytz.utc)
        qtime = tq.time().isoformat()
        qdate = tq.date().isoformat()

        if c:
            t0 = time.time()
            self.mysql_execute(c,"insert ignore into dated (host,ipaddr,qdate,qfirst) values (%s,'',%s,%s)",
                               (qhost,qdate,qtime))
            t1 = time.time()
            td = t1-t0
            self.mysql_execute(c,"select id from dated where host=%s and ipaddr='' and qdate=%s",
                               (qhost,qdate))
            host_id = c.fetchone()
            if host_id:
                # Update the query count for the hostname
                self.mysql_execute(c,"update dated set qlast=%s,qcount=qcount+1 where id=%s",(qtime,host_id))

        try:
            if self.debug: print("DEBUG qhost={}".format(qhost))
            a = socket.gethostbyname_ex(qhost)
            ipaddrs = a[2]
            if self.debug: print("DEBUG   qhost={} ipaddrs={}".format(qhost,ipaddrs))
        except socket.gaierror:
            if host_id: self.mysql_execute(c,"update dated set qlast=%s,ecount=ecount+1 where id=%s",(qtime,host_id))
            if self.debug: print("ERROR socket.aierror {} ".format(qhost))
            return
        except socket.herror:
            if host_id: self.mysql_execute(c,"update dated set qlast=%s,ecount=ecount+1 where id=%s",(qtime,host_id))
            if self.debug: print("ERROR socket.herror {}".format(qhost))
            return
        # Try each IP address
        for ipaddr in set(ipaddrs): # do each one once
            # Query the IP address
            wt = self.webtime_ip(qhost, ipaddr)
            if self.debug: 
                print("DEBUG   qhost={} ipaddr={:15} wt={}".format(qhost,ipaddr,wt))
            if c and wt:
                # Note that we are going to query this IP address (again)
                self.mysql_execute(c,"insert ignore into dated (host,ipaddr,qdate,qfirst) values (%s,%s,%s,%s)",
                                   (wt.qhost,wt.qipaddr,wt.qdate(),wt.qtime()))
                self.mysql_execute(c,"select id from dated where host=%s and ipaddr=%s and qdate=%s",
                                   (wt.qhost,wt.qipaddr,wt.qdate()))
                ip_id = c.fetchone()[0]
                self.mysql_execute(c,"update dated set qlast=%s,qcount=qcount+1 where id=%s",(wt.qtime(),ip_id))
            if c and webtime_wrong_time(wt):
                # We got a response and it's the wrong time
                self.mysql_execute(c,"update dated set wtcount=wtcount+1 where id=%s",(ip_id))
            if wt:
                # We got a wrong time
                yield wt



    def queryhost(self,qhost):
        """Query the host and stores the bad time reads in the times database if they are off."""
        import os,math

        c = None
        conn = None
        if self.mysql_config:
            if args.mysql_max and self.mysql_execute_count > args.mysql_max:
                self.mysql_reconnect() 
            
            conn = self.mysql_connect(cache=True)
            c = conn.cursor()

        for wt in self.webtime(qhost,c):
            # Note if the webtime is off.
            if webtime_record(wt):
                if args.verbose: 
                    print("{:35} {:20} {:30} {}".format(wt.qhost,wt.qipaddr,wt.pdiff(),wt.rdatetime))
                self.mysql_execute(c,"insert into times (host,ipaddr,qdatetime,qduration,rdatetime,delta) "+
                                   "values (%s,%s,%s,%s,%s,timestampdiff(second,%s,%s))",
                                   (wt.qhost,wt.qipaddr,wt.qdatetime_iso(),
                                    wt.qduration,wt.rdatetime_iso(),
                                    wt.qdatetime_iso(),wt.rdatetime_iso()))
                if conn: conn.commit()


if __name__=="__main__":
    import argparse
    import configparser

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
    parser.add_argument("--timeout",type=float,default=3,help="HTTP connect timeout")
    parser.add_argument("--host",help="Specify a host")
    parser.add_argument("--repeat",type=int,help="Times to repeat experiment")
    parser.add_argument("--norepeat",action="store_true",help="Used internally to implement repeating")
    parser.add_argument("--mysql_max",type=int,default=0,help="Number of MySQL connections before reconnecting")
    parser.add_argument("--dumpschema",action="store_true")
    parser.add_argument("--createusg",action="store_true",help="Create USG table")

    args = parser.parse_args()
    config = get_config(args)

    if args.dumpschema:
        call([config['mysqldump'],'-h',config['host'],'-u',config['user'],'-p',config['passwd'],'-d',config['db']])
        exit(0)

    w = WebLogger(args.debug)

    # Make sure mySQL works
    if args.mysql:
        w.mysql_config = config["mysql"]
        conn = w.mysql_connect(cache=False)       # test it out
        if args.debug: print("MySQL Connected")

    if args.createusg:
        domains = usg_domains()
        c = conn.cursor()
        c.execute("delete from usg")
        for domain in domains:
            c.execute("insert into usg (host) values (%s)",(domain,))
        conn.commit()
        exit(0)

    # If we are repeating, run self recursively (remove repeat args)
    if args.repeat and not args.norepeat:
        for r in range(args.repeat):
            print("**************************************")
            print("**************** {:4} ****************".format(r))
            print("**************************************")
            print(time.asctime())
            subprocess.call([sys.executable] + sys.argv + ["--norepeat"])
        exit(0)

    lookups = 0
    domains = set()

    if args.host:
        domains.append(args.host)

    #
    # Get the list of URLs to check
    #
    if args.usg:
        domains = usg_domains()
        print("Total USG: {}".format(len(domains)))

    if not domains:
        # Read the top-1m.csv file if we are not using USG domains
        for line in csv.reader(open("top-1m.csv"),delimiter=','):
            domains.add(line[1])
            if len(domains) > args.count:
                break

    # do the study

    from multiprocessing import Pool
    pool  = Pool(args.threads)

    if args.debug: print("Total Domains: {}".format(len(domains)))

    if args.mysql:
        c = conn.cursor()
        start_rows = {}
        if args.debug: print(time.asctime())
        for table in ["times","dated"]:
            c.execute("select count(*) from "+table)
            start_rows[table] = c.fetchone()[0]
            print("Start Rows in {}: {}".format(table,start_rows[table]))
        c.execute("select max(id) from dated")
        max_id = c.fetchone()[0]
        conn.commit()
    time_start = time.time()

    # Query the costs, either locally or in the threads
    if args.threads==1:
        [w.queryhost(u) for u in domains]
    else:
        pool.map(w.queryhost, domains)
    time_end = time.time()
    dcount = len(domains)
    print("Total lookups: {:,}  Total time: {:.0f}  Lookups/sec: {:.2f}".format(
        dcount,time_end-time_start,dcount/(time_end-time_start)))
    if args.mysql:
        for table in ["times","dated"]:
            c.execute("select count(*) from "+table)
            ct = c.fetchone()[0]
            print("End rows in {}: {}  (+{})".format(table,ct,ct-start_rows[table]))
        if args.debug:
            print("New dated rows:")
            c.execute("select * from dated where id>%s",(max_id,))
            for row in c.fetchall():
                print(row)
