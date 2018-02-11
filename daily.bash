#!/bin/bash
#
# Daily maintenance
make backup && mv database.sql.gz /var/www/html && chcon -t httpd_sys_rw_content_t /var/www/html/database.sql.gz

