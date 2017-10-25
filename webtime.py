#https://support.alexa.com/hc/en-us/articles/200461990-Can-I-get-a-list-of-top-sites-from-an-API-
#http://s3.amazonaws.com/alexa-static/top-1m.csv.zip

import sys
if sys.version < '3':
    raise RuntimeError("Requires Python 3")

import os
import csv
import time,datetime,pytz
import subprocess
import math
import db
import configparser
import socket
import struct

MIN_TIME = 3.0                          # Don't record more off than this
CONFIG_INI = "config.ini"
DEFAULT_RETRY_COUNT = 3                 # how many times to retry a query
DEFAULT_TIMEOUT = 5                     # default timeout, in seconds
ALWAYS_RECORD_DOMAINS = set(['time.gov','time.nist.gov','time.glb.nist.gov','ntp1.glb.nist.gov'])
DEFAULT_THREADS=8

prefixes = ["","","","www.","www.","www.","www1.","www2.","www3."]

def ip2long(ip):
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

def WebTimeExp(*,domain=None,ipaddr=None,protocol='http',config=None):
    """Like WebTime, but performs the experiment and returns a WebTime object with the results"""
    """Find the webtime of a particular domain and IP address"""
    import requests,socket,email,sys
    url = "{}://{}/".format(protocol,domain)
    for i in range(config.getint('webtime','retry')):
        s = requests.Session()
        try:
            t0 = time.time()
            r = s.head(url,timeout=config.getint('webtime','timeout'),allow_redirects=False)
            t1 = time.time()
        except requests.exceptions.ConnectTimeout as e:
            return None
        except requests.exceptions.ConnectionError as e:
            return None
        except requests.exceptions.ReadTimeout as e:
            return None

        try:
            val = r.headers["Date"]
        except KeyError:
            # No date in header; we see these on redirects from the Big IP appliance
            # that is trying to force people to use https:
            return None
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
    return set([i[4][0] for i in socket.getaddrinfo(hostname, 0)])

def get_cname(hostname):
    """Return the CNAME for hostname, if it exists"""
    import dns.resolver
    try:
        for rdata in dns.resolver.query(hostname,'CNAME'):
            return str(rdata.target)
    except Exception as e:
        return None

class QueryHostEngine:
    """This class implements is the web experiment engine. A collection of objects are meant to be called in a multiprocessing pool.
    Each object creates a connection to the SQL database. The queryhost(qhost) entry point performs a lookup for all IP addresses
    Associated with the host.  Currently we do not try to use t he prefixes, but we could.
    Key methods:
    .__init__(db,debug)         - Initializes. db is the parameters for the database connection, but it doesn't connect until needed.
    .webtime(qhost,cursor=None) - get the webtime for every IP address for qhost; cursor is the MySQL cursor.
    .queryhost(qhost)           - main entry point. Run the experiment on host qhost, all IP addresses
    """
    def __init__(self,config,debug=False):
        """Create the object.
        @param db - a proxied database connection
        @param debug - if we are debugging
        """
        assert type(config)==configparser.ConfigParser
        self.config    = config
        self.db        = db.mysql( config)
        self.debug     = debug

    def queryhost_params(self,qhost,cname,ipaddr,protocol,record_all):
        isv6 = 1 if ":" in ipaddr else 0
        https = 1 if protocol=='https' else 0
        wt = WebTimeExp(domain=qhost,ipaddr=ipaddr,config=self.config)
        if not wt:
            return

        # Make sure that the host is in dated for the (host,ipaddr,qdate) combination.
        # That is the unique key; https is not considered
        self.db.execute("insert ignore into dated (host,ipaddr,isv6,qdate,qfirst) values (%s,%s,%s,%s,%s)",
                        (wt.qhost,wt.qipaddr,isv6,wt.qdate(),wt.qtime()))
        id = self.db.select1("select id from dated where host=%s and ipaddr=%s and qdate=%s ",
                             (wt.qhost,wt.qipaddr,wt.qdate()))[0]
        cmd = "update dated set qlast=%s,qcount=qcount+1"
        if wt.wrong_time():
            # We got a response and it's the wrong time
            cmd += ",wtcount=wtcount+1"
        cmd += " where id=%s"
        self.db.execute(cmd,(wt.qtime(),id))

        if wt.should_record() or record_all:
            self.db.execute("insert ignore into times (host,cname,ipaddr,isv6,https,qdatetime,qduration,rdatetime,offset) "+
                       "values (%s,%s,%s,%s,%s,%s,%s,%s,timestampdiff(second,%s,%s))",
                       (wt.qhost,cname,wt.qipaddr,isv6,https,wt.qdatetime_iso(),
                        wt.qduration,wt.rdatetime_iso(),
                        wt.qdatetime_iso(),wt.rdatetime_iso()))
        self.db.commit()
        

    def queryhost(self,qhost):
        """
        Given the domain, get the IP addresses and query each one. 
        Updates the dated table.
        If time should be recorded, update the times table.
        Return a WebTime object for each IP address.
        NOTE ON SQL: only the dated table is updated, so that is the only one that needs to be locked.
        """

        if self.debug:
            print("DEBUG PID{} webtime({})".format(os.getpid(),qhost))

        # Make sure we are connected to the database
        assert self.db.mysql_version() > '5'

        # Record the times when we start querying the host
        qdatetime = datetime.datetime.fromtimestamp(time.time(),pytz.utc)
        qtime = qdatetime.time().isoformat()
        qdate = qdatetime.date().isoformat()

        # Note: fields in dated that don't have ipaddr are for all ipaddrs
        self.db.execute("insert ignore into dated (host,ipaddr,qdate,qfirst) values (%s,%s,%s,%s)", (qhost,'',qdate,qtime))
        dated_id = self.db.select1("select id from dated where host=%s and ipaddr='' and qdate=%s", (qhost,qdate))[0]

        # Update the query count for the hostname
        self.db.execute("UPDATE dated SET qlast=%s,qcount=qcount+1 WHERE id=%s",(qtime,dated_id))
        self.db.execute("UPDATE hosts SET qdatetime=now() WHERE host=%s",(qhost,))

        # Make sure that this host is in the hosts table
        self.db.execute("insert ignore into hosts (host,qdatetime) values (%s,now())", (qhost,))

        # Try to get the IPaddresses for the host
        cname = get_cname(qhost)
        try:
            ipaddrs = get_ip_addrs(qhost)
            if self.debug: print("DEBUG PID{}  qhost={} ipaddrs={}".format(os.getpid(),qhost,ipaddrs))
        except socket.gaierror:
            self.db.execute("update dated set qlast=%s,ecount=ecount+1 where id=%s",(qtime,dated_id))
            self.db.commit()
            if self.debug: print("ERROR socket.aierror {} ".format(qhost))
            return
        except socket.herror:
            self.db.execute("update dated set qlast=%s,ecount=ecount+1 where id=%s",(qtime,dated_id))
            self.db.commit()
            if self.debug: print("ERROR socket.herror {}".format(qhost))
            return

        # Are we supposed to record all of the responses for this host?
        try:
            record_all = self.db.select1("select recordall from hosts where host=%s",(qhost,))[0]
        except TypeError:
            record_all = 0

        # Check each IP address for this host. Yield a wt object for each that is found
        for ipaddr in set(ipaddrs): # do each one once
            #
            # Query the IP address
            #
            for protocol in self.config.get('hosts','protocol').split(','):
                for repeat in range(self.config.getint('webtime','repeat',fallback=1)):
                    self.queryhost_params(qhost,cname,ipaddr,protocol,record_all)

