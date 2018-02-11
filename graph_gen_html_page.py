# -*- coding: utf-8 -*-
#
# time analysis plotting system.
# Log:
# 2017-06-16 Created by anj1
# 2018-02-11 Cleaned up by simson

CONFIG_INI = "config.ini"

# plotting system:
import matplotlib 
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdt
from matplotlib.dates import MO

import os, sys, pymysql, re, operator, time, graphgen, configparser

from datetime import datetime, timedelta
import db


def reverse_host(host):
    """Give a hostname, reverse the order of the sections"""
    return ".".join(list(reversed(host.split('.'))))

def ipaddrs_for_host(host):
    return [row[0] for row in dbc.execute("SELECT DISTINCT ipaddr FROM times where host=%s",host)]

def get_sizes(dbc):
    c = dbc.execute("select table_schema 'DB Name', SUM(data_length+index_length)/1024/1024 'Database Size' FROM information_schema.TABLES where table_schema='time'")
    tablesize = c.fetchall()[0][1]
    tables = ["times", "dated"]
    sizes = []
    for t in tables:
        c = dbc.execute("select count(*) from "+t)
        sizes.append(c.fetchall()[0][0])
    return (tablesize, sizes[0], sizes[1])

def page_by_host(dbc, img_dir, html_dir):
    if args.host:
        hosts = [args.host]
    else:
        hosts = [row[0] for row in dbc.execute("SELECT DISTINCT host FROM times").fetchall()]

    if args.debug:
        print("total hosts:",hosts)

    hosts_r = sorted([reverse_host(s) for s in hosts])
    epoch = datetime.utcfromtimestamp(0)
    num_hosts, num_empty_hosts = 0, 0
    htmlfile = open(os.path.join(html_dir,"index.html"), 'w')
    htmlcode = ""
    htmlfile.write("<!DOCTYPE html>\n\n<html>\n")

    if not args.nosizes:
        tablesize, timessize, datedsize = get_sizes(dbc)
        htmlcode += "<a href='byip.html'>Plots by IP</a>\n"
        htmlcode += ("<p style='font-size:20px'>Rows in 'times': %s</p>\n" % timessize)
        htmlcode += ("<p style='font-size:20px'>Rows in 'dated': %s</p>\n" % datedsize)
        htmlcode += ("<p style='font-size:20px'>Database size: %s MB</p>\n" % tablesize)
        
    htmlcode += ("<p style='font-size:20px'>Latest update: %s</p>\n" % datetime.strftime(datetime.now(), "%m-%d-%Y %H:%M:%S"))
    htmlcode += "<table>\n"
    htmlfile.write(htmlcode)

    for host_r in hosts_r:
        host = '.'.join(list(reversed(host_r.split('.'))))
        if args.debug:
            print("DEBUG: host {}".format(host))
        total_points = 0
        ips = ipaddrs_for_host(host)
        if not ips:
            continue            # no ipaddresses for this host!
        hyper_printed = False
        stats_str = host+":\n"
        # Add in a timeseries line for each IP address associated with the hostname
        ipcount = 0
        for ip in ips:
            print("DEBUG    ip {}".format(ip))
            plt.close('all')
            fig, ax1 = plt.subplots()
            ax2 = ax1.twinx()
            abs_sum = 0
            c.execute("select qdatetime, offset, qduration from times where host='%s' and ipaddr='%s'" % (host, ip))
            points = []
            all_low = True
            for row in c.fetchall():
                time, oset, rtt = row
                oset = int(oset)
                # if the offset value is between -2 and 2, assume it is zero
                if all_low and oset >= 3:
                    all_low = False
                epochseconds = int((time-epoch).total_seconds())
                points.append((epochseconds, time, oset, rtt))
                #                for es, t, oset in points:
                #                    abs_sum += abs(oset)

            # if the plot consists of all zeroes or has only 1 point, don't plot it
            if all_low or len(points) < 100:
                num_empty_hosts += 1
            else:
                c.execute("select qdate,qcount,ecount from dated where ipaddr='%s'" % (ip))
                qpoints = []
                zeroes = 0
                total_queries = 0
                num_points = len(points) 
                for qdate,qcount,ecount in c.fetchall():
                    total_queries += int(qcount)
                    zeroes -= int(ecount)
                    qpoints.append((qdate, qcount))
                zeroes += total_queries - num_points
                qdates, qtimes = zip(*sorted(qpoints))
                ax2.plot(qdates, qtimes, "+", label="queries", color='g', zorder=0)  
                num_hosts += 1
                ipcount += 1
                img_name = host.replace(".", "-")+str(ipcount)+".png"
                total_points += num_points
                epochtimes, times, offsets, rtts = zip(*sorted(points, key=operator.itemgetter(0)))
                # calculate the features and record them as a caption on the html page
                chars = graphgen.gen_chars(offsets)
                f_query = qdates[0].strftime('%m/%d/%Y')
                l_query = qdates[len(qdates)-1].strftime('%m/%d/%Y')
                offset_mean = sum(offsets)/num_points
                offset_std = (sum([(i-offset_mean)**2 for i in offsets])/num_points)**0.5
                rtt_mean = sum(rtts)/num_points
                rtt_std = (sum([(i-rtt_mean)**2 for i in rtts])/num_points)**0.5
                stats_str = "%s (%d points)\n\tFirst query: %s\n\tLast query: %s\n\tzeroes: %d (%f%%)\n\tnum offset classes: %d\n\toffset stats:\n\t\tmean: %4f\n\t\tstd. dev.: %4f\n\t\tmin: %d\n\t\tmax: %d\n\tRTT stats:\n\t\tmean: %4f\n\t\tstd. dev.: %4f\n\t\tmin: %4f\n\t\tmax: %4f" % (ip, len(points), f_query, l_query, zeroes, 100*zeroes/total_queries, chars[1], offset_mean, offset_std, min(offsets), max(offsets), rtt_mean, rtt_std, min(rtts), max(rtts))
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
                plt.savefig(img_dir+img_name, bbox_inches='tight')
                if not hyper_printed:
                    host_anchor = host.replace(".","_")
                    htmlfile.write("<tr>\n\t<td><a href='http://%s'>%s</a></td></tr>" % (host, host))
                    hyper_printed = True
                    htmlfile.write("<tr>\n\t<td><a href='#%s'><img id='%s' src='%s' alt='%s'></a></td>" % (host_anchor, host_anchor, img_dir.split("/")[-2:][0]+'/'+img_name, "timeseries plot " + str(num_hosts)))
                else:
                    htmlfile.write("<tr>\n\t<td><img src='%s' alt='%s'></td>" % (img_dir.split("/")[-2:][0]+'/'+img_name, "timeseries plot " + str(num_hosts)))
                htmlfile.write("\t<td align='left'><pre>%s</pre></td>\n</tr>\n" % stats_str)
    
    htmlfile.write("</table>")
    htmlfile.write("</html>")
    htmlfile.close()
    print ("Images created: " + str(num_hosts))

