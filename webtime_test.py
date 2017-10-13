import py.test
from webtime import *

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

