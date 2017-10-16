#!/usr/bin/env python3
#
# hosts_ntp_servers.py:
# extract the public NTP servers from the Stratum files
#
from bs4 import BeautifulSoup, SoupStrainer
import glob
import urllib.request
import re
import os

ip_re = re.compile(b"(\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3})")

def extract_ntp_PublicTimeServer(page_text):
    s = BeautifulSoup(page_text,"lxml",parse_only=SoupStrainer('tr'))
    for row in s.findAll("tr"):
        cells = row.findAll("td")
        if len(cells)==2:
            name  = cells[0].text.strip()
            value = cells[1].text.strip()
            print(name,value)


def find_servers(server_list):
    servers = set()
    for link in BeautifulSoup(server_list, "lxml", parse_only=SoupStrainer('a')):
        try:
            url = link.attrs['href']
        except AttributeError:
            continue
        except KeyError:
            continue
        if url.startswith("/bin/view/Servers/PublicTimeServer"):
            url = "http://support.ntp.org"+url
            print("          ")
            print(url)
            bn = os.path.basename(url)
            if not os.path.exists(bn):
                open(bn,"wb").write(urllib.request.urlopen(url).read())
                print("read {} bytes from {}".format(os.path.getsize(bn),url))
            extract_ntp_PublicTimeServer(open(bn,"rb"))



if __name__=="__main__":
    for fname in glob.glob("Stratum*"):
        find_servers(open(fname,"rb").read())
