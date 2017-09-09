#!/usr/bin/env python3
import glob
import urllib
import urllib.request
import re
from bs4 import BeautifulSoup


if __name__=="__main__":
    page = urllib.request.urlopen("http://usgv6-deploymon.antd.nist.gov/cgi-bin/generate-gov.v4").read()
    soup = BeautifulSoup(page,'lxml')
    for link in soup.findAll('a', attrs={'href': re.compile("^https?://")}):
        print(link.get('href'))
