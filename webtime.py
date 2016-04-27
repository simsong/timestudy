#!/usr/bin/env python3
#https://support.alexa.com/hc/en-us/articles/200461990-Can-I-get-a-list-of-top-sites-from-an-API-
#http://s3.amazonaws.com/alexa-static/top-1m.csv.zip

import csv
import time

def webtime(host):
    import time
    from http import client
    import email
    import datetime
    import socket

    t0 = time.time()

    prefixes = ["","","","www.","www.","www.","www1.","www2.","www3."]
    prefixes = [""]

    for prefix in prefixes:
        qhost = prefix+host
        print("{}\t\t\r".format(qhost),end="")
        connection = client.HTTPConnection(qhost,timeout=5)
        try:
            connection.request("HEAD","/")
            response = connection.getresponse()
        except client.RemoteDisconnected:
            continue
        except socket.gaierror:
            continue
        except socket.timeout:
            continue
        except NameError:
            continue
        except ConnectionResetError:
            continue
        except client.BadStatusLine:
            continue
        except OSError:
            continue
        t1 = time.time()
        for (key,val) in filter(lambda r:r[0]=='Date',response.getheaders()):
            if val:
                date = email.utils.parsedate_to_datetime(val)
                yield (qhost,val,date.timestamp(),date.timestamp()-time.time())

def queryhost(vax):
    (rank,host) = vax
    for (qhost,val,t,dt) in webtime(host):
        sign = " "
        if dt<0:
            dt = -dt;
            sign = "-"
        if dt<5:
            continue
        sec  = int(dt % 60)
        min  = int((dt/60) % 60)
        hour = int(dt / 3600)
        print("{:4} {:30} {:30} {}{:02}:{:02}:{:02}".format(rank,qhost,val,sign,hour,min,sec))    



if __name__=="__main__":
    #for i in range(10000):
    #    queryhost(45,"blogspot.com")

    from multiprocessing import Pool

    count = 100
    start = time.time()
    lookups = 0
    urls = []
    for line in csv.reader(open("top-1m.csv"),delimiter=','):
        urls.append(line)
        if len(urls)>count:
            break
    pool = Pool(15)
    results = pool.map(queryhost,urls)
    end = time.time()
    print("Total lookups: {}  lookups/sec: {}".format(count,count/(end-start)))
    

        
