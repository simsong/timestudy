# -*- coding: utf-8 -*-
#
# time analysis plotting system.
# Log:
# 2017-06-16 Created by anj1
# 2018-02-11 Cleaned up by simson

CONFIG_INI = "config.ini"
MIN_OFFSET = 3

# plotting system:
import matplotlib 
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdt
from matplotlib.dates import MO
from collections import defaultdict
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
DATE_FORMAT='%Y-%m-%d'
EPOCH = datetime.utcfromtimestamp(0)

# https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/
VISUALLY_DISTINCT_COLORS=[
    #("Red", "#E6194B"),
    #("Green", "#3CB44B"),
    ("Blue", "#0082C8"),
    ("Orange", "#F58231"),
    ("Purple", "#911EB4"),
    ("Cyan", "#46F0F0"),
    ("Magenta", "#F032E6"),
    ("Lime", "#D2F53C"),
    ("Pink", "#FABEBE"),
    ("Teal", "#008080"),
    ("Lavender", "#E6BEFF"),
    ("Brown", "#AA6E28"),
    ("Beige", "#FFFAC8"),
    ("Maroon", "#800000"),
    ("Mint", "#AAFFC3"),
    ("Olive", "#808000"),
    ("Coral", "#FFD8B1"),
    ("Navy", "#000080")]

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


def ip_sort_function(ip):
    # https://stackoverflow.com/questions/5619685/conversion-from-ip-string-to-integer-and-backward-in-python
    import socket, struct
    if "." in ip:
        return struct.unpack("!I", socket.inet_aton(ip))[0]
    _str = socket.inet_pton(socket.AF_INET6, ip)
    a, b = struct.unpack('!2Q', _str)
    return (a << 64) | b


class Times:
    """Statistics for each measurement that is recorded"""
    __slots__ = ['ipaddr', 'timet', 'offset', 'qduration']
    def __init__(self,ipaddr,timet,offset,qduration):
        self.ipaddr = ipaddr
        self.timet  = timet
        self.offset = offset
        self.qduration = qduration
    def __repr__(self):
        return "<Times {} {} {} {}>".format(self.ipaddr,self.timet,self.offset,self.qduration)

class Dated:
    """Statistics for each Date"""
    __slots__ = ['ipaddr', 'qdate', 'qcount', 'ecount']
    def __init__(self,ipaddr,qdate,qcount,ecount):
        self.ipaddr = ipaddr
        self.qdate  = qdate
        self.qcount = qcount
        self.ecount = ecount
    def __repr__(self):
        return "<Dated {} {} {} {}>".format(self.ipaddr,self.qdate,self.qcount,self.ecount)
        
