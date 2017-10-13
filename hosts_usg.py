#!/usr/bin/env python3

# library for dealing with USG hosts


import requests
import glob
import re
from bs4 import BeautifulSoup

def url_to_hostname(s):
    from urllib.parse import urlparse
    netloc = urlparse(s).netloc
    c = netloc.find(':')
    return netloc[0:c] if c>0 else netloc

def usg_from_nist():
    """Return a list of USG hosts from the NIST setting"""
    r = requests.get("http://usgv6-deploymon.antd.nist.gov/cgi-bin/generate-gov.v4")
    soup = BeautifulSoup(r.text,'lxml')

    return [ url_to_hostname( link.get('href') )
             for link in soup.findAll('a', attrs={'href': re.compile("^https?://")})]

def usg_from_analytics():
    URL = "https://analytics.usa.gov/data/live/sites.csv"
    r = requests.get(URL)
    return r.text.splitlines()


if __name__=="__main__":
    print("usg_from_analytics:")
    print(usg_from_analytics())
