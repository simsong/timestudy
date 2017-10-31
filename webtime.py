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
import json

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
    (days,secs)  = factor(secs, 24*60*60)
    (hours,secs) = factor(secs, 60*60)
    (mins, secs) = factor(secs, 60)

    ret = sign
    if days:
        ret += "{}d ".format(days)
    ret += "{:02.0f}:{:02.0f}:{:02.0f}".format(hours,mins,secs)
    return ret

def should_record_hostname(host):
    return host.lower() in ALWAYS_RECORD_DOMAINS

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

def is_v6(ipaddr):
    """Returns 1 if addr is an ipv6 address, otherwise 0. We return 1/0 rather than True/False because it's used in an SQL query"""
    return 1 if ":" in ipaddr else 0

def is_https(protocol):
    """Returns 1 if protocol is https, otherwise 0. We return 1/0 rather than True/False because it's used in an SQL query"""
    return 1 if protocol=='https' else 0

class WebTime():
    """Webtime class. Represents a query to a remote web server and the response.
    @param qdatetime - a datetime object when the query was made
    @param rdatetime - the datetime returned by the remote system.
    """
    def __init__(self,qhost=None,qipaddr=None,cname=None,
                 qdatetime=None,qduration=None,protocol=None,rdatetime=None,headers=None,
                 rcode=None,mintime=MIN_TIME,redirect=None):
        def fixtime(dt):
            try:
                return dt.astimezone(pytz.utc)
            except ValueError:
                return dt.replace(tzinfo=pytz.utc)
        self.qhost      = qhost
        self.qipaddr    = qipaddr
        self.cname      = cname
        self.qdatetime  = fixtime(qdatetime)
        self.qduration  = qduration
        self.rdatetime  = fixtime(rdatetime)
        self.rcode      = rcode # response code
        self.mintime    = mintime
        self.protocol   = protocol
        self.redirect   = redirect
        self.headers    = headers

    def __repr__(self):
        return "<WebTime {}://{} ({}) ({}) qdatetime:{} offset_seconds:{}>".format(self.protocol,self.qhost,self.cname,self.qipaddr,self.qdatetime,self.offset_seconds())

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
        return self.wrong_time() or should_record_hostname(self.qhost)

def WebTimeExp(*,domain=None,ipaddr=None,cname=None,protocol=None,config=None):
    """Like WebTime, but performs the experiment and returns a WebTime object with the results"""
    """Find the webtime of a particular domain and IP address"""

    assert (domain!=None)
    assert (ipaddr!=None)
    assert (config!=None)
    assert (protocol!=None)

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
        try:
            from urllib.parse import urlparse
            redirect = urlparse(r.headers.get('Location')).hostname
        except Exception:
            redirect = None
        return WebTime(qhost=domain,qipaddr=ipaddr,cname=cname,
                       qdatetime=qdatetime,
                       qduration=qduration,
                       rdatetime=date,
                       protocol=protocol,
                       rcode=r.status_code,
                       headers=r.headers,
                       redirect = redirect)
    # Too many retries
    if self.debug:
        print("ERROR too many retries")
    return None
        
        
