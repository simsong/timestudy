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

def get_mysql_driver():
    """Return any MySQL driver that's installed"""
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

def get_mysql_config(fname=None):
    """Get a ConfigParser that's preped file a MySQL connections"""
    import configparser
    config = configparser.ConfigParser()
    config["mysql"] = {"host":"",
                       "user":"",
                       "passwd":"",
                       "port":DEFAULT_MYSQL_PORT,
                       "db":DEFAULT_MYSQL_DB,
                       "mysqldump":"mysqldump" }
    if fname:
        config.read(fname)
    return config


def mysql_dump(config):
    mc = config["mysql"]
    cmd = ['mysqldump','-h',mc['host'],'-u',mc['user'],'-p' + mc['passwd'], '-d',mc['db']]
    print(cmd)
    return subprocess.call(cmd)

class mysql:
    """Encapsulate a MySQL connection"""
    def __init__(self,config):
        self.mysql_config = config['mysql']
        self.conn = None

    def send_schema(self,schema):
        c = self.conn.cursor()
        for stmt in schema.split(";"):
            stmt = stmt.strip()
            if stmt:
                c.execute(stmt)

    def upgrade_schema(self):
        """Upgrade schema if necessary"""
        cursor = self.conn.cursor()
        res = cursor.execute("show tables like 'metadata'")
        if res:
            return
        print("Upgrading schema...")
        self.send_schema(open("schema_v1_v2.sql","r").read())

    def connect(self):
        self.mysql = get_mysql_driver()
        try:
            self.conn = self.mysql.connect(host=self.mysql_config["host"],
                                      port=int(self.mysql_config["port"]),
                                      user=self.mysql_config["user"],
                                      passwd=self.mysql_config['passwd'],
                                      db=self.mysql_config['db'])
            self.conn.cursor().execute("set innodb_lock_wait_timeout=20")
            self.conn.cursor().execute("SET tx_isolation='READ-COMMITTED'")
            self.conn.cursor().execute("SET time_zone = '+00:00'")
            self.upgrade_schema()
        except RuntimeError as e:
            print("Cannot connect to mysqld. host={} user={} passwd={} port={} db={}".format(
                self.mysql_config['host'],
                self.mysql_config['user'],
                self.mysql_config['passwd'],
                self.mysql_config['port'],
                self.mysql_config['db']))
            raise e

    def select(self,cmd,args=None):
        """execute an SQL command and return the cursor, which can be used as an iterator"""
        cursor = self.conn.cursor()
        cursor.execute(cmd,args)
        return cursor
    
    def select1(self,cmd,args=None):
        """execute an SQL command and return the first row"""
        cursor = self.select(cmd,args)
        return cursor.fetchone()

    def close(self):
        if self.conn:
            del self.conn           # delete the connection if it exists
            self.conn = None

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

