import os, sys, pymysql, re, operator, time, graphgen
import matplotlib.pyplot as plt
import matplotlib.dates as mdt
from datetime import datetime, timedelta

def mysql_connect(passwd):
    mc = {"host":"db1.antd.nist.gov",
          "user":"anj1",
          "passwd":passwd,
          "port":0,
          "db":"time",
          "mysqldump":"mysqldump"}
    conn = pymysql.connect(host=mc["host"], port=int(mc["port"]), user=mc["user"], passwd=mc["passwd"], db=mc["db"])
    conn.cursor().execute("set innodb_lock_wait_timeout=20")
    conn.cursor().execute("set tx_isolation='READ-COMMITTED'")
    conn.cursor().execute("set time_zone = '+00:00'")
    return conn

def page_by_host(conn, img_dir):
    c = conn.cursor()
    cmd = "select distinct host from times"
    c.execute(cmd)
    hosts = [row[0] for row in c.fetchall()]
    epoch = datetime.utcfromtimestamp(0)
    num_hosts, num_empty_hosts = 0, 0
    htmlfile = open("/var/www/html/time-data/index.html", 'w')
    htmlfile.write("<!DOCTYPE html>\n\n<html>\n")
    tablesize, timessize, datedsize = get_sizes(conn)
    num_images = len(os.listdir(img_dir))
    htmlfile.write("<a href='byip.html'>Plots by IP</a>\n")
    htmlfile.write("<p style='font-size:20px'>Rows in 'times': %s</p>\n" % timessize)
    htmlfile.write("<p style='font-size:20px'>Rows in 'dated': %s</p>\n" % datedsize)
    htmlfile.write("<p style='font-size:20px'>Database size: %s MB</p>\n" % tablesize)
    htmlfile.write("<table>\n")

    for host in hosts:
        ips = set()
        total_points = 0
        c.execute("select distinct ipaddr from times where host='%s'" % host)
        plt.clf()
        img_name = host.replace(".", "-")+".png"
        for row in c.fetchall():
            ip = row[0]
            ips.add(ip)
        if len(ips) != 0:
            stats_str = host+":\n"
            for ip in ips:
                abs_sum = 0
                c.execute("select qdatetime, offset from times where host='%s' and ipaddr='%s'" % (host, ip))
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
                    stats_str += "%s (%s points)\n\tpercentage zeroes: %s\n\tnum offsets: %s\n\tavg trend len: %s\n" % (ip, str(len(points)), str(chars[0]), str(chars[1]), str(chars[2]))
                    plt.plot(times, offsets, "-x", label=ip)
            if total_points > 0:
                plt.gca().xaxis.set_major_formatter(mdt.DateFormatter('%m/%Y'))
                plt.gca().xaxis.set_major_locator(mdt.MonthLocator())
                plt.gcf().autofmt_xdate()
                plt.legend(bbox_to_anchor=(1.05, 1), loc=2)
                plt.savefig(img_dir+img_name, bbox_inches='tight')
                htmlfile.write("<tr>\n\t<th><img src='%s' alt='%s'></th>" % (img_dir.split("/")[-2:][0]+'/'+img_name, "timeseries plot " + str(num_hosts)))
                htmlfile.write("\t<td align='left'><pre>%s</pre></td>\n</tr>\n" % stats_str)
    
    htmlfile.write("</table>")
    htmlfile.write("</html>")
    htmlfile.close()
    print ("Images created: " + str(num_hosts))

def page_by_ip(conn, img_dir):
    c = conn.cursor()
    cmd = "select distinct ipaddr from times"
    c.execute(cmd)
    ips = [row[0] for row in c.fetchall()]
    epoch = datetime.utcfromtimestamp(0)
    num_hosts, num_empty_hosts = 0, 0
    htmlfile = open("/var/www/html/time-data/byip.html", 'w')
    htmlfile.write("<!DOCTYPE html>\n\n<html>\n")
    tablesize, timessize, datedsize = get_sizes(conn)
    num_images = len(os.listdir(img_dir))
    htmlfile.write("<a href='index.html'>Plots by host</a>\n")
    htmlfile.write("<p style='font-size:20px'>Rows in 'times': %s</p>\n" % timessize)
    htmlfile.write("<p style='font-size:20px'>Rows in 'dated': %s</p>\n" % datedsize)
    htmlfile.write("<p style='font-size:20px'>Database size: %s MB</p>\n" % tablesize)
    htmlfile.write("<table>\n")

    for ip in ips:
        hosts = set()
        total_points = 0
        c.execute("select distinct host from times where ipaddr='%s'" % ip)
        plt.clf()
        img_name = ip.replace(".", "-")+".png"
        for row in c.fetchall():
            host = row[0]
            hosts.add(host)
        if len(hosts) != 0:
            for host in hosts:
                abs_sum = 0
                c.execute("select qdatetime, offset from times where host='%s' and ipaddr='%s'" % (host, ip))
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
    
def get_sizes(conn):
    c = conn.cursor()
    c.execute("select table_schema 'DB Name', SUM(data_length+index_length)/1024/1024 'Database Size' FROM information_schema.TABLES where table_schema='time'")
    tablesize = c.fetchall()[0][1]
    tables = ["times", "dated"]
    sizes = []
    for t in tables:
        c.execute("select count(*) from "+t)
        sizes.append(c.fetchall()[0][0])
    return (tablesize, sizes[0], sizes[1])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print ("Password Required")
    else:
        print(time.asctime())
        start = time.time()
        conn = mysql_connect(sys.argv[1])
        page_by_host(conn, "/var/www/html/time-data/hostplots/")
        page_by_ip(conn, "/var/www/html/time-data/ipplots/")
        print ("Took %s seconds" % str(time.time()-start))