class Plotter:
    def __init__(self,dbc,host):
        self.dbc = dbc
        self.host = host
        self.dateds = []
        self.times  = []        # bad times
        self.ips    = defaultdict(int)     # ipaddresses we've seen

    def get_data(self):
        # Get all of the bad reads at once, break into individual ipaddresses if needed
        # 
        cmd = "SELECT qdatetime, ipaddr, offset, qduration FROM times WHERE host=%s and abs(offset)>=%s GROUP BY qdatetime ORDER BY qdatetime"
        for (qdatetime, ipaddr, offset, qduration) in dbc.execute(cmd, (self.host,MIN_OFFSET)):
            self.times.append( Times(ipaddr, qdatetime, offset, qduration) )
            self.ips[ipaddr] += 1

        for (ipaddr, qdate, qcount, ecount) in dbc.execute("select ipaddr,qdate,qcount,ecount from dated where host=%s GROUP BY qdate ORDER BY qdate", (self.host,)):
            self.dateds.append( Dated(ipaddr, qdate, qcount, ecount) )

    def total_queries(self):
        return sum([d.qcount for d in self.dateds])
        
    def total_errors(self):
        return sum([d.ecount for d in self.dateds])

    def make_plot(self,outdir):
        # Prepare the axes where the plot will go
        fig, ax1 = plt.subplots() # ax1 is in seconds; it tracks offsets and round-trip time
        ax2 = ax1.twinx()         # ax2 counts queries per day.

        # Create the graph axes
        ax1.set_title("{}: ".format(self.host))
        ax1.set_ylabel('offset (sec)')
        ax1.xaxis.set_major_formatter(mdt.DateFormatter(DATE_FORMAT))
        ax1.xaxis.set_major_locator(mdt.WeekdayLocator(byweekday=MO))

        # Plot the RTTs
        qdatetimes, qdurations = zip(*( (t.timet, t.qduration) for t in self.times))
        ax1.plot(qdatetimes, qdurations, 'x', color='r', label='RTTs', zorder=5)
        ax1.plot(qdatetimes, qdurations, color='r', alpha=0.5) # draw the round trip times

        # Plot the time offsets
        # We do a pass for each IP address, each in a different color
        color_number = 0
        for ip in sorted(set(self.ips),key=ip_sort_function):
            color = VISUALLY_DISTINCT_COLORS[color_number % len(VISUALLY_DISTINCT_COLORS)][1]
            color_number += 1
            if color_number > 100:
                color_number = 0
            ip_qdatetimes, ip_offsets = zip(*( (t.timet, t.offset) for t in self.times if t.ipaddr==ip))
            ax1.scatter(ip_qdatetimes, ip_offsets, s=2, color=color,
                        label='{} offset ({} points)'.format(ip,len(ip_offsets)),
                        zorder=10) # draw the blue dots
            ax1.plot(ip_qdatetimes, ip_offsets, color=color, alpha=0.5) # trace the line between the dots
        
        ax1.legend(bbox_to_anchor=(1.05, 1), loc=2)
        fig.autofmt_xdate(rotation=45)

        # Plot the query count
        qdates,qtimes = zip(*( (q.qdate,q.qcount) for q in self.dateds ) )
        ax2.plot(qdates, qtimes, "+", label="queries", color='g', zorder=0)  
        ax2.set_ylabel('query count (per day)')
        ax2.legend(bbox_to_anchor=(1.05, 1), loc=3)

        # Now save the graph
        self.img_name = self.host.replace(".", "-")+".png"
        plotsdir = os.path.join(outdir,HOSTPLOTS_SUBDIR)
        fname     = os.path.join(plotsdir,self.img_name)
        t0 = time.time()
        plt.savefig(fname, bbox_inches='tight')
        t1 = time.time()
        if args.debug:
            print("saved figure to {} in {:.4}s".format(fname,t1-t0))
        plt.close('all')

    def make_html(self,htmlfile):
        """Outputs the HTML that matches the graph that we just made"""
        # First line is the hostname and a link to the host
        host_anchor = self.host.replace(".","_")
        htmlfile.write("<a name='{}'><tr><td><a href='http://{}'>{}</a></td> </tr>".
                       format(host_anchor,self.host, self.host))
        htmlfile.write("<tr><td><a href='#{}'><img id='{}' src='{}' alt='{}'></a></td></tr>".
                       format(host_anchor, host_anchor, HOSTPLOTS_SUBDIR+"/"+self.img_name, "timeseries plot "))
        htmlfile.write("<tr><td align='left'><pre>")
        htmlfile.write(" • ".join(self.ips))
        htmlfile.write("\n")
        htmlfile.write("Query range: {} — {}\n".format(
            self.dateds[0].qdate.strftime(DATE_FORMAT),
            self.dateds[-1].qdate.strftime(DATE_FORMAT)))
                       
        def stats(name,data):
            return "{}:\n\tmean: {:8.2f}\n\tstd. dev.: {:8.2f}\n\tmin: {}\n\tmax: {}\n".format(
                name,
                statistics.mean(data),
                statistics.stdev(data),
                min(data),
                max(data))

        htmlfile.write(stats("Drift:",[t.offset for t in self.times]))
        htmlfile.write(stats("RTT",[t.qduration for t in self.times]))
        htmlfile.write("</pre></td></tr>\n")



