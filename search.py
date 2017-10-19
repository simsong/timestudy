#!/usr/bin/env python3

#https://support.alexa.com/hc/en-us/articles/200461990-Can-I-get-a-list-of-top-sites-from-an-API-
#http://s3.amazonaws.com/alexa-static/top-1m.csv.zip

import sys
if sys.version < '3':
    raise RuntimeError("Requires Python 3")

import cgi
import cgitb
import db
import os

CONFIG_INI="config.ini"

def search_host(dbc,host):
    if host=="":
        yield list()
    for row in dbc.execute("select qdatetime,host,ipaddr,offset from times where host like '%{}%'".format(host)):
        yield row
    

if __name__=="__main__":
    import argparse

    cgitb.enable()
    print("Content-Type: text/html")
    print()
    
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    parser.add_argument("--timeout",type=float,default=3,help="HTTP connect timeout")
    parser.add_argument("--limit",type=int,help="Limit to LIMIT oldest hosts",default=100000)
    parser.add_argument("-j","--threads",type=int,help="Specify number of threads",default=0)

    args = parser.parse_args()
    assert os.path.exists(args.config)
    config = db.get_mysql_config(args.config)       # prep it with default MySQL parameters
    dbc = db.mysql(config)

    form = cgi.FieldStorage()
    q = form.getfirst("q","").lower()
    
    #print("q={}".format(q))
    print("<form><input type='text' name='q'/><input type='submit'></form>")
    
    if q:
        print("<p>Search <b>{}</b></p>".format(q))
        print("<table>")
        print("<tr>{}</tr>".format("".join("<th>{}</th>".format(x) for x in ['datetime','host','ipaddr','offset'])))
        for row in search_host(dbc,q):
            print("<tr>{}</tr>".format("".join("<td>{}</td>".format(x) for x in row)))
        print("</table>")

    print("<p><i>{}</i></p>".format(dbc.select1("select version();")[0]))
    
