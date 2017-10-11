#!/usr/bin/env python3

# library for dealing with USG hosts


import glob
import urllib
import urllib.request
import re
from bs4 import BeautifulSoup

def url_to_hostname(s):
    from urllib.parse import urlparse
    netloc = urlparse(s).netloc
    c = netloc.find(':')
    return netloc[0:c] if c>0 else netloc

def usg_from_nist():
    """Return a list of USG hosts from the NIST setting"""
    page = urllib.request.urlopen("http://usgv6-deploymon.antd.nist.gov/cgi-bin/generate-gov.v4").read()
    soup = BeautifulSoup(page,'lxml')

    return [ url_to_hostname( link.get('href') )
             for link in soup.findAll('a', attrs={'href': re.compile("^https?://")})]

def usg_from_analytics():
    URL = "https://analytics.usa.gov/data/live/sites.csv"
    req = urllib.request(URL,headers={'Accept-encoding':'identity'})
    data = req.urlopen(URL).read()
    print("data:",data)
    exit(0)

    resource = urllib.request.urlopen(URL)
    print("resource=",resource)
    print("resource.headers.get_content_charset()=",resource.headers.get_content_charset())
    print("resource.read()=",resource.read().decode('utf-8'))
    contents  = resource.read().decode(resource.headers.get_content_charset())
    return contents.splitlines()


if __name__=="__main__":
    print("usg_from_analytics:")
    print(usg_from_analytics())
