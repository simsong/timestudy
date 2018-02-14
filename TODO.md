Real time reports:
Proposal is for a CGI script that displays a form if called without arguments, otherwise just performs the search.

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