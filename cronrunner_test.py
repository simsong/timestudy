import py.test
from cronrunner import *

def test_getlock():
    fd = getlock(__file__)
    try:
        fd2 = getlock(__file__)
        assert(False)           # whoops; second attempt should fail
    except RuntimeError as e:
        pass                    # I want to fail the second time

def test_logger_info():
    import os
    from subprocess import call,PIPE,DEVNULL
    msg = "log test PID{}".format(os.getpid())
    logger_info(msg)
    # Now make sure that it's there
    r = call(['grep',msg,'/var/log/messages'],stdout=DEVNULL,stderr=DEVNULL)
    assert(r==0)                # we found it if r==0
