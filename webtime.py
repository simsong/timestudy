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

MIN_TIME = 3.0                          # Don't record more off than this
CONFIG_INI = "config.ini"
DEFAULT_RETRY_COUNT = 3                 # how many times to retry a query
DEFAULT_TIMEOUT = 5                     # default timeout, in seconds
ALWAYS_RECORD_DOMAINS = set(['time.gov','time.nist.gov','ntp1.glb.nist.gov'])

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
                 qduration=None,rdatetime=None,rcode=None,mintime=MIN_TIME):
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
        self.mintime    = mintime

    def __repr__(self):
        return "<WebTime qhost:{} qipaddr:{} qdatetime:{} offset_seconds:{}>".format(self.qhost,self.qipaddr,self.qdatetime,self.offset_seconds())

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
    def wrong_time(self):
        """Returns true if time is off by more than minimum time."""
        return math.fabs(self.offset_seconds()) > self.mintime
    def should_record(self):
        """Return True if we should record, which is if the time is from time.gov or if it is wrong"""
        return self.wrong_time() or (self.qhost.lower() in ALWAYS_RECORD_DOMAINS)

def WebTimeExp(*,domain=None,ipaddr=None,proto='http',retry=DEFAULT_RETRY_COUNT,timeout=DEFAULT_TIMEOUT):
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
        
        
def get_ip_addrs(hostname):
    """Get all of the IP addresses for a hostname"""
    import socket
    return set([i[4][0] for i in socket.getaddrinfo(hostname, 0)])

class QueryHostEngine:
    """This class implements is the web experiment engine. A collection of objects are meant to be called in a multiprocessing pool.
    Each object creates a connection to the SQL database. The queryhost(qhost) entry point performs a lookup for all IP addresses
    Associated with the host.  Currently we do not try to use t he prefixes, but we could.
    Key methods:
    .__init__(db,debug)         - Initializes. db is the parameters for the database connection, but it doesn't connect until needed.
    .webtime(qhost,cursor=None) - get the webtime for every IP address for qhost; cursor is the MySQL cursor.
    .queryhost(qhost)           - main entry point. Run the experiment on host qhost, all IP addresses
    """
    def __init__(self,db,debug=False):
        """Create the object.
        @param db - a proxied database connection
        @param debug - if we are debugging
        """
        self.db        = db
        self.debug     = debug

    def queryhost(self,qhost):
        """
        Given the domain, get the IP addresses and query each one. 
        Updates the dated table.
        Return a WebTime object for each IP address.
        """
        import time
        import datetime

        if self.debug: print("DEBUG PID{} webtime({})".format(os.getpid(),qhost))

        # Record the times when we start querying the host
        qdatetime = datetime.datetime.fromtimestamp(time.time(),pytz.utc)
        qtime = qdatetime.time().isoformat()
        qdate = qdatetime.date().isoformat()

        # Update the dates for this host
        # 
        self.db.execute("insert ignore into dated (host,ipaddr,qdate,qfirst) values (%s,'',%s,%s)",
                           (qhost,qdate,qtime))
        host_id = self.db.select1("select id from dated where host=%s and ipaddr='' and qdate=%s",
                           (qhost,qdate))
        if not host_id:
            raise RuntimeError("Could not create host_id for host={} qdate={}".format(host,qdate))

        # Update the query count for the hostname
        self.db.execute("update dated set qlast=%s,qcount=qcount+1 where id=%s",(qtime,host_id))
        self.db.execute("update hosts set qdatetime=now() where host=%s",(qhost,))

        # Try to get the IPaddresses for the host
        try:
            ipaddrs = get_ip_addrs(qhost)
            if self.debug: print("DEBUG PID{}  qhost={} ipaddrs={}".format(os.getpid(),qhost,ipaddrs))
        except socket.gaierror:
            self.db.execute("update dated set qlast=%s,ecount=ecount+1 where id=%s",(qtime,host_id))
            if self.debug: print("ERROR socket.aierror {} ".format(qhost))
            return
        except socket.herror:
            self.db.mysql_execute("update dated set qlast=%s,ecount=ecount+1 where id=%s",(qtime,host_id))
            if self.debug: print("ERROR socket.herror {}".format(qhost))
            return

        # Are we supposed to record all of the responses for this host?
        try:
            record_all = self.db.select1("select recordall from hosts where host=%s",(qhost))[0]
        except TypeError:
            record_all = 0

        # Check each IP address for this host. Yield a wt object for each that is found
        for ipaddr in set(ipaddrs): # do each one once
            # Query the IP address
            wt = WebTimeExp(domain=qhost,ipaddr=ipaddr)
            if self.debug: 
                print("DEBUG   qhost={} ipaddr={:39} wt={}".format(qhost,ipaddr,wt))
            if not wt:
                continue
            # Note that we are going to query this IP address (again)
            isv6 = 1 if ":" in ipaddr else 0
            self.db.execute("insert ignore into dated (host,ipaddr,isv6,qdate,qfirst) values (%s,%s,%s,%s,%s)",
                               (wt.qhost,wt.qipaddr,isv6,wt.qdate(),wt.qtime()))
            ip_id = self.db.select1("select id from dated where host=%s and ipaddr=%s and qdate=%s",
                               (wt.qhost,wt.qipaddr,wt.qdate()))[0]
            self.db.execute("update dated set qlast=%s,qcount=qcount+1 where id=%s",(wt.qtime(),ip_id))
            if wt.wrong_time():
                # We got a response and it's the wrong time
                self.mysql_execute("update dated set wtcount=wtcount+1 where id=%s",(ip_id))
            if wt.should_record() or record_all:
                if args.verbose: 
                    print("{:35} {:20} {:30} {}".format(wt.qhost,wt.qipaddr,wt.pdiff(),wt.rdatetime))
                self.db.execute("insert ignore into times (host,ipaddr,isv6,qdatetime,qduration,rdatetime,offset) "+
                           "values (%s,%s,%s,%s,%s,%s,timestampdiff(second,%s,%s))",
                           (wt.qhost,wt.qipaddr,wt.qdatetime_iso(),
                            wt.qduration,wt.rdatetime_iso(),
                            wt.qdatetime_iso(),wt.rdatetime_iso()))
                self.db.commit()

