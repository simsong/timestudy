#!/bin/bash
#
# Daily maintenance
source config.bash
make pub
make backup && mv database.sql.gz /var/www/html 

sestatus=`/usr/sbin/sestatus | grep SELinux.status | awk '{print $3;}'`
if [ $sestatus = 'enabled' ]; then
  sudo chcon -R -t httpd_sys_rw_content_t /var/www/html
fi

