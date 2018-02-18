#!/usr/bin/python3

# 
# db.py:
# Code for working with the MySQL database

import os,sys,subprocess,time
if sys.version < '3':
    raise RuntimeError("Requires Python 3")


DEFAULT_CONFIG="config.ini"
DEFAULT_MYSQL_DB   = 'timedb'
DEFAULT_MYSQL_PORT = 3306
DEFAULT_MAX_EXECUTES = 0     # reconnect after 

SCHEMA = 'schema.sql'

# Common DB and Config Routines
# Find a MySQL driver..

USE_MYSQLDB=True
USE_PYMYSQL=False               # ran into error when rowid went larger than 65536

def file_contents(fname):
    return open(fname,"r").read()

def get_mysql_driver():
    """Return any MySQL driver that's installed"""
    try:
        import mysql.connector
        return mysql.connector
    except ImportError:
        pass

    try:
        if USE_MYSQLDB:
            import MySQLdb, _mysql_exceptions
            return MySQLdb
    except ImportError:
        pass

    try:
        if USE_PYMYSQL:
            import pymysql, pymysql.err
            return pymysql
    except ImportError:
        pass

    raise RuntimeError("Cannot find MySQL driver")

def get_mysql_config(fname=None):
    """Get a ConfigParser that's preped with the MySQL defaults"""
    import configparser
    config = configparser.ConfigParser()
    config.add_section('mysql')
    config['mysql'] = {"host":"",
                       "user":"",
                       "passwd":"",
                       "port":DEFAULT_MYSQL_PORT,
                       "db":DEFAULT_MYSQL_DB,
                       "mysqldump":"mysqldump",
                       "debug":0
    }
    if fname:
        config.read(fname)
    return config


def mysql_dump_stdout(config,opts):
    """Using the config, dump MySQL schema"""
    mc = config["mysql"]
    cmd = ['mysqldump','-h',mc['host'],'-u',mc['user'],'-p' + mc['passwd'], opts,mc['db']]
    sys.stderr.write(" ".join(cmd)+"\n")
    subprocess.call(cmd)

class mysql:
    """Encapsulate a MySQL connection"""
    def __init__(self,config):
        self.config        = config
        self.conn          = None
        self.execute_count = 0  # count number of executes
        self.mysql_max_executes = DEFAULT_MAX_EXECUTES
        self.debug         = config.getint('mysql','debug')
        self.null          = config.getboolean('mysql','null', fallback=False) #  are we using the null driver?
        self.execute_total  = 0  # running total of how long each execute took
        self.execute_last = 0

    def connect(self):
        if self.null: return
        self.mysql = get_mysql_driver()
        try:
            self.conn = self.mysql.connect(host=self.config.get("mysql","host"),
                                           port=self.config.getint("mysql",'port'),
                                           user=self.config.get("mysql","user"),
                                           passwd=self.config.get("mysql","passwd"),
                                           db=self.config.get("mysql","db"))
            self.conn.cursor().execute("set innodb_lock_wait_timeout=20")
            self.conn.cursor().execute("SET tx_isolation='READ-COMMITTED'")
            self.conn.cursor().execute("SET time_zone = '+00:00'")

        except RuntimeError as e:
            print("Cannot connect to mysqld. host={} user={} passwd={} port={} db={}".format(
                self.config.get('mysql','host'),
                self.config.get('mysql','user'),
                self.config.get('mysql','passwd'),
                self.config.get('mysql','port'),
                self.config.get('mysql','db')))
            raise e

    def table_exists(self,tablename):
        """Return true if tablename is a real table"""
        cursor = self.conn.cursor()
        cursor.execute("show tables like %s",(tablename,))
        res = cursor.fetchall()
        return True if res else False

    def send_schema(self,schema):
        c = self.conn.cursor()
        for stmt in schema.split(";"):
            stmt = stmt.strip()
            if stmt:
                c.execute(stmt)

    def mysql_version(self):
        if self.null: return '5.0.0-NULL'
        return self.select1("select version();")[0]

    def execute(self,cmd,args=None):
        """Execute an SQL command and return the cursor, which can be used as an iterator.
        Connect to the database if necessary."""
        import mysql.connector.errors
        if self.null:
            if self.debug:
                print("null.execute({})   PID:{} ".format(cmd % args,os.getpid()))
            return
        self.execute_count += 1
        if self.mysql_max_executes and self.execute_count > self.mysql_max_executes:
            self.close()        # close out and reconnect
        if not self.conn:
            self.connect()
        if self.debug:
            try:
                if '%s' in cmd:
                    print("db.execute({})   PID:{} ".format(cmd % args,os.getpid()),end='')
                else:
                    assert (args==None)
                    print("db.execute({})   PID:{} ".format(cmd,os.getpid()),end='')
            except TypeError as e:
                print("cmd=",cmd)
                print("args=",args)
                raise e
        self.t0 = time.time()
        cursor = self.conn.cursor()
        try:
            cursor.execute(cmd,args)
        except mysql.connector.errors.ProgrammingError as e:
            print("")
            print("*** MySQL Programming Error ***")
            print("cmd=",cmd)
            print("args=",args)
            raise e
        self.t1 = time.time()
        self.execute_last = self.t1-self.t0
        self.execute_total += self.execute_last
        if self.debug:
            print("t={:.3f}".format(self.execute_last))
        return cursor
    
    def select1(self,cmd,args=None):
        """execute an SQL command and return the first row"""
        if self.null: return (None,)
        cursor = self.execute(cmd,args) # debug handled by execute()
        return cursor.fetchone()

    def commit(self):
        if self.null:  return
        if self.debug: print("db.COMMIT   PID:{}".format(os.getpid()))
        self.conn.commit()

    def log(self,msg,level='INFO'):
        """Save msg in the log table, return the log id"""
        c = self.execute("INSERT INTO log (pid,level,value) VALUES (%s,%s,%s)",(os.getpid(),level,msg))
        self.conn.commit()
        return c.lastrowid

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
    parser.add_argument('--config',help='specify config file',default=DEFAULT_CONFIG)
    parser.add_argument("--dumpschema",action='store_true',help="dump schema to stdout")
    parser.add_argument("--dumpdb",action='store_true',help="dump schema to stdout")

    args = parser.parse_args()
    config = get_mysql_config(args.config)

    if args.dumpschema:
        mysql_dump_stdout(config,'-d')

    if args.dumpdb:
        mysql_dump_stdout(config,'-q')

