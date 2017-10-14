import py.test
from webtime import *

GOOD_TIME = 'time.glb.nist.gov' # for a good time, call...
GOOD_TIME_IP = '132.163.4.22'
GOOD_TIME_CORRECT = 5           # our clock should be within this many seconds of the GOOD TIME

def test_s_to_hms():
    assert s_to_hms(0)==" 00:00:00"
    assert s_to_hms(10)==" 00:00:10"
    assert s_to_hms(70)==" 00:01:10"
    assert s_to_hms(3600)==" 01:00:00"
    assert s_to_hms(3615)==" 01:00:15"
    

def test_WebTime():
    import email
    t1 = 'Fri, 13 Oct 2017 03:05:36 GMT'
    t2 = 'Fri, 13 Oct 2017 03:05:37 GMT'
    w = WebTime(qhost='example',
                qipaddr='10.0.0.1',
                qdatetime=email.utils.parsedate_to_datetime(t1),
                qduration=1.0,
                rdatetime=email.utils.parsedate_to_datetime(t2),
                rcode=200)
    assert w.rcode==200
    assert w.qduration
    assert w.pdiff()==" 00:00:01"
    assert w.qdate()=="2017-10-13"
    assert w.qtime()=="03:05:36"

def test_WebTimeExp():
    w = WebTimeExp(domain=GOOD_TIME,ipaddr=GOOD_TIME_IP)
    assert w.offset() < datetime.timedelta(seconds=GOOD_TIME_CORRECT)       # we should be off by less than 5 seconds


def test_get_ip_addrs():
    addrs = get_ip_addrs("google-public-dns-a.google.com")
    assert "8.8.8.8" in addrs

def test_WebTimeExperiment():
    import time,datetime
    import db
    config = db.get_mysql_config("config.ini")
    mdb    = db.mysql(config)
    mdb.upgrade_schema()
    w      = WebTimeExperiment(mdb)
    assert(w.db == mdb)
    assert(w.debug == False)

    qhost = GOOD_TIME

    w.queryhost(qhost)

    # Make sure that host is in the database now
    s = mdb.select1("select max(id),ipaddr,max(qdate) from dated where host=%s limit 1",(GOOD_TIME))
    assert s[2]==datetime.datetime.fromtimestamp(time.time(),pytz.utc).date()
