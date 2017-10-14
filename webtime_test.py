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
    # We do this by making sure that there is an entry in the database for 'today'
    # Because 'today' may change between the start and the end, we measure it twice,
    # and we only do the assert if the day hasn't changed
    day0 = datetime.datetime.fromtimestamp(time.time(),pytz.utc).date()
    s = mdb.select1("select max(id),ipaddr,max(qdate) from dated where host=%s limit 1",(GOOD_TIME))
    day1 = datetime.datetime.fromtimestamp(time.time(),pytz.utc).date()
    assert s[2] in [day0,day1]
    if day0==day1:
        assert s[2]==day0