def get_hosts(config):
    """Return the list of hosts specified by the 'sources' option in the [hosts] section of the config file. """
    (source_file,source_function) = config['hosts']['source'].split('.')
    module = __import__(source_file)
    func = getattr(module,source_function)
    return func()

if __name__=="__main__":
    import argparse
    import configparser
    import sys

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    parser.add_argument("--threads","-j",type=int,default=8,help="Number of threads")
    parser.add_argument("--verbose",action="store_true",help="output to STDOUT")
    parser.add_argument("--retry",type=int,default=2,help="Times to retry each web server")
    parser.add_argument("--mintime",type=float,default=MIN_TIME,help="Don't record times shorter than this.")
    parser.add_argument("--timeout",type=float,default=3,help="HTTP connect timeout")
    parser.add_argument("--limit",type=int,help="Limit to LIMIT oldest hosts",default=100000)

    args = parser.parse_args()
    config = db.get_mysql_config(args.config)       # prep it with default MySQL parameters

    # Make sure MySQL works. We do this here so that we don't report
    # that we can't connect to MySQL after the loop starts.  We cache
    # the results in w to avoid reundent connections to the MySQL
    # server.

    dbcon = db.mysql(config)
    ver = dbcon.mysql_version()
    if args.debug:
        print("MySQL Version {}".format(ver))
    # Upgrade the schema if necessary
    dbcon.upgrade_schema()

    # Get the hosts
    hosts = get_hosts(config)

    #TODO: GET THE URLS TO CHECK

    #
    # Get the list of URLs to check
    #
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

