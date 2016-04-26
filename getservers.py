#!/usr/bin/env python3
from bs4 import BeautifulSoup, SoupStrainer
import glob
import urllib.request
import re

ip_re = re.compile(b"(\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3})")

def find_servers(text):
    servers = set()
    for link in BeautifulSoup(text, "lxml", parse_only=SoupStrainer('a')):
        try:
            url = link.attrs['href']
            print(url)
        except AttributeError:
            continue
        except KeyError:
            continue
        if url.startswith("/bin/view/Servers/PublicTimeServer"):
            url = "http://support.ntp.org"+url
            page = urllib.request.urlopen(url).read()
            print("read {} bytes from {}".format(len(page),url))
            m = ip_re.search(page)
            if m:
                print(m.group(1))




if __name__=="__main__":
    for fname in glob.glob("Stratum*"):
        find_servers(open(fname,"rb").read())
