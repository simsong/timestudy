#!/usr/bin/python3

# 
# db.py:
# Code for working with the MySQL database

import sys
if sys.version < '3':
    raise RuntimeError("Requires Python 3")


DEFAULT_MYSQL_DB   = 'timedb'
DEFAULT_MYSQL_PORT = 3306

# Common DB and Config Routines

# Find a MySQL driver..


def get_mysql():
    try:
        import pymysql, pymysql.err
        return pymysql
    except ImportError:
        pass

    try:
        import MySQLdb, _mysql_exceptions
        return MySQLdb
    except ImportError:
        pass

    raise RuntimeError("Cannot find MySQL driver")

def mysql_prep(config):
    """Prep the config file for the MySQL section"""
    config["mysql"] = {"host":"",
                       "user":"",
                       "passwd":"",
                       "port":DEFAULT_MYSQL_PORT,
                       "db":DEFAULT_MYSQL_DB,
                       "mysqldump":"mysqldump" }


def mysql_connect(config):
    mysql = get_mysql()
    mc = config['mysql']
    try:
        conn = mysql.connect(host=mc["host"],port=int(mc["port"]),user=mc["user"],
                               passwd=mc['passwd'],db=mc['db'])
        conn.cursor().execute("set innodb_lock_wait_timeout=20")
        conn.cursor().execute("SET tx_isolation='READ-COMMITTED'")
        conn.cursor().execute("SET time_zone = '+00:00'")
        upgrade_schema(conn)
        return conn
    except RuntimeError as e:
        print("Cannot connect to mysqld. host={} user={} passwd={} port={} db={}".format(
            mc['host'],mc['user'],mc['passwd'],mc['port'],mc['db']))
        raise e
    
def send_schema(conn,schema):
    c = conn.cursor()
    for stmt in schema.split(";"):
        stmt = stmt.strip()
        if stmt:
            c.execute(stmt)

def upgrade_schema(conn):
    """Upgrade schema if necessary"""
    cursor = conn.cursor()
    res = cursor.execute("show tables like 'metadata'")
    if res:
        return
    print("Upgrading schema...")
    send_schema(conn,open("schema_v1_v2.sql","r").read())

def mysql_stats(c):
    global max_id
    c = conn.cursor()
    if args.debug: 
        print(time.asctime())
    for table in ["times","dated"]:
        c.execute("select count(*) from "+table)
        p = c.fetchone()[0]
        if table not in start_rows:
            print("Start Rows in {}: {:,}".format(table,p))
        else:
            print("End Rows in {}: {:,} ({:,} new)".format(table,p,p-start_rows[table]))
        start_rows[table] = p

    c.execute("select max(id) from dated")
    max_id = c.fetchone()[0]
        
    if args.debug:
        print("New dated rows:")
        c.execute("select * from dated where id>%s",(max_id,))
        for row in c.fetchall():
            print(row)

def mysql_dump(config):
    mc = config["mysql"]
    cmd = ['mysqldump','-h',mc['host'],'-u',mc['user'],'-p' + mc['passwd'], '-d',mc['db']]
    print(cmd)
    subprocess.call(cmd)
    exit(0)
    


if __name__=="__main__":
    import argparse
    import configparser
    import sys

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--config',help='specify config file')
    parser.add_argument("--dumpschema",action="store_true")

    args = parser.parse_args()

    import configparser 
    config = configparser.ConfigParser() # create a config parser
    db.mysql_prep(config)                # prep it with default MySQL parameters
    config.read(args.config)             # read the config file

    if args.dumpschema:
        mysql_dumpschema(config)

