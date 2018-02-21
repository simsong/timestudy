#!/usr/bin/env python3

#https://support.alexa.com/hc/en-us/articles/200461990-Can-I-get-a-list-of-top-sites-from-an-API-
#http://s3.amazonaws.com/alexa-static/top-1m.csv.zip

import sys
if sys.version < '3':
    raise RuntimeError("Requires Python 3")

import db
import os
import time

def log_search_host(dbc,host):
    if host=="":
        yield list()
    for row in dbc.execute("select qdatetime,host,ipaddr,offset from times where (host like '%{}%') or (ipaddr like '%{}%')".format(host,host)):
        yield row
    
def html_search_host(dbc,host):
    print("<table>")
    print("<tr>{}</tr>".format("".join("<th>{}</th>".format(x) for x in ['datetime','host','ipaddr','offset'])))
    for row in log_search_host(dbc,host):
        print("<tr>{}</tr>".format("".join("<td>{}</td>".format(x) for x in row)))
    print("</table>")


def ipaddrs_for_host(dbc,host):
    v4addrs = [row[0] for row in dbc.execute("select distinct ipaddr from dated where host=%s and ipaddr>'' and isv6=0 order by ipaddr",(host,)).fetchall()]
    v6addrs = [row[0] for row in dbc.execute("select distinct ipaddr from dated where host=%s and ipaddr>'' and isv6=1 order by ipaddr",(host,)).fetchall()]
    return v4addrs + v6addrs

def tr(*args):
    return '<tr>{}</tr>\n'.format("".join('<td>{}</td>'.format(x) for x in args))

def percent(num,total):
    return "{:,} ({:.2}%)".format(num,float(num)*100.0/float(total))

def html_info_host(dbc,host):
    print("<style>")
    print("table { border-collapse: collapse; }")
    print("table, th, td { border: 1px solid black; }")
    print("</style>")
    for ipaddr in ipaddrs_for_host(dbc,host):
        print("<p><table>")
        print( tr(host,ipaddr) )
        (date1,date2,qcount,wtcount) = dbc.select1("SELECT MIN(qdate),MAX(qdate),SUM(qcount),SUM(wtcount) "
                                                   "FROM dated WHERE host=%s AND ipaddr=%s",(host,ipaddr))
        print( tr('First query', date1) )
        print( tr('Last query',  date2) )
        print( tr('Number queries', qcount))
        print( tr('Avg queries per day', float(qcount)/((date2-date1).days+1)))
        print( tr('Nummber of wrong time queries: ', percent(wtcount,qcount)))
        print( tr('Clock offset data:' ))
        print( tr('Num offset classes: ', 'TBD'))
        print( tr("RTT Data:"))
        (qavg,qstddev,qmin,qmax) = dbc.select1("SELECT AVG(qduration),STD(qduration),MIN(qduration),MAX(qduration) FROM times WHERE host=%s AND ipaddr=%s",(host,ipaddr))
        print( tr("mean", qavg))
        print( tr("Std dev.", qstddev))
        print( tr("qmin", qmin))
        print( tr("qmax", qmax))
        print("</table></p>")
        
        

if __name__=="__main__":
    import argparse

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    parser.add_argument("--timeout",type=float,default=3,help="HTTP connect timeout")
    parser.add_argument("--limit",type=int,help="Limit to LIMIT oldest hosts",default=100000)
    parser.add_argument("--info",help='info on this host')

    args = parser.parse_args()
    assert os.path.exists(args.config)
    config = db.get_mysql_config(args.config)       # prep it with default MySQL parameters
    dbc = db.mysql(config)

    if args.debug:
        dbc.debug=1

    if args.info:
        print(html_info_host(dbc,args.info))
        exit(0)
    

    import cgi
    import cgitb
    cgitb.enable()
    print("Content-Type: text/html")
    print()
    
    form = cgi.FieldStorage()
    q = form.getfirst("q","").lower()
    t = form.getfirst("type","").lower()
    q = "".join(filter(lambda ch:ch.isalnum() or ch in "-_.",q))
    
    print("Log search: <form><input type='text' name='q'/><input type='submit'><input type='hidden' name='type' value='log'></form>")
    print("Host Info: <form><input type='text' name='q'/><input type='submit'><input type='hidden' name='type' value='info'></form>")
    
    if q:
        t0 = time.time()
        print("<p>Search <b>{}</b></p>".format(q))
        print("<p>...</p>")
        sys.stdout.flush()

        if t=='info':
            html_info_host(dbc,q)
        else:
            html_search_host(dbc,q)
        t1 = time.time()
        print("<p>Query time: {}msec</p>".format(t1-t0))

    print("<p><i>{}</i></p>".format(dbc.select1("select version();")[0]))
    
