#https://support.alexa.com/hc/en-us/articles/200461990-Can-I-get-a-list-of-top-sites-from-an-API-
#http://s3.amazonaws.com/alexa-static/top-1m.csv.zip

import os
import csv
import time,datetime,pytz
import subprocess
import sys
import math

# Find a MySQL driver..
mysql = None
try:
    import pymysql, pymysql.err
    mysql = pymysql
except ImportError:
    pass

try:
    if not mysql:
        import MySQLdb, _mysql_exceptions
        mysql = MySQLdb
except ImportError:
    pass


MIN_TIME = 1.0                # Resolution of remote websites
CONFIG_INI = "config.ini"

mysql_schema = """
"""

prefixes = ["","","","www.","www.","www.","www1.","www2.","www3."]

def get_config(args):
    import configparser
    config = configparser.ConfigParser()
    config["mysql"] = {"host":"",
                       "user":"",
                       "passwd":"",
                       "port":0,
                       "db":"",
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


def s_to_hms(secs):
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

#
# Do we record?
#
def webtime_wrong_time(wt):
    return math.fabs(wt.offset_seconds()) > args.mintime if wt else None

def webtime_record(wt):
    if "time.gov" in wt.qhost.lower(): # internal control
        return True
    return webtime_wrong_time(wt)

"""
def usg_hosts():
    from bs4 import BeautifulSoup, SoupStrainer
    hosts = set()
    import urllib, urllib.request
    page = urllib.request.urlopen("http://usgv6-deploymon.antd.nist.gov/cgi-bin/generate-gov.v4").read()
    for link in BeautifulSoup(page, "lxml", parse_only=SoupStrainer('a')):
        try:
            import urllib
            o = urllib.parse.urlparse(link.attrs['href'])
            if o.netloc: hosts.add(o.netloc)
        except AttributeError:
            pass
    return hosts
"""

def usg_hosts():
    import csv, requests
    url = "https://analytics.usa.gov/data/live/sites.csv"
    hosts = set()
    with requests.Session() as s:
        download = s.get(url)
        decoded = download.content.decode('utf-8')
        cr = csv.reader(decoded.splitlines())
        hostlist = list(cr)[1:]
        for host in hostlist:
            hosts.add(host[0])
    return hosts

    
def alexa_hosts():
    # Read the top-1m.csv file if we are not using USG domains
    hosts = set()
    for line in csv.reader(open("top-1m.csv"),delimiter=','):
        hosts.add(line[1])
    return hosts
    # do the study


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
            conn = mysql.connect(host=mc["host"],port=int(mc["port"]),user=mc["user"],
                                   passwd=mc['passwd'],db=mc['db'])
            conn.cursor().execute("set innodb_lock_wait_timeout=20")
            conn.cursor().execute("SET tx_isolation='READ-COMMITTED'")
            conn.cursor().execute("SET time_zone = '+00:00'")
            self.mysql_execute_count = 0
            if cache:
                self.connected = conn
            return conn
        except RuntimeError as e:
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
        #except pymysql.err.InternalError as e:
        #    print("ERROR: pymysql.err.InternalError: {}".format(cmd % args))
        #    self.mysql_reconnect()
        #    
        #except pymysql.err.ProgrammingError as e:
        #    print("ERROR: pymysql.err.ProgrammingError: {}".format(cmd % args))
        #    self.mysql_reconnect()
        #    
        #except _mysql_exceptions.OperationalError as e:
        #    print("Error: _mysql_exceptions.OperationalError: {}".format(cmd % args))
        #    print(repr(e))
        #    self.mysql_reconnect()

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
            val = r.getheader("Date")
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
            self.mysql_execute(c,"insert ignore into dated_v6test (host,ipaddr,qdate,qfirst) values (%s,'',%s,%s)",
                               (qhost,qdate,qtime))
            t1 = time.time()
            td = t1-t0
            self.mysql_execute(c,"select id from dated_v6test where host=%s and ipaddr='' and qdate=%s",
                               (qhost,qdate))
            host_id = c.fetchone()
            if host_id:
                # Update the query count for the hostname
                self.mysql_execute(c,"update dated_v6test set qlast=%s,qcount=qcount+1 where id=%s",(qtime,host_id))
            self.mysql_execute(c,"update hosts set qdatetime=now() where host=%s",(qhost,))
        try:
            if self.debug: print("DEBUG qhost={}".format(qhost))
            a = socket.getaddrinfo(qhost, 0)
            ipaddrs = [i[4][0] for i in a]
            if self.debug: print("DEBUG   qhost={} ipaddrs={}".format(qhost,ipaddrs))
        except socket.gaierror:
            if host_id: self.mysql_execute(c,"update dated_v6test set qlast=%s,ecount=ecount+1 where id=%s",(qtime,host_id))
            if self.debug: print("ERROR socket.aierror {} ".format(qhost))
            return
        except socket.herror:
            if host_id: self.mysql_execute(c,"update dated_v6test set qlast=%s,ecount=ecount+1 where id=%s",(qtime,host_id))
            if self.debug: print("ERROR socket.herror {}".format(qhost))
            return
        # Try each IP address
        for ipaddr in set(ipaddrs): # do each one once
            # Query the IP address
            wt = self.webtime_ip(qhost, ipaddr)
            if self.debug: 
                print("DEBUG   qhost={} ipaddr={:39} wt={}".format(qhost,ipaddr,wt))
            if c and wt:
                # Note that we are going to query this IP address (again)
                isv6 = 1 if ":" in ipaddr else 0
                self.mysql_execute(c,"insert ignore into dated_v6test (host,ipaddr,isv6,qdate,qfirst) values (%s,%s,%r,%s,%s)",
                                   (wt.qhost,wt.qipaddr,isv6,wt.qdate(),wt.qtime()))
                self.mysql_execute(c,"select id from dated_v6test where host=%s and ipaddr=%s and qdate=%s",
                                   (wt.qhost,wt.qipaddr,wt.qdate()))
                ip_id = c.fetchone()[0]
                self.mysql_execute(c,"update dated_v6test set qlast=%s,qcount=qcount+1 where id=%s",(wt.qtime(),ip_id))
            if c and webtime_wrong_time(wt):
                # We got a response and it's the wrong time
                self.mysql_execute(c,"update dated_v6test set wtcount=wtcount+1 where id=%s",(ip_id))
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
                isv6 = 1 if ":" in wt.qipaddr else 0
                self.mysql_execute(c,"insert ignore into times_v6test (host,ipaddr,isv6,qdatetime,qduration,rdatetime,offset) "+
                                   "values (%s,%s,%r,%s,%s,%s,timestampdiff(second,%s,%s))",
                                   (wt.qhost,wt.qipaddr,isv6,wt.qdatetime_iso(),
                                    wt.qduration,wt.rdatetime_iso(),
                                    wt.qdatetime_iso(),wt.rdatetime_iso()))
                if conn: conn.commit()


def load_hosts(c,hosts,flag):
    for host in hosts:
        c.execute("insert ignore into hosts (host,usg) values (%s,%s)",(host,flag))
    conn.commit()
    exit(0)

def mysql_stats(c):
    global max_id
    c = conn.cursor()
    if args.debug: 
        print(time.asctime())
    for table in ["times_v6test","dated_v6test"]:
        c.execute("select count(*) from "+table)
        p = c.fetchone()[0]
        if table not in start_rows:
            print("Start Rows in {}: {:,}".format(table,p))
        else:
            print("End Rows in {}: {:,} (delta{:,})".format(table,p,p-start_rows[table]))
        start_rows[table] = p

    c.execute("select max(id) from dated_v6test")
    max_id = c.fetchone()[0]
        
    if args.debug:
        print("New dated rows:")
        c.execute("select * from dated_v6test where id>%s",(max_id,))
        for row in c.fetchall():
            print(row)


if __name__=="__main__":
    import argparse
    import configparser

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--usg',action='store_true',help="Only check USG websites")
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--mysql",action="store_true",help="output to MySQL DB",default=True)
    #parser.add_argument("--mongo",action="store_true",help="output to MongoDB")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    parser.add_argument("--threads","-j",type=int,default=8,help="Number of threads")
    parser.add_argument("--verbose",action="store_true",help="output to STDOUT")
    parser.add_argument("--retry",type=int,default=2,help="Times to retry each web server")
    parser.add_argument("--mintime",type=float,default=MIN_TIME,help="Don't record times shorter than this.")
    parser.add_argument("--timeout",type=float,default=3,help="HTTP connect timeout")
    parser.add_argument("--host",help="Specify a host for a specific, one-time check")
    parser.add_argument("--repeat",type=int,default=0,help="Times to repeat experiment")
    parser.add_argument("--duration", type=int, default=0, help="Repeat experiment for number of hours")
    parser.add_argument("--norepeat",action="store_true",help="Used internally to implement repeating")
    parser.add_argument("--mysql_max",type=int,default=0,help="Number of MySQL transactions before reconnecting")
    parser.add_argument("--dumpschema",action="store_true")
    parser.add_argument("--loadusg",action="store_true",help="Load USG table")
    parser.add_argument("--loadalexa",action="store_true",help="Load Alexa table")
    parser.add_argument("--limit",type=int,help="Limit to LIMIT oldest hosts",default=100000)


    args = parser.parse_args()
    config = get_config(args)

    if args.dumpschema:
        mc = config["mysql"]
        cmd = ['mysqldump','-h',mc['host'],'-u',mc['user'],'-p' + mc['passwd'], '-d',mc['db']]
        print(cmd)
        subprocess.call(cmd)
        exit(0)

    w = WebLogger(args.debug)

    # Make sure mySQL works
    if args.mysql:
        w.mysql_config = config["mysql"]
        conn = w.mysql_connect(cache=False)       # test it out
        c = conn.cursor()
        if args.debug: print("MySQL Connected")

    if args.loadusg:   load_hosts(c,usg_hosts(),1)
    if args.loadalexa: load_hosts(c,alexa_hosts(),0)

    # If we are repeating, run self recursively (remove repeat args)
    if args.repeat and not args.norepeat and not args.duration:
        for r in range(args.repeat):
            print("**************************************")
            print("**************** {:4} ****************".format(r))
            print("**************************************")
            print(time.asctime())
            subprocess.call([sys.executable] + ["-W ignore"] + sys.argv + ["--norepeat"])
        exit(0)

    if args.duration and not args.norepeat and not args.repeat:
        starttime = time.time()
        rundur = args.duration*60*60
        count = 0
        avg_runtime = 0
        while (time.time()-starttime+avg_runtime+60 < rundur):
            runstart = time.time()
            count += 1
            print("**************************************")
            print("**************** {:4} ****************".format(count))
            print("**************************************")
            print(time.asctime())
            subprocess.call([sys.executable] + ["-W ignore"] + sys.argv + ["--norepeat"])
            runtime = time.time() - runstart
            avg_runtime = avg_runtime + ((runtime-avg_runtime)/count)
        exit(0)

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
    if args.mysql: mysql_stats(c)

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
