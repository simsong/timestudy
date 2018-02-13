#!/usr/bin/env python3

# library for dealing with FDIC hosts

FNAME = "etc/INSTITUTIONS2.CSV"

import csv

def url_to_hostname(s):
    from urllib.parse import urlparse
    netloc = urlparse(s).netloc.lower()
    c = netloc.find(':')
    return netloc[0:c] if c>0 else netloc

def fdic_institutions_from_csv():
    """Return a list of USG hosts from the NIST setting"""
    ret = ['time.gov','time.nist.gov'] # # internal controls
    with open('etc/FDIC_INSTITUTIONS2.CSV','r',encoding='latin1') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = url_to_hostname(row['WEBADDR'])
            if name:
                ret.append(name)
    return ret

if __name__=="__main__":
    print(fdic_institutions_from_csv())