def get_hosts(config):
    """Return the list of hosts specified by the 'sources' option in the [hosts] section of the config file. """
    (source_file,source_function) = config['hosts']['source'].split('.')
    source_function = source_function.replace("()","") # remove () if it was provided
    module = __import__(source_file)
    try:
        func = getattr(module,source_function)
    except AttributeError:
        raise RuntimeError("module '{}' does not have a function '{}'".format(source_file,source_function))
    order = config['hosts']['order']
    if order =='random':
        import random
        import copy
        ret = copy.copy(func())
        random.shuffle(ret)
        return ret
    elif order=='as_is':
        return func()
    else:
        raise RuntimeError("hosts:order '{}' must be random or as_is".format(order))

if __name__=="__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    parser.add_argument("--timeout",type=float,default=3,help="HTTP connect timeout")
    parser.add_argument("--limit",type=int,help="Limit to LIMIT oldest hosts",default=100000)
    parser.add_argument("-j","--threads",type=int,help="Specify number of threads",default=0)

    args = parser.parse_args()
    config = db.get_mysql_config(args.config)       # prep it with default MySQL parameters

    if config.getint('mysql','debug'):
        args.debug = 1          # override

    # Make sure MySQL works. We do this here so that we don't report
    # that we can't connect to MySQL after the loop starts.  We cache
    # the results in w to avoid reundent connections to the MySQL
    # server.

    dbc = db.mysql(config)
    ver = dbc.mysql_version()
    if args.debug:
        print("MySQL Version {}".format(ver))
    # Upgrade the schema if necessary
    dbc.upgrade_schema()

    # Get the hosts
    hosts = get_hosts(config)

    # Create a QueryHostEngine. It will not connect to the SQL Database until the connection is needed.
    # If we run in a multiprocessing pool, each process will get its own connection
    qhe = QueryHostEngine( config )
    
    # Start parallel execution
    time_start = time.time()

    # Determine how many entries in the database at start
    if args.debug:
        host_count = len(hosts)
        print("Total Hosts: {:,}".format(host_count))
        (qcount0,ecount0,wtcount0) = dbc.select1("select sum(qcount),sum(ecount),sum(wtcount) from dated")
        print("Initial stats:  queries: {:,}   errors: {:,}   wrong times: {:,}".format(qcount0,ecount0,wtcount0))

    # Query the costs, either locally or in the threads
    threads = config.getint('DEFAULT','threads',fallback=DEFAULT_THREADS)
    if args.threads:
        threads = args.threads
    if threads==1:
        [qhe.queryhost(u) for u in hosts]
    else:
        from multiprocessing import Pool
        pool = Pool(threads)
        pool.map(qhe.queryhost, hosts)
    time_end = time.time()
    time_total = time_end-time_start

    # Determine the ending stats
    if args.debug:
        (qcount1,ecount1,wtcount1) = dbc.select1("select sum(qcount),sum(ecount),sum(wtcount) from dated")
        print("Ending stats:  queries: {:,}   errors: {:,}   wrong times: {:,}".format(qcount1,ecount1,wtcount1))
        print("Total hosts: {:,}  Total time: {}  Hosts/sec: {:.2f}  Queries/sec: {:.2f}"\
              .format(host_count,s_to_hms(time_total),host_count/time_total,float(qcount1-qcount0)/time_total))

