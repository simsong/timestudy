#!/bin/bash
#
# Daily maintenance
source config.bash
make pub
make backup && mv database.sql.gz /var/www/html 
sudo chcon -R -t httpd_sys_rw_content_t /var/www/html

