#!/usr/bin/env python3
#
# Print stats about the system
#
import db
import os
import tabulate

CONFIG_INI = "config.ini"

def query(dbc,cmd,desc=None):
    c = dbc.execute(cmd)
    field_names = [i[0] for i in c.description]
    headers = field_names
    content = c.fetchall()
    print(tabulate.tabulate(content,headers=headers))
    #print(tabulate.tabulate([headers],content))
    
if __name__=="__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config",help="config file",default=CONFIG_INI)
    args = parser.parse_args()
    if not os.path.exists(args.config):
        raise RuntimeError("{} does not exist; specify config file with --config FILENAME".
                           format(args.config))
    config = db.get_mysql_config(args.config)       # prep it with default MySQL parameters
    if config.getint('mysql','debug'):
        args.debug = 1          # override
    dbc = db.mysql(config)
    query(dbc,"select * from log where level='ERR' order by modified desc limit 10")
    query(dbc,"select * from log where level='INFO' order by modified desc limit 10")
    exit(1)
    query(dbc,"select host,offset,qdatetime,ipaddr,cname from times order by qdatetime desc limit 10","Last 10 bad times:")
    query(dbc,"select host,qdate,qlast,ipaddr,qcount,ecount,wtcount from dated order by qdate desc,qlast desc limit 10","Last 10 queried")
    


