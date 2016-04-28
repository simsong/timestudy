#!/usr/bin/env python3
from bs4 import BeautifulSoup, SoupStrainer
import glob
import urllib.request
import re



if __name__=="__main__":
    page = urllib.request.urlopen("http://usgv6-deploymon.antd.nist.gov/cgi-bin/generate-gov.v4").read()
    for link in BeautifulSoup(page, "lxml", parse_only=SoupStrainer('a')):
        try:
            import urllib
            o = urllib.parse.urlparse(link.attrs['href'])

        except AttributeError:
            pass