def page_by_ip(dbc, img_dir, html_dir):
    c = dbc.cursor()
    cmd = "select distinct ipaddr from times"
    c.execute(cmd)
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
        c = dbc.execute("select distinct host from times where ipaddr='%s'" % ip)
        plt.clf()
        img_name = ip.replace(".", "-")+".png"
        for row in c.fetchall():
            host = row[0]
            hosts.add(host)
        if len(hosts) != 0:
            for host in hosts:
                abs_sum = 0
                c = dbc.execute("select qdatetime, offset from times where host='%s' and ipaddr='%s'" % (host, ip))
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
                    chars = graphgen.gen_chars(offsets)
                    plt.plot(times, offsets, "-x", label=host)
            if total_points > 0:
                plt.gca().xaxis.set_major_formatter(mdt.DateFormatter('%m/%Y'))
                plt.gca().xaxis.set_major_locator(mdt.MonthLocator())
                plt.gcf().autofmt_xdate()
                plt.legend(bbox_to_anchor=(1.05, 1), loc=2)
                plt.savefig(img_dir+img_name, bbox_inches='tight')
                htmlfile.write("<tr>\n\t<th><img src='%s' alt='%s'></th>" % (img_dir.split("/")[-2:][0]+'/'+img_name, "timeseries plot " + str(num_hosts)))
                htmlfile.write("\t<td align='left'><pre>%s</pre></td>\n</tr>\n" % (ip + ":\n" + str(hosts)[1:-1]))
    
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

    dbc.execute("set innodb_lock_wait_timeout=20")
    dbc.execute("set tx_isolation='READ-COMMITTED'")
    dbc.execute("set time_zone = '+00:00'")

    print("Starting at {}".format(time.asctime()))
    t0 = time.time()
    page_by_host(dbc, os.path.join(args.outdir,'hostplots'), args.outdir)
    page_by_ip(dbc, os.path.join(args.outdir,'ipplots'), args.outdir)
    t1 = time.time()
    print("Took {} seconds".format(t1-t0))
