Short list of things we agreed to do, March 16th, 2018:
- [ ] rate limiting on the good sites
- [ ] EDUs
- [ ] Better backup of database
- [ ] NTP hosts
- [ ] Set up a system at NIST
- [ ] Query interface
- [ ] Metadata in the database to find problems
- [ ] Did anything happen on DST?



Database Enhancement
* make it so that we get ipaddr and cnames at the same time by using getipbyhostname_ex. Remove get_cname()
* Transparent databsae upgrades? We probably don't have enough out there yet. 
* Plots by IP address
* Search Interface
* .edu hosts: https://github.com/Hipo/university-domains-list
Target sources:
 
Alexa 500 – no csv, pay for more than 500: https://aws.amazon.com/alexa-top-sites/
Moz 500 – csv - https://moz.com/top500
Magic 1 Million - https://blog.majestic.com/development/majestic-million-csv-daily/
Cisco Umbrella 1 Million – CSV – DNS names, need to weed out zones from hosts - https://umbrella.cisco.com/blog/2016/12/14/cisco-umbrella-1-million/.
 
I used to have a better link to all .edu but can’t find it right now.
https://github.com/endSly/world-universities-csv
https://github.com/Hipo/university-domains-list
 
* * Smaller plots pages. For example, plots with offset>100, etc.

* Make output page in bootstrap, and add features like bootstrap_collapse.
  https://www.w3schools.com/bootstrap/bootstrap_collapse.asp
* Flag button, or Tag feature.  


* Query interface:
  • stats DB by:
  • Tags
  • Offset range
  • RTT range
  • %zeros etc
  • # queries etc

* Demonstrating that the server is not drifting, by regularly querying a time standard host.

10a - First we see the number of errors in the last WEEK (tunable) and the number of queries today
10b - If errors>0, we query.
10c - Otherwise, we query if we haven’t queried today

Adding back the stats on Queries, Avg Q per day, Zeros, %Zeros, Offsets, %Offsets would help.

* Check all zeros twice a day, not once a day, but at random intervals. (I guess that means every 12 hours?)


It would be nice to add back to the meta data:
 
# Queries, avg per day.
# Zeros, %zero.
# Non-zero, %non-zero.
# Of Unique IPs responding.


* Add metadata to each plot:
  Num URLs:  number of distinct URLs in graph/stats
  Num IPs:      number of distinct IPs in graph/stats

* Rework legend:
  Addresses:
   10.10.10.10 – CNAME (if exists) or DNS Name - #queries, #offsets, #zeros
   2620::1 - CNAME (if exists) or DNS Name - #queries, #offsets, #zeros
 
  Remove offset counts from legend … leave in meta data
  Print all float meta data "{0:.2f}"
 
Q: The outliers are interesting to think about … not sure what could make a -20 suddenly become a -10.
A: This happens in a lot of graphs, airnow.gov being one of many examples.

* Add logic so a host that hasn't had an invalid measurement in the last WINDOWDAYS days only gets checked once a day.

Reporing Enhancement:
* So one suggestion was if number of unique IPv4s > N, we join series by CNAME.  From what I can see that will collapse all couldfront lists to one CNAME. 

Sampling and Recording Enahncement:
* One per day, unless CONDITION is met.
* CONDITION = an errornous time within the past 7 days
* If CONDITION is met, record all samples (good and bad)

Real time reports:
Proposal is for a CGI script that displays a form if called without arguments, otherwise just performs the search.


Q: I guess it might also not over react to the on random bad measurement.
A: THIS IS EXCEEDINGLY IMPORTANT: What is the mechanism for a “random bad measurement?”  We are keeping all of the headers returned in a “bad measurement.” Why would a host suddenly report a bad measurement?


Specify:
* Start time
* End time
* group by = hour, day, month

For each line, reports:
* start and end times
* # of queries
* # that were wrong, and %
* average offset
* stddev
* Regression of the points. We can calculate y=mx+b with a simple linear regression, but I want to report x=-b/m, which is the value of x when Y is 0. For the hosts that drift, this would be the time of the reboot, which is kind of neat.

Separately: I want to add the 0s to the graph, in a different color.

Bring back the hostname graph (as opposed to the IP address).  Have all IP addresses in slightly different colors.

I’m going to be refactoring the drawing program so that it’s a callable function in which I can specify all of those parameters. I think that I can get the drawing time down to less than a second for an IP address.

Sound good?