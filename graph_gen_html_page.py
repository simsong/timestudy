# -*- coding: utf-8 -*-
#
# time analysis plotting system.
# Log:
# 2017-06-16 Created by anj1
# 2018-02-11 Cleaned up by simson

CONFIG_INI = "config.ini"
MIN_OFFSET = 3
EPOCH = datetime.utcfromtimestamp(0)

# plotting system:
import matplotlib 
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdt
from matplotlib.dates import MO

import os
import sys
import re
import operator
import time
import configparser
import statistics

from datetime import datetime, timedelta
import pytz

MIN_POINTS_TO_PLOT=10
DEFAULT_TIME_ZONE='America/New_York'

import db


def now():
    return datetime.now(pytz.timezone(DEFAULT_TIME_ZONE)).strftime("%Y-%m-%d %H:%M:%S %z")

def reverse_host(host):
    """Give a hostname, reverse the order of the sections"""
    return ".".join(list(reversed(host.split('.'))))

def ipaddrs_for_host(dbc,host):
    return [row[0] for row in dbc.execute("SELECT DISTINCT ipaddr FROM times where host=%s",(host,))]

def get_sizes(dbc):
    c = dbc.execute("select table_schema 'DB Name', SUM(data_length+index_length)/1024/1024 'Database Size' FROM information_schema.TABLES where table_schema='time'")
    tablesize = c.fetchall()[0][1]
    tables = ["times", "dated"]
    sizes = []
    for t in tables:
        c = dbc.execute("select count(*) from "+t)
        sizes.append(c.fetchall()[0][0])
    return (tablesize, sizes[0], sizes[1])

STATS_FMT=""""%s (%d points)
        First query: %s
        Last query: %s
        zeroes: %d (%f%%)
        num offset classes: %d
        offset stats:
        \tmean: %4f
        \tstd. dev.: %4f
        \tmin: %d
        \tmax: %d
        RTT stats:
        \tmean: %4f
        \tstd. dev.: %4f
        \tmin: %4f
        \tmax: %4f"""

def show_tables(dbc):
    print("tables:",dbc.execute("SHOW TABLES").fetchall())

