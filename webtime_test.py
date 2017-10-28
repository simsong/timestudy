import py.test
from webtime import *
import db

GOOD_TIME = 'time.glb.nist.gov' # for a good time, call...
GOOD_TIME_IP = '132.163.4.22'
GOOD_TIME_CORRECT = 5           # our clock should be within this many seconds of the GOOD TIME

def test_s_to_hms():
    assert s_to_hms(0)==" 00:00:00"
    assert s_to_hms(10)==" 00:00:10"
    assert s_to_hms(70)==" 00:01:10"
    assert s_to_hms(3600)==" 01:00:00"
    assert s_to_hms(3615)==" 01:00:15"
    

def test_get_cname():
    assert get_cname("nosuchhost")==None
    assert get_cname("www.media.mit.edu")=="www-prod.media.mit.edu."

def test_acast():
    # [centos@timedb ~]$ host acast.grc.nasa.gov
    # acast.grc.nasa.gov is an alias for web.grc.nasa.gov.
    # web.grc.nasa.gov has address 128.156.253.24
    # web.grc.nasa.gov has IPv6 address 2001:4d0:4310:1040::18
    # web.grc.nasa.gov mail is handled by 100 mx2.grc.nasa.gov.
    # web.grc.nasa.gov mail is handled by 100 mx1.grc.nasa.gov.
    # [centos@timedb ~]$
    host = 'acast.grc.nasa.gov';

def test_should_record_hostname():
    assert should_record_hostname("nosuchhost")==False
    assert should_record_hostname("time.nist.gov")==True

def test_WebTime():
    import email
    qdate = 'Fri, 13 Oct 2017 03:05:36 GMT'
    rdate = 'Fri, 13 Oct 2017 09:05:37 GMT' # far off
    w = WebTime(qhost='example',
                qipaddr='10.0.0.1',
                qdatetime=email.utils.parsedate_to_datetime(qdate),
                qduration=1.0, 
                rdatetime=email.utils.parsedate_to_datetime(qdate), # the same
                rcode=200)
    assert w.rcode==200
    assert w.qduration
    assert w.pdiff()==" 00:00:00"
    assert w.qdate()=="2017-10-13"
    assert w.qtime()=="03:05:36"
    assert w.should_record()==False
    
    w = WebTime(qhost='example2',
                qipaddr='10.0.0.1',
                qdatetime=email.utils.parsedate_to_datetime(qdate),
                qduration=1,  #
                rdatetime=email.utils.parsedate_to_datetime(rdate), # very far off
                rcode=200)
    assert w.should_record()==True

    # time.nist.gov should always be recorded
    w = WebTime(qhost='time.nist.gov',
                qipaddr='10.0.0.1',
                qdatetime=email.utils.parsedate_to_datetime(qdate),
                qduration=1.0,  # long enough to require alerting
                rdatetime=email.utils.parsedate_to_datetime(qdate),
                rcode=200)
    assert w.should_record()==True


def test_WebTimeExp():
    w = WebTimeExp(domain=GOOD_TIME,ipaddr=GOOD_TIME_IP,protocol='http',config=db.get_mysql_config("config.ini"))
    assert w.offset() < datetime.timedelta(seconds=GOOD_TIME_CORRECT)       # we should be off by less than 5 seconds

def test_WebTimeExp_redirect():
    w = WebTimeExp(domain='nist.gov',protocol='https',ipaddr='50.17.216.216',config=db.get_mysql_config("config.ini"))
    assert w.rcode in [301,303]
    assert w.redirect=='https://www.nist.gov/'

def test_get_ip_addrs():
    addrs = get_ip_addrs("google-public-dns-a.google.com")
    assert "8.8.8.8" in addrs

def test_QueryHostEngine():
    import time,datetime
    config = db.get_mysql_config("config.ini")
    mdb    = db.mysql(config)
    qhe    = QueryHostEngine(config)
    assert(type(qhe.db) == type(mdb))
    assert(qhe.debug == False)

    # Enable debugging. It will print to stdout but only generate output if the test fails
    mdb.debug = 1
    qhe.debug = 1
    qhe.db.debug = 1

    # Make sure that host is in the database now
    # We do this by making sure that there is an entry in the database for 'today'
    # Because 'today' may change between the start and the end, we measure it twice,
    # and we only do the assert if the day hasn't changed
    day0 = datetime.datetime.fromtimestamp(time.time(),pytz.utc).date()

    # Run a query!
    qhost = GOOD_TIME
    qhe.queryhost(qhost)

    (id,ipaddr,qdate) = mdb.select1("select id,ipaddr,qdate from dated where host=%s order by id desc limit 1",(GOOD_TIME,))
    day1 = datetime.datetime.fromtimestamp(time.time(),pytz.utc).date()
    assert id > 0                 # make sure id is good
    assert ipaddr > ''            # 
    assert qdate in [day0,day1]   # the day must be when we started or when we stopped

    # Now make sure we got both a http and an https value
    (id,ipaddr,http) = mdb.select1("select id,ipaddr,https from dated where host=%s and https=0 order by id desc limit 1",(GOOD_TIME,))
    assert id > 0

    (id,ipaddr,http) = mdb.select1("select id,ipaddr,https from dated where host=%s and https=1 order by id desc limit 1",(GOOD_TIME,))
    assert id > 0

def test_QueryHostEngine_Redirect():
    import time,datetime
    config = db.get_mysql_config("config.ini")
    mdb    = db.mysql(config)
    qhe    = QueryHostEngine(config)

    # Enable debugging. It will print to stdout but only generate output if the test fails
    mdb.debug = 1
    qhe.debug = 1
    qhe.db.debug = 1

    # Time.gov always has its time recorded. So we will query time.gov and see if we get the redirect
    qhe.queryhost('time.gov')


SOME_HOSTS=['host{}'.format(i) for i in range(1,100)] # a lot of hosts
def some_hosts():
    return SOME_HOSTS

def test_get_hosts():
    import configparser
    config = configparser.ConfigParser()
    config.add_section('hosts')
    config.set('hosts','source','webtime_test.some_hosts')
    config.set('hosts','order','as_is')
    hosts = get_hosts(config)
    assert hosts==SOME_HOSTS

    # test random order
    config.set('hosts','order','random')
    rhosts = get_hosts(config)
    assert len(SOME_HOSTS) == len(rhosts)
    assert SOME_HOSTS != rhosts
    assert sorted(SOME_HOSTS) == sorted(rhosts)

    # test the one that's there
    hosts = get_hosts(db.get_mysql_config(CONFIG_INI))
    assert 100 < len(hosts) < 100000
