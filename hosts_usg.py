#!/usr/bin/env python3

# library for dealing with USG hosts

TIMEOUT=10

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
    try:
        r = requests.get("http://usgv6-deploymon.antd.nist.gov/cgi-bin/generate-gov.v4",timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        return []
    soup = BeautifulSoup(r.text,'lxml')

    return [ url_to_hostname( link.get('href') )
             for link in soup.findAll('a', attrs={'href': re.compile("^https?://")})]

def usg_from_analytics():
    """Return a list of USG hosts from analytics.usa.gov"""
    URL = "https://analytics.usa.gov/data/live/sites.csv"
    try:
        r = requests.get(URL,timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        return []
    return r.text.splitlines()

def pulse_cio_gov_analytics():
    URL = 'https://analytics.usa.gov/data/live/sites.csv'
    try:
        r = requests.get(URL,timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        return []
    return r.text.splitlines()

def pulse_cio_gov_https():
    import csv
    URL = 'https://pulse.cio.gov/data/domains/https.csv'
    try:
        r = requests.get(URL,timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        return []
    return [row['Domain'] for row in csv.DictReader(r.text.splitlines(), delimiter=',', quotechar='"')]


def usg_from_cio():
    return list(set(pulse_cio_gov_analytics() + pulse_cio_gov_https()))

if __name__=="__main__":
    print("usg_from_analytics:")
    print(usg_from_analytics())