# The mysterious mad_outliers function
def mad_outliers(ts, threshold):
    med = ts[len(ts)//2]
    absdiff = [abs(t-med) for t in ts]
    meddiff = absdiff[len(absdiff)//2]
    if meddiff == 0:
        return [abs(t) > abs(med) for t in absdiff]
    else:
        return [(t*0.6745)/meddiff > threshold for t in absdiff]


# The mysterious get_breaks function
def get_breaks(ts_sorted, avg_trend, threshold):
    breaks = []
    if avg_trend == 0:
        trend_threshold = threshold
    else:
        trend_threshold = (1+threshold)*avg_trend
    prev_os, class_min = ts_sorted[0], ts_sorted[0]
    in_range = lambda x, y: (-trend_threshold <= (x-y) <= trend_threshold) or (-trend_threshold >= (x-y) >= trend_threshold)
    for offset in ts_sorted:
        if not in_range(offset, prev_os):
            breaks.append((class_min, prev_os))
            class_min = offset
            prev_os = offset
        else:
            prev_os = offset
            
    return breaks
        
# The mysterious gen_chars function. What does this do?
def gen_chars(ts):
    zeroes = ts.count(0)
    ts_sorted = sorted(ts)
    slopes = [ts[i+1] - ts[i] for i in range(len(ts)-1)]
    slopes_sorted = sorted(slopes)
    prev_slope = slopes[0]
    slope_changes = 0
    for s in slopes:
        if prev_slope != 0 and not s/prev_slope > 0:
            slope_changes += 1
        prev_slope = s
        
    trendpoints, trendsum = 0, 0
    is_outlier = mad_outliers(slopes_sorted, 3)
    for i in range(len(is_outlier)):
        if not is_outlier[i]:
            trendpoints += 1
            trendsum += slopes_sorted[i]
            
    if trendpoints == len(slopes_sorted):
        avg_trend_len = len(ts)
    else:
        avg_trend_len = len(ts)//(len(is_outlier)-trendpoints)
    avg_trend = trendsum/trendpoints
    offset_breaks = get_breaks(ts_sorted, avg_trend, 1)
    return (zeroes/len(ts), len(offset_breaks)+1, avg_trend_len/len(ts), avg_trend)



class Dated:
    __slots__ = ['ipaddr', 'qdate', 'qcount', 'ecount']
    def __init__(self,ipaddr,qdate,qcount,ecount)
        self.ipaddr = ipaddr
        self.qdate  = qdate
        self.qcount = qcount
        self.ecount = ecount
        
class Times:
    __slots__ = ['ipaddr', 'timet', 'offset', 'qduration']
    def __init__(self,ipaddr,timet,offset,qduration):
        self.ipaddr = ipaddr
        self.timet  = timet
        self.offset = offset
        self.qduration = qduration
        

class Plotter:
    def __init__(self,dbc,host,ipplots,htmlfile):
        self.dbc = dbc
        self.host = host
        self.ipplots = ipplots
        self.htmlfile = htmlfile
        self.dateds = []
        self.points = []        # bad times
        self.ips    = set()     # ipaddresses we've seen

    def get_data(self):
        # Get all of the bad reads at once, break into individual ipaddresses if needed
        # 
        for (ipaddr,qdatetime,offset,qduration) in dbc.execute("SELECT ipaddr, qdatetime, offset, qduration FROM times WHERE host=%s and abs(offset)>=%s",
                                                           (host,MIN_OFFSET)):
            timet = int((qdatetime-EPOCH).total_seconds())
            self.points.append(Times(ipaddr,timet,offset,qduration))
            self.ips.add(ipaddr)

        for (ipaddr,qdate,qcount,ecount) in dbc.execute("select ipaddr,qdate,qcount,ecount from dated where host=%s", (host,)):
            self.dated.append(Dated(ipaddr,qdate,qcount,ecount))

    def total_queries(self):
        return sum([d.qcount for d in self.dateds])
        
    def total_errors(self):
        return sum([d.ecount for d in self.dateds])

    def new_plot(self):
        plt.close('all')
        self.fig, self.ax1 = plt.subplots()
        self.ax2 = ax1.twinx()

    def make_plot(self):
        first = True
        for ip in self.ips:
            # Create a new plot if this is first time through or if we are creating many plots
            if first or self.manyplots:
                plt.close('all')
                first = False

            qpoints = []
            zeroes = 0
            total_queries = 0
            num_points = len(points) 
            zeroes += total_queries - num_points
            qdates, qtimes = zip(*sorted(qpoints))
            ax2.plot(qdates, qtimes, "+", label="queries", color='g', zorder=0)  
            num_hosts += 1
            ipcount += 1
            img_name = host.replace(".", "-")+str(ipcount)+".png"
            total_points += num_points
            epochtimes, times, offsets, rtts = zip(*sorted(points, key=operator.itemgetter(0)))
            # calculate the features and record them as a caption on the html page
            chars = gen_chars(offsets)
            f_query = qdates[0].strftime('%m/%d/%Y')
            l_query = qdates[len(qdates)-1].strftime('%m/%d/%Y')
            offset_mean = statistics.mean(offsets)
            offset_std  = statistics.stdev(offsets)
            rtt_mean = statistics.mean(rtts)
            rtt_std  = statistics.stdev(rtts)
            stats_str = STATS_FMT % (ip, len(points), f_query, l_query, zeroes, 100*zeroes/total_queries, chars[1], 
                                     offset_mean, offset_std, min(offsets), max(offsets), rtt_mean, rtt_std, min(rtts), max(rtts))
            #                    plt.plot(times, offsets, "-x", label=ip)
            o_pts, = ax1.plot(times, offsets, ".", color='b', label='offsets', zorder=10)
            o_line, = ax1.plot(times, offsets, color='b', alpha=0.1)
            r_pts, = ax1.plot(times, rtts, 'x', color='r', label='RTTs', zorder=5)
            r_line, = ax1.plot(times, rtts, color='r', alpha=0.1)
            ax1.set_title(host+": "+ip)
            ax1.set_ylabel('offset (sec)')
            ax2.set_ylabel('query count (per day)')
            ax1.xaxis.set_major_formatter(mdt.DateFormatter('%m/%d/%Y'))
            ax1.xaxis.set_major_locator(mdt.WeekdayLocator(byweekday=MO))
            fig.autofmt_xdate(rotation=90)
            ax1.legend(bbox_to_anchor=(1.05, 1), loc=2)
            ax2.legend(bbox_to_anchor=(1.05, 1), loc=3)
            plotsdir = os.path.join(outdir,HOSTPLOTS_SUBDIR)
            fname     = os.path.join(plotsdir,img_name)
            t0 = time.time()
            plt.savefig(fname, bbox_inches='tight')
            t1 = time.time()
            if args.debug:
                print("saved figure to {} in {:.4}s".format(fname,t1-t0))
            if not hyper_printed:
                host_anchor = host.replace(".","_")
                htmlfile.write("<tr>\n\t<td><a href='http://%s'>%s</a></td></tr>" % (host, host))
                hyper_printed = True
                htmlfile.write("<tr>\n\t<td><a href='#%s'><img id='%s' src='%s' alt='%s'></a></td>" %
                               (host_anchor, host_anchor, HOSTPLOTS_SUBDIR+"/"+img_name, "timeseries plot " + str(num_hosts)))
            else:
                htmlfile.write("<tr>\n\t<td><img src='%s' alt='%s'></td>" % (HOSTPLOTS_SUBDIR+"/"+img_name, "timeseries plot " + str(num_hosts)))
            htmlfile.write("\t<td align='left'><pre>%s</pre></td>\n</tr>\n" % stats_str)

    


HOSTPLOTS_SUBDIR='hostplots'
def page_by_host(dbc, outdir):
    if args.host:
        hosts = [args.host]
    else:
        hosts = [row[0] for row in dbc.execute("SELECT DISTINCT host FROM times")]
    if args.debug:
        print("total hosts:",hosts)

    hosts_r = sorted([reverse_host(s) for s in hosts])
    num_hosts, num_empty_hosts = 0, 0
    htmlfile = open(os.path.join(outdir,"index.html"), 'w')
    htmlcode = ""
    htmlfile.write("<!DOCTYPE html>\n\n<html>\n")

    show_tables(dbc)
    show_tables(dbc)
    show_tables(dbc)

    if not args.nosizes:
        tablesize, timessize, datedsize = get_sizes(dbc)
        htmlcode += "<a href='byip.html'>Plots by IP</a>\n"
        htmlcode += ("<p style='font-size:20px'>Rows in 'times': %s</p>\n" % timessize)
        htmlcode += ("<p style='font-size:20px'>Rows in 'dated': %s</p>\n" % datedsize)
        htmlcode += ("<p style='font-size:20px'>Database size: %s MB</p>\n" % tablesize)
        
    htmlcode += ("<p style='font-size:20px'>Latest update: {}</p>\n".format(now()))
    htmlcode += "<table>\n"
    htmlfile.write(htmlcode)

    for host_r in hosts_r:
        host = '.'.join(list(reversed(host_r.split('.'))))
        if args.debug:
            print("DEBUG: host {}".format(host))
        total_points = 0

        make_plot(dbc,host,ipaddrs=True)

    htmlfile.write("</table>")
    htmlfile.write("</html>")
    htmlfile.close()
    if args.debug:
        print("Images created: {}   skipped: {}".format(num_hosts,num_empty_hosts))

def page_by_ip(dbc, img_dir, html_dir):
    print("page_by_ip")
    c = dbc.execute("select distinct ipaddr from times")
    ips = [row[0] for row in c.fetchall()]
    epoch = datetime.utcfromtimestamp(0)
    num_hosts, num_empty_hosts = 0, 0
    htmlfile = open(os.path.join(html_dir,"byip.html"), 'w')
    htmlfile.write("<!DOCTYPE html>\n\n<html>\n")
    htmlfile.write("<a href='index.html'>Plots by host</a>\n")

    # We previously put the get_sizes() results in this page too, but that isn't necessary

    htmlfile.write("<table>\n")
    for ip in ips:
        hosts = set()
        total_points = 0
        c = dbc.execute("select distinct host from times where ipaddr=%s",(ip,))
        plt.clf()
        img_name = ip.replace(".", "-")+".png"
        for row in c.fetchall():
            host = row[0]
            hosts.add(host)
        if len(hosts) != 0:
            for host in hosts:
                abs_sum = 0
                c = dbc.execute("select qdatetime, offset from times where host=%s and ipaddr=%s", (host, ip))
                points = []
                for row in c.fetchall():
                    time, oset = row
                    oset = int(oset)
                    if oset < 3:
                        oset = 0
                    epochseconds = int((time-epoch).total_seconds())
                    points.append((epochseconds, time, oset))
                for es, t, oset in points:
                    abs_sum += abs(oset)
                if abs_sum == 0 or len(points) < 2:
                    num_empty_hosts += 1
                else:
                    num_hosts += 1
                    total_points += len(points)
                    epochtimes, times, offsets = zip(*sorted(points, key=operator.itemgetter(0)))
                    chars = gen_chars(offsets)
                    plt.plot(times, offsets, "-x", label=host)
            if total_points > 0:
                plt.gca().xaxis.set_major_formatter(mdt.DateFormatter('%m/%Y'))
                plt.gca().xaxis.set_major_locator(mdt.MonthLocator())
                plt.gcf().autofmt_xdate()
                plt.legend(bbox_to_anchor=(1.05, 1), loc=2)
                plt.savefig(img_dir+img_name, bbox_inches='tight')
                htmlfile.write("<tr>\n\t<th><img src='%s' alt='%s'></th>" % (img_dir.split("/")[-2:][0]+'/'+img_name, "timeseries plot " + str(num_hosts)))
                htmlfile.write("\t<td align='left'><pre>%s</pre></td>\n</tr>\n" % (ip + ":\n" + str(hosts)[1:-1]))
                htmlfile.flush()
    
    htmlfile.write("</table>")
    htmlfile.write("</html>")
    htmlfile.close()
    print ("Images created: " + str(num_hosts))
    
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--debug",action="store_true",help="write results to STDOUT")
    parser.add_argument("--verbose",action="store_true",help="output to STDOUT")
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    parser.add_argument("--host",help="Specify a host; just do the report for that one host")
    parser.add_argument("--usg",action="store_true",help="Only USG")
    parser.add_argument("--outdir",help="Where to put the output.",default='plots')
    parser.add_argument("--nosizes",help="Do not report the size of the tables",action='store_true')

    args = parser.parse_args()
    config = db.get_mysql_config(args.config)
    dbc    = db.mysql(config)

    if args.debug:
        dbc.debug = args.debug
        print("debug mode")

    dbc.execute("set innodb_lock_wait_timeout=20")
    dbc.execute("set tx_isolation='READ-COMMITTED'")
    dbc.execute("set time_zone = '+00:00'")

    print("Starting at {}".format(time.asctime()))
    t0 = time.time()
    page_by_host(dbc, args.outdir)
    #page_by_ip(dbc, os.path.join(args.outdir,'ipplots'), args.outdir)
    t1 = time.time()
    print("Took {:.2} seconds".format(t1-t0))
