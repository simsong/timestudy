import pymysql, sys, time
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

def time_diff(conn, img_dir, startdate=None):
    c = conn.cursor()
    c.execute("select distinct ipaddr from times")
    ips = [row[0] for row in c.fetchall()]
    print (len(ips))
    cmd = "select qdatetime from times where ipaddr='%s'" 
    if startdate:
        cmd += " and qdatetime > '%s'" % startdate.strftime("%Y-%m-%d %H:%M:%S")
    htmlfile = open("/var/www/html/time-data/timediffs.html", 'w')
    htmlfile.write("<!DOCTYPE html>\n\n<html>\n")
    htmlfile.write("<head>\n\t<link rel='stylesheet' href='style.css'>\n</head>\n")
    count = 0
    for ip in ips:
        if count % 500 == 0:
            print (str(count))
        img_name = ip.replace(".","-")+".png"
        times = []
        c.execute(cmd % ip)
        for row in c.fetchall():
            times.append(row[0])
        if len(times) > 0:
            times.sort()
            deltas = {}
            prev_time = times[0]
            for t in times:
                timediff = t-prev_time
                try:
                    deltas[int(timediff.total_seconds())] += 1
                except KeyError:
                    deltas[int(timediff.total_seconds())] = 1
                prev_time = t
            delta_counts = [0 for i in range(max(deltas)+1)]
            for d in deltas:
                delta_counts[d] += 1
            plt.clf()
            plt.vlines(list(deltas.keys()), 0, list(deltas.values()))
            plt.savefig(img_dir+img_name)
            img_loc = img_dir.split("/")[-2:][0]+'/'+img_name
            htmlfile.write("<div class='floated_img'>\n\t<img src='%s' alt=\%s\>\n\t<p style='font-size:20px'>%s</p>\n</div>\n" % (img_loc, img_loc, img_name))
        count += 1
    htmlfile.write("</html>")
    htmlfile.close()
    
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print ("Password Required")
    else:
        print (time.asctime())
        conn = mysql_connect(sys.argv[1])
        starttime = datetime(2017, 7, 20, 14)
        time_diff(conn, "/var/www/html/time-data/timediffplots/", starttime)
        print (time.asctime())
