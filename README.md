# timestudy

We are trying to develop a meaningful measurement technique and tool to characterize the state of distributed time synchronization among Internet servers.

The purpose of this project is to look at the clocks of servers on the
Internet and see if they have the proper time or not. Many do not.
For those that do not, we would like to characterize the following:


# Theory of Operation
New source code design:
## cronrunner.py 
Run from cron. Runs a single experiment
## webtime.py
Runs a single experiment

# Research Questions

* What kinds of time skews are observed? Buchholz and Tjaden observed several main categories:

** "Stuck" clocks.
** Wrong time, but progressing at a rate of R=1.0  (1 remote system second to 1 real second)
** Wrong time and drifting. (R!=1.0)
** Periodically were reset to the correct time, but then drifting. (R!=1.0, but with resetting)
** Single IP/hostname that jumps between two or more behaviors (indicates a load balancer, presumably, with multiple systems sharing a single IP address.)
** Random response.

* Are there any additional behaviors that can be characterized? (Am I missing any?)

* Can we quantify the behaviors above so that we can 1) recognize them automatically; 2) detect when a behavior changes?

* Are computers that are off by large amounts of time otherwise poorly managed?  Is there a relationship between a computer's vulnerability and how far its clock is off? (Probably, but how could we *test* this?)

* If round-robin DNS is used as a load balancer (many IP addresses for a domain), are all of the machines off by the same amount. e.g.:

    www.solardecathlon.gov              54.192.85.190        -21:57:13                      2016-05-14 01:38:26+00:00
    www.solardecathlon.gov              54.192.85.92         -21:57:13                      2016-05-14 01:38:26+00:00
    www.solardecathlon.gov              54.192.85.98         -21:57:13                      2016-05-14 01:38:26+00:00

## Regarding NTP

* Are there *any* NTP servers that are wrong that are listed in the authortative files?  If they are off, how long are they off?

* Can we survey the IPv4 address space for all NTP servers? 
** If so, are there any random NTP servers that are off? 
** Why are they off? 
** Do they follow the same kinds of behavior as HTTP servers that are off?


# Data Collection, Management and Analysis

Running this experiment requires three distinct activities: collection, management, and analysis.

*Collection* --- I have developed a collection program that will ask a remote website what time it is and store this in a database. This program needs to prioritize which host to scan next. The current system has a randomized priority system, in that it gets a list of randomly chosen hosts out of the database and then scans a bunch of them, then goes back for more.

The collection system is multi-threaded. An Amazon microinstance can support roughly 10 threads at a time in Python doing collection without noticable slowdown.

The hosts to scan are kept in a datatbase. Right now its a SQL database. The fastest way to choose 100 random hosts from a database is NOT to sort the database by RANDOM() and then sort and take a LIMIT. Instead, it's better to select those that have RANDOM() <  100 / TABLE SIZE. (This really surprised me, but it's dramatically faster to do that later, because no sort is required, and because most of the rows in the database don't need to be brought into memory). 

*Management* --- The data has to be stored somewhere. Experiments demonstrate that storing in a database is significantly faster than storing in a flat file. (Really!)  We explored storing in sqlite3 and mysql. Sqlite3 is significantly faster than mysql, but it doesn't support multi-user access in any way that is reasonable. The MySQL schema we have should scale to 1B rows. To go beyond that you may wish to explore mongodb. Other databases to consider are MongoDB, DynamoDB (on Amazon), and the various Amazon RDS products. If you can set up your own cluster, consider MongoDB and Cassandra. 

*Analysis* --- It's not clear what to do here. I have code that will print pretty reports about which servers are far off. This is actualy used in the Collection phase --- if a server is far off, you probably want to measure it more often than a server that has the right time. If a server is erratic you want to measure it even more often, until you figure out why it is erratic.

# Other open questions:

* Can you use a Kalman Filter to improve measurements or predictions?

# Code written to date

In this repository you will find the following:

README.md - This file

StratumOneTimeServers - The Stratum One Time Servers

StratumTwoTimeServers - The Stratum Two Time Servers

config.ini.dist - Configuration file. Right now it just has database host/name/username/password. Except it doesn't have the password. Put the password in and rename config.ini.

getservers.py --- extracts the servers from the public NTP list and parsers them.

getusg.py --- Grabs the USG servers from usgv6-deploymon.antd.nist.gov. Can we get a better source?

ntp.txt --- My notes on NTP servers

report.py --- That report program I mentioned above.

schema.sql --- the best schema I came up with.

ttd.txt --- Stuff that needs to be done.

webtime.py --- the acquisition program.

webtime.sql --- another schema.




## Related Work

This study revisits the research question posed by:

```
@article{brief-study-of-time,
  title="A brief study of time",
  author="Florian Buchholz and Brett Tjaden",
  year=2007,
  journal="Digital Investigation",
  volume="4",
  issue="S",
  pages="S31--S42"
}
```

## Methodology

This study will use the methodology described in the Buchholz and Tjaden paper for sensing the time on remote servers, specifically:

* Method 1 --- Examine HTTP headers.
* Method 2 --- NTP queries
* [Method 3 --- tcp timestamp] --- This method no longer works because most systems no longer implement this option.


clockdiff in iputils used to determine idfference

# Resources

## NTP Server List:
* Servers: http://support.ntp.org/bin/view/Servers/StratumOneTimeServers
* Servers: http://support.ntp.org/bin/view/Servers/StratumTwoTimeServers

## Databases

* Look at TokuMX, a drop-in replacement for MongoDB. https://www.percona.com/downloads/percona-tokumx/