class QueryHostEngine:
    """This class implements is the web experiment engine. A collection of objects are meant to be called in a multiprocessing pool.
    Each object creates a connection to the SQL database. The queryhost(qhost) entry point performs a lookup for all IP addresses
    Associated with the host.  Currently we do not try to use t he prefixes, but we could.
    Key methods:
    .__init__(db,debug)         - Initializes. db is the parameters for the database connection, but it doesn't connect until needed.
    .webtime(qhost,cursor=None) - get the webtime for every IP address for qhost; cursor is the MySQL cursor.
    .queryhost(qhost,force_record=False) - main entry point. Run the experiment on host qhost, all IP addresses; if force, make sure we record
    """
    def __init__(self,config,debug=False,runid=None):
        """Create the object.
        @param db - a proxied database connection
        @param debug - if we are debugging
        """
        assert type(config)==configparser.ConfigParser
        self.config    = config
        self.db        = db.mysql( config)
        self.debug     = debug
        self.runid     = runid
        if debug:
            self.db.debug  = debug

    def queryhost_params(self,*,qhost,cname,ipaddr,seq,protocol,dated_id,record_all):
        """Perform a query of qhost; return the WebTime object if the experiment was successful."""

        # Update the query count for the hostname
        self.db.execute("UPDATE hosts SET qdatetime=now() WHERE host=%s",(qhost,))

        cmd = "UPDATE dated SET qlast=%s,qcount=qcount+1"
        wt = WebTimeExp(domain=qhost,ipaddr=ipaddr,cname=cname,protocol=protocol,config=self.config)
        if wt:
            qlast = wt.qtime()
            if wt.wrong_time():
                # We got a response and it's the wrong time
                cmd += ",wtcount=wtcount+1"
        if not wt:
            # Got an error. Increment the error count
            cmd += ",ecount=ecount+1 "
            qlast = datetime.datetime.now().time()

        cmd += " WHERE id=%s"
        self.db.execute(cmd, (qlast,dated_id))

        if wt and (wt.should_record() or record_all):
            # Record wrong time!
            cursor = self.db.execute("INSERT INTO times (run,host,cname,ipaddr,isv6,seq,https,qdatetime,qduration,rdatetime,offset,response,redirect) "+
                                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TIMESTAMPDIFF(SECOND,%s,%s),%s,%s)",
                                (self.runid,wt.qhost,cname,wt.qipaddr,is_v6(ipaddr),seq,is_https(protocol),wt.qdatetime_iso(),
                                 wt.qduration,wt.rdatetime_iso(),
                                 wt.qdatetime_iso(),wt.rdatetime_iso(),wt.rcode,wt.redirect))
            if cursor and cursor.rowcount==1:
                self.db.execute("INSERT INTO headers (timeid,headers) values (%s,%s)",
                                (cursor.lastrowid,json.dumps(dict(wt.headers))))
        self.db.commit()
        return wt
        
    def queryhost(self,qhost,force_record=False):
        """
        Given the domain, get the IP addresses and query each one. 
        Updates the dated table.
        If time should be recorded, update the times table.
        Return a list of WebTime objects for all successful queries.
        NOTE ON SQL: only the dated table is updated, so that is the only one that needs to be locked.
        """

        ret = []
        if self.debug:
            print("DEBUG PID{} webtime({})".format(os.getpid(),qhost))

        # Make sure we are connected to the database
        assert self.db.mysql_version() > '5'

        # Now we create two sets, one that we've queried, one that we need to query.
        # Each time we query a host, remove it from to_query and add it to queried.
        # Add a host to to_query() if we get a redirect.
        # We might get multiple redirects on each query, so we will keep a set.

        to_query = set([qhost]) # the hosts that we need to query
        queried  = set()        # the hosts that we did query

        while to_query:
            qhost = to_query.pop() # get another host to query
            if qhost in queried:   
                continue        # we've already queried this host
            queried.add(qhost)  # add this host to the list of hosts that we have queried

            # Record the times when we start querying the host
            qdatetime = datetime.datetime.fromtimestamp(time.time(),pytz.utc)
            qtime = qdatetime.time().isoformat()
            qdate = qdatetime.date().isoformat()

            # Make sure that this host is in the hosts table
            self.db.execute("INSERT IGNORE INTO hosts (host,qdatetime) VALUES (%s,now())", (qhost,))

            # Try to get the IPaddresses for the host
            cname = get_cname(qhost)
            try:
                # Get the ipaddresses for this host. DNS errors are recorded in dated as errors with ipaddr=error-code and https=NULL
                ipaddrs = get_ip_addrs(qhost)
                if self.debug: print("DEBUG PID{}  qhost={} ipaddrs={}".format(os.getpid(),qhost,ipaddrs))
            except socket.gaierror as e:
                self.db.execute("insert ignore into dated (host,ipaddr,qdate,qfirst) values (%s,%s,%s,%s)", (qhost,'aierror',qdate,qtime))
                self.db.execute("update dated set qlast=%s,ecount=ecount+1 where host=%s and ipaddr=%s and qdate=%s",(qtime,qhost,'aierror',qdate))
                self.db.commit()
                if self.debug: print("ERROR socket.aierror {} {}".format(qhost,str(e)))
                continue
            except socket.herror as e:
                self.db.execute("insert ignore into dated (host,ipaddr,qdate,qfirst) values (%s,%s,%s,%s)", (qhost,'herror',qdate,qtime))
                self.db.execute("update dated set qlast=%s,ecount=ecount+1 where host=%s and ipaddr=%s and qdate=%s",(qtime,qhost,herror,qdate))
                self.db.commit()
                if self.debug: print("ERROR socket.herror {} {}".format(qhost,str(e)))
                continue

            # Are we supposed to record all of the responses for this host?
            try:
                record_all = self.db.select1("SELECT recordall FROM hosts WHERE host=%s",(qhost,))[0]
            except TypeError:
                record_all = 0

            if force_record:
                record_all = True

            # Check each IP address for this host. Yield a wt object for each that is found
            for ipaddr in set(ipaddrs): # do each one once
                #
                # Query the IP address
                #
                for protocol in self.config.get('hosts','protocol').split(','):

                    # Make sure that this (host,ipaddr,protocol) combination is in dated
                    cursor = self.db.execute("INSERT IGNORE INTO dated (host,ipaddr,isv6,https,qdate,qfirst) "
                                             "VALUES (%s,%s,%s,%s,%s,%s)",
                                             (qhost,ipaddr,is_v6(ipaddr),is_https(protocol),qdate,qtime))
                    if cursor and cursor.rowcount==1:
                        dated_id = cursor.lastrowid
                    else:
                        # Get the id (we might be able to just read it)
                        dated_id = self.db.select1("select id from dated where host=%s and ipaddr=%s and https=%s and qdate=%s",
                                                   (qhost,ipaddr,is_https(protocol),qdate))[0]

                    # Now perform experiments, adding the redirects to to_query as necessary
                    for seq in range(self.config.getint('webtime','repeat',fallback=1)):
                        wt = self.queryhost_params(qhost=qhost,cname=cname,ipaddr=ipaddr,seq=seq,protocol=protocol,
                                                   dated_id=dated_id,record_all=record_all)
                        if wt and wt.redirect and (wt.redirect not in queried):
                            to_query.add(wt.redirect) # another to query
                        ret.append(wt)
        return ret