HOSTPLOTS_SUBDIR='hostplots'
def page_by_host(dbc, outdir):
    if args.host:
        hosts = [args.host]
    else:
        hosts = [row[0] for row in dbc.execute("SELECT DISTINCT host FROM times")]
    if args.debug:
        print("total hosts:",hosts)

    hosts_reversed = sorted([reverse_host(s) for s in hosts])
    num_hosts, num_empty_hosts = 0, 0
    htmlfile = open(os.path.join(outdir,"index.html"), 'w')
    htmlcode = ""
    htmlfile.write("<!DOCTYPE html>\n\n<html>\n")

    if not args.nosizes:
        tablesize, timessize, datedsize = get_sizes(dbc)
        htmlcode += "<a href='byip.html'>Plots by IP</a>\n"
        htmlcode += ("<p style='font-size:20px'>Rows in 'times': %s</p>\n" % timessize)
        htmlcode += ("<p style='font-size:20px'>Rows in 'dated': %s</p>\n" % datedsize)
        htmlcode += ("<p style='font-size:20px'>Database size: %s MB</p>\n" % tablesize)
        
    htmlcode += "<p style='font-size:20px'>Latest update: {}</p>\n".format(now())
    htmlcode += "<table>\n"
    htmlfile.write(htmlcode)

    for host_reversed in hosts_reversed:
        host = '.'.join(list(reversed(host_reversed.split('.'))))

        p = Plotter(dbc,host)
        p.get_data()
        p.make_plot(outdir)
        p.make_html(htmlfile)

    htmlfile.write("</table>")
    htmlfile.write("</html>")
    htmlfile.close()
    if args.debug:
        print("Images created: {}   skipped: {}".format(num_hosts,num_empty_hosts))

#def page_by_ip(dbc, img_dir, html_dir):
#    print("page_by_ip")
#    c = dbc.execute("select distinct ipaddr from times")
#    ips = [row[0] for row in c.fetchall()]
#    epoch = datetime.utcfromtimestamp(0)
#    num_hosts, num_empty_hosts = 0, 0
#    htmlfile = open(os.path.join(html_dir,"byip.html"), 'w')
#    htmlfile.write("<!DOCTYPE html>\n\n<html>\n")
#    htmlfile.write("<a href='index.html'>Plots by host</a>\n")
#
#    # We previously put the get_sizes() results in this page too, but that isn't necessary
#
#    htmlfile.write("<table>\n")
#    for ip in ips:
#        hosts = set()
#        total_points = 0
#        c = dbc.execute("select distinct host from times where ipaddr=%s",(ip,))
#        plt.clf()
#        img_name = ip.replace(".", "-")+".png"
#        for row in c.fetchall():
#            host = row[0]
#            hosts.add(host)
#        if len(hosts) != 0:
#            for host in hosts:
#                abs_sum = 0
#                c = dbc.execute("select qdatetime, offset from times where host=%s and ipaddr=%s", (host, ip))
#                points = []
#                for row in c.fetchall():
#                    time, oset = row
#                    oset = int(oset)
#                    if oset < 3:
#                        oset = 0
#                    epochseconds = int((time-epoch).total_seconds())
#                    points.append((epochseconds, time, oset))
#                for es, t, oset in points:
#                    abs_sum += abs(oset)
#                if abs_sum == 0 or len(points) < 2:
#                    num_empty_hosts += 1
#                else:
#                    num_hosts += 1
#                    total_points += len(points)
#                    epochtimes, times, offsets = zip(*sorted(points, key=operator.itemgetter(0)))
#                    chars = gen_chars(offsets)
#                    plt.plot(times, offsets, "-x", label=host)
#            if total_points > 0:
#                plt.gca().xaxis.set_major_formatter(mdt.DateFormatter('%m/%Y'))
#                plt.gca().xaxis.set_major_locator(mdt.MonthLocator())
#                plt.gcf().autofmt_xdate()
#                plt.legend(bbox_to_anchor=(1.05, 1), loc=2)
#                plt.savefig(img_dir+img_name, bbox_inches='tight')
#                htmlfile.write("<tr>\n\t<th><img src='%s' alt='%s'></th>" % (img_dir.split("/")[-2:][0]+'/'+img_name, "timeseries plot " + str(num_hosts)))
#                htmlfile.write("\t<td align='left'><pre>%s</pre></td>\n</tr>\n" % (ip + ":\n" + str(hosts)[1:-1]))
#                htmlfile.flush()
#    
#    htmlfile.write("</table>")
#    htmlfile.write("</html>")
#    htmlfile.close()
#    print ("Images created: " + str(num_hosts))
    
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
