#!/bin/bash
dig +short $1 
for i in 1 2 3 4 5
  do
  for h in http https 
  do
    echo -n "${h}://$1/  "
    curl --insecure --silent --dump-header /tmp/x ${h}://$1 >/dev/null; grep Date /tmp/x
  done
done