def query_interactive(config,hosts):
    """Query a remote system..."""
    if not args.db:
        config.set('mysql','null', 'True')
    print("GMT Time: {}".format(time.asctime(time.gmtime(time.time()))))
    qhe = QueryHostEngine( config, debug=args.debug)
    for host in hosts:
        print("> "+host)
        if ":" in host:
            (protocol,qhost,ipaddr) = host.split(":",2)
            print(qhe.queryhost_params(qhost=qhost,cname=None,ipaddr=ipaddr,seq=0,protocol='http',dated_id=None,record_all=False))
            continue
        for wt in qhe.queryhost(host):
            print(wt)
            if args.debug:
                for h in wt.headers:
                    print("    {}: {}".format(h,wt.headers[h]))

if __name__=="__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--verbose",action="store_true",help="Be more verbose")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    parser.add_argument("--timeout",type=float,default=3,help="HTTP connect timeout")
    parser.add_argument("--limit",type=int,help="Limit to LIMIT oldest hosts",default=100000)
    parser.add_argument("--db",action="store_true",help="When running interactive, write to the database")
    parser.add_argument("-j","--threads",type=int,help="Specify number of threads",default=0)
    parser.add_argument("hosts",nargs="+",help="Just query these hosts (or host:ipaddr) directly")

    args = parser.parse_args()
    config = db.get_mysql_config(args.config)       # prep it with default MySQL parameters

    if config.getint('mysql','debug'):
        args.debug = 1          # override

    if args.hosts:
        query_interactive(config,args.hosts)
        exit(0)
    
    # Make sure MySQL works. We do this here so that we don't report
    # that we can't connect to MySQL after the loop starts.  We cache
    # the results in w to avoid reundent connections to the MySQL
    # server.

    dbc = db.mysql(config)
    ver = dbc.mysql_version()
    if args.debug:
        print("MySQL Version {}".format(ver))

    runid = dbc.log("{} running".format(__file__))

    # Get the hosts
    hosts = get_hosts(config)

    # Create a QueryHostEngine. It will not connect to the SQL Database until the connection is needed.
    # If we run in a multiprocessing pool, each process will get its own connection
    qhe = QueryHostEngine( config, debug=args.debug, runid=runid )
    
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
        [qhe.queryhost(qhost) for u in hosts]
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

    dbc.log("run {} finished".format(runid))
