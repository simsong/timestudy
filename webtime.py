#https://support.alexa.com/hc/en-us/articles/200461990-Can-I-get-a-list-of-top-sites-from-an-API-
#http://s3.amazonaws.com/alexa-static/top-1m.csv.zip

import os
import csv
import time,datetime,pytz
import subprocess
import sys
import math
import db

mysql = db.get_mysql_driver()

MIN_TIME = 1.0                # Resolution of remote websites
CONFIG_INI = "config.ini"
DEFAULT_RETRY_COUNT = 3                 # how many times to retry a query
DEFAULT_TIMEOUT = 5                     # default timeout, in seconds

prefixes = ["","","","www.","www.","www.","www1.","www2.","www3."]

def ip2long(ip):
    import socket,struct
    """
    Convert an IP string to long
    """
    packedIP = socket.inet_aton(ip)
    return struct.unpack("!L", packedIP)[0]

def s_to_hms(secs):
    """Returns a second as an [sign]hour:min:sec string.
    Space for sign is always present"""
    def factor(secs,period):
        return (secs // period,secs % period)

    sign  = " "
    if secs < 0:
        sign = "-"
        secs = -secs
    (days,secs) = factor(secs, 24*60*60)
    (hours,secs) = factor(secs, 60*60)
    (mins, secs) = factor(secs, 60)

    ret = sign
    if days:
        ret += "{}d ".format(days)
    ret += "{:02.0f}:{:02.0f}:{:02.0f}".format(hours,mins,secs)
    return ret


class WebTime():
    """Webtime class. Represents a query to a remote web server and the response.
    @param qdatetime - a datetime object when the query was made
    @param rdatetime - the datetime returned by the remote system.
    """
    def __init__(self,qhost=None,qipaddr=None,qdatetime=None,
                 qduration=None,rdatetime=None,rcode=None):
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

        # Make sure that datetimes are aware

    def offset(self):
        try:
            if self.qdatetime > self.rdatetime:
                return self.qdatetime - self.rdatetime
            else:
                return self.rdatetime - self.qdatetime
        except TypeError as e:
            print("Bad wt: {}".format(self))
            raise e

    def offset_seconds(self):
        return self.offset().total_seconds()

    def qdatetime_iso(self):
        return self.qdatetime.isoformat().replace("+00:00","")

    def rdatetime_iso(self):
        return self.rdatetime.isoformat().replace("+00:00","")

    def pdiff(self):
        """Print the offset in an easy to read format"""
        return s_to_hms(self.offset_seconds())
    def qdate(self):
        return self.qdatetime.date().isoformat()
    def qtime(self):
        return self.qdatetime.time().isoformat()
    def __repr__(self):
        return "<WebTime {} {} {} {}>".format(self.qhost,self.qipaddr,self.qdatetime,self.rdatetime)
    def wrong_time(self):
        """Returns true if time is off by more than minimum time."""
        return math.fabs(self.offset_seconds()) > args.mintime if wt else None
    def should_record(self):
        """Return True if we should record, which is if the time is from time.gov or if it is wrong"""
        return ("time.gov" in self.qhost.lower()) or self.wrong_time(wt)

def WebTimeExp(domain,ipaddr,proto='http',retry=DEFAULT_RETRY_COUNT,timeout=DEFAULT_TIMEOUT):
    """Like WebTime, but performs the experiment and returns a WebTime object with the results"""
    """Find the webtime of a particular domain and IP address"""
    import requests,socket,email,sys
    url = "{}://{}/".format(proto,domain)
    for i in range(retry):
        s = requests.Session()
        try:
            t0 = time.time()
            r = s.head(url,timeout=timeout,allow_redirects=False)
            t1 = time.time()
        except RuntimeException as e:
            if self.debug: print("ERROR {} requests.RequestException {} {}".format(e,domain,ipaddr))
            continue
        val = r.headers["Date"]
        try:
            date = email.utils.parsedate_to_datetime(val)
        except TypeError:
            continue        # no date!
        except ValueError:
            f = open("error.log","a")
            f.write("{} now: {} host: {} ipaddr: {}  Date: {}".format(time.localtime(),time.time(),domain,ipaddr,date))
            f.close()
            continue
        qduration = t1-t0
        qdatetime = datetime.datetime.fromtimestamp(t0+qduration/2,pytz.utc)
        return WebTime(qhost=domain,qipaddr=ipaddr,qdatetime=qdatetime,qduration=qduration,
                       rdatetime=date,rcode=r.status_code)
    # Too many retries
    if self.debug: print("ERROR too many retries")
    return None
        
        
class WebLogger:
    """This class is the web logging engine. 
    Key methods:
    .mysql_connect() - reconnects if not connected. This should be moved to another class
    .mysql_execute(c,cmd,args) - execute a MySQL command. Why is cursor an arg and not an instance variable?
    .webtime_ip(domain,ipaddr) - get the time for domain,ipaddr. Not an external entry point.
    .webtime(qhost,cursor=None) - get the webtime for every IP address for qhost; cursor is the MySQL cursor.
    .queryhost(qhost)      - 
    """
    def __init__(self,db,debug=False):
        """Create the object.
        @param db - a proxied database connection
        @param debug - if we are debugging
        """
        self.db        = db
        self.debug     = debug

    def webtime_ip(self,domain,ipaddr):
        """Find the webtime of a particular domain and IP address"""
        import http,socket,email,sys
        RemoteDisconnected = http.client.BadStatusLine
        if sys.version>'3.5':
            RemoteDisconnected = http.client.RemoteDisconnected
        url = "http://{}/".format(domain)
        for i in range(args.retry):
            connection = http.client.HTTPConnection(ipaddr,80,timeout=args.timeout)
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
            val = r.getheader["Date"]
            try:
                date = email.utils.parsedate_to_datetime(val)
            except TypeError:
                continue        # no date!
            except ValueError:
                f = open("error.log","a")
                f.write("{} now: {} host: {} ipaddr: {}  Date: {}".format(time.localtime(),time.time(),domain,ipaddr,date))
                f.close()
            qduration = t1-t0
            qdatetime = datetime.datetime.fromtimestamp(t0+qduration/2,pytz.utc)
            return WebTime(qhost=domain,qipaddr=ipaddr,qdatetime=qdatetime,qduration=qduration,
                           rdatetime=date,rcode=r.code)
        # Too many retries
        if self.debug: print("ERROR too many retries")
        return None
        

    def webtime(self,qhost,cursor=None):
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

        # Update the dates for this host
        t0 = time.time()
        self.mysql_execute(cursor,"insert ignore into dated (host,ipaddr,qdate,qfirst) values (%s,'',%s,%s)",
                           (qhost,qdate,qtime))
        t1 = time.time()
        td = t1-t0
        self.mysql_execute(cursor,"select id from dated where host=%s and ipaddr='' and qdate=%s",
                           (qhost,qdate))
        host_id = c.fetchone()
        if host_id:
            # Update the query count for the hostname
            self.mysql_execute(cursor,"update dated set qlast=%s,qcount=qcount+1 where id=%s",(qtime,host_id))
        self.mysql_execute(c,"update hosts set qdatetime=now() where host=%s",(qhost,))

        try:
            if self.debug: print("DEBUG qhost={}".format(qhost))
            a = socket.getaddrinfo(qhost, 0)
            ipaddrs = [i[4][0] for i in a]
            if self.debug: print("DEBUG   qhost={} ipaddrs={}".format(qhost,ipaddrs))
        except socket.gaierror:
            if host_id: self.mysql_execute(cursor,"update dated set qlast=%s,ecount=ecount+1 where id=%s",(qtime,host_id))
            if self.debug: print("ERROR socket.aierror {} ".format(qhost))
            return
        except socket.herror:
            if host_id: self.mysql_execute(cursor,"update dated set qlast=%s,ecount=ecount+1 where id=%s",(qtime,host_id))
            if self.debug: print("ERROR socket.herror {}".format(qhost))
            return

        # Check each IP address for this host
        for ipaddr in set(ipaddrs): # do each one once
            # Query the IP address
            wt = self.webtime_ip(qhost, ipaddr)
            if self.debug: 
                print("DEBUG   qhost={} ipaddr={:39} wt={}".format(qhost,ipaddr,wt))
            if cursor and wt:
                # Note that we are going to query this IP address (again)
                isv6 = 1 if ":" in ipaddr else 0
                self.mysql_execute(cursor,"insert ignore into dated (host,ipaddr,isv6,qdate,qfirst) values (%s,%s,%s,%s,%s)",
                                   (wt.qhost,wt.qipaddr,isv6,wt.qdate(),wt.qtime()))
                self.mysql_execute(cursor,"select id from dated where host=%s and ipaddr=%s and qdate=%s",
                                   (wt.qhost,wt.qipaddr,wt.qdate()))
                ip_id = c.fetchone()[0]
                self.mysql_execute(cursor,"update dated set qlast=%s,qcount=qcount+1 where id=%s",(wt.qtime(),ip_id))
            if cursor and wt.wrong_time():
                # We got a response and it's the wrong time
                self.mysql_execute(cursor,"update dated set wtcount=wtcount+1 where id=%s",(ip_id))
            if wt:
                # We got a wrong time
                yield wt

    def queryhost(self,qhost):
        """Query the host and stores the bad time reads in the times database if they are off."""
        import os,math

        cursor = None
        conn = None
        if self.mysql_config:
            if args.mysql_max and self.mysql_execute_count > args.mysql_max:
                self.mysql_reconnect() 
            
            conn = self.mysql_connect(cache=True)
            cursor = conn.cursor()

        self.mysql_execute(c,"select recordall from hosts_v6test where host=%s",(qhost))
        record_all = c.fetchone()[0]

        for wt in self.webtime(qhost,cursor):
            # Note if the webtime is off.
            if webtime_record(wt) or record_all>0:
                if args.verbose: 
                    print("{:35} {:20} {:30} {}".format(wt.qhost,wt.qipaddr,wt.pdiff(),wt.rdatetime))
                self.mysql_execute(cursor,"insert ignore into times (host,ipaddr,isv6,qdatetime,qduration,rdatetime,offset) "+
                                   "values (%s,%s,%s,%s,%s,%s,timestampdiff(second,%s,%s))",
                                   (wt.qhost,wt.qipaddr,wt.qdatetime_iso(),
                                    wt.qduration,wt.rdatetime_iso(),
                                    wt.qdatetime_iso(),wt.rdatetime_iso()))
                if conn: conn.commit()


if __name__=="__main__":
    import argparse
    import configparser
    import sys

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--cron',action='store_true',help='Indicates that it was run from cronrunner')
    parser.add_argument('--config',help='specify config file')
    parser.add_argument('--usg',action='store_true',help="Only check USG websites")
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--mysql",action="store_true",help="write results to MySQL DB",default=True)
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    parser.add_argument("--threads","-j",type=int,default=8,help="Number of threads")
    parser.add_argument("--verbose",action="store_true",help="output to STDOUT")
    parser.add_argument("--retry",type=int,default=2,help="Times to retry each web server")
    parser.add_argument("--mintime",type=float,default=MIN_TIME,help="Don't record times shorter than this.")
    parser.add_argument("--timeout",type=float,default=3,help="HTTP connect timeout")
    parser.add_argument("--host",help="Specify a host for a specific, one-time check")
    parser.add_argument("--limit",type=int,help="Limit to LIMIT oldest hosts",default=100000)

    args = parser.parse_args()

    config = db.get_mysql_config(args.config)       # prep it with default MySQL parameters

    # Make sure MySQL works. We do this here so that we don't report
    # that we can't connect to MySQL after the loop starts.  We cache
    # the results in w to avoid reundent connections to the MySQL
    # server.

    w = WebLogger(args.debug)
    if args.mysql:
        dbcon = db.mysql(config)
        conn = dbcon.mysql_connect(cache=False)       # test it out
        c = conn.cursor()
        if args.debug: print("MySQL Connected")

    #TODO: GET THE URLS TO CHECK

    #
    # Get the list of URLs to check
    #
    #usgflag = 1 if args.usg else 0
    usgflag = 1
    c.execute("select host from hosts where usg=%s order by qdatetime limit %s",(usgflag,args.limit))
    hosts = [row[0] for row in c.fetchall()]
    print("Total Hosts: {}".format(len(hosts)))

    from multiprocessing import Pool
    pool  = Pool(args.threads)

    start_rows = {}

    time_start = time.time()

    # Query the costs, either locally or in the threads
    if args.threads==1:
        [w.queryhost(u) for u in hosts]
    else:
        pool.map(w.queryhost, hosts)
    time_end = time.time()
    dcount = len(hosts)
    print("Total lookups: {:,}  Total time: {}  Lookups/sec: {:.2f}"\
          .format(dcount,s_to_hms(time_end-time_start),dcount/(time_end-time_start)))
    if args.mysql: mysql_stats(c)

