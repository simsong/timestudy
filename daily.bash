#!/bin/bash
#
# Daily maintenance
make backup && mv database.sql.gz /var/www/html && sudo chcon -R -t httpd_sys_rw_content_t /var/www/html

