#!/bin/bash
dig +short $1 
for i in 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0
  do
  for h in http 
  do
    echo -n "${h}://$1/  "
    echo -n `date`
    curl --insecure --silent --dump-header /tmp/x ${h}://$1 >/dev/null; grep Date /tmp/x
    sleep 1
  done
done
