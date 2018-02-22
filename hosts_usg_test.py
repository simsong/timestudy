import pytest

from hosts_usg import *

def test_url_to_hostname():
    assert url_to_hostname("http://www.nist.gov/") == 'www.nist.gov'
    assert url_to_hostname("http://www.nist.gov:99/") == 'www.nist.gov'
    assert url_to_hostname("https://www.nist.gov/") == 'www.nist.gov'

def test_pulse_cio_gov_anlaytics():
    ret = pulse_cio_gov_analytics()
    assert 1000 < len(ret) < 100000
    assert "cep.gov" in ret
    assert "cfa.gov" in ret

def test_pulse_cio_gov_https():
    ret = pulse_cio_gov_analytics()
    assert 1000 < len(ret) < 100000
    assert "login.gov" in ret

#def test_usg_from_nist():
#    ret = usg_from_nist()
#    assert type(ret)==list
#    assert 1000 < len(ret) < 1e6
#    assert "www.nist.gov" in ret

def test_usg_from_cio():
    ret = usg_from_cio()
    assert type(ret)==list
    assert 1000 < len(ret) < 1e6
    assert "18f.gsa.gov" in ret

