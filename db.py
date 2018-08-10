#!/usr/bin/python3

# 
# db.py:
# Code for working with the MySQL database

import os
import sys
import subprocess
import time
import socket
if sys.version < '3':
    raise RuntimeError("Requires Python 3")


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

def loadavg():
    return float(open("/proc/loadavg").read().split(" ",maxsplit=1)[0])

def meminfo():
    data = open("/proc/meminfo","r").read().split("\n")
    return dict([(e[0],int(e[1].strip().split(' ')[0])) for e in [line.split(":") for line in data if ":" in line]])

def log_var_names():
    return ["host","pid","cpu","memtotal","memfree"]

def log_vars():
    mem = meminfo()
    return [socket.gethostname(),os.getpid(),loadavg(),mem['MemTotal'],mem['MemFree']]

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

def make_config_ro(config):
    """Copy the user information to the ro user"""
    if config['mysql']['ro_user']=='':
        raise RuntimeError("No ro_user in config file...")
    config['mysql']['user']   = config['mysql']['ro_user']
    config['mysql']['passwd'] = config['mysql']['ro_passwd']

def get_mysql_config(fname=None,mode='rw'):
    """Get a ConfigParser that's preped with the MySQL defaults. If mode=='ro', then use the ro_user and ro_passwd"""
    import configparser
    config = configparser.ConfigParser()
    config.add_section('mysql')
    config['mysql'] = {"host":"",
                       "user":"",
                       "passwd":"",
                       'ro_user':'',
                       'ro_passwd':'',
                       "port":DEFAULT_MYSQL_PORT,
                       "db":DEFAULT_MYSQL_DB,
                       "mysqldump":"mysqldump",
                       "debug":0
    }
    if fname:
        config.read(fname)
    if mode!='ro':
        config['mysql']['user']   = config['mysql']['ro_user']
        config['mysql']['passwd'] = config['mysql']['ro_passwd']
    return config

def mysql_dump_stdout(config,opts):
    """Using the config, dump MySQL schema"""
    user = config["mysql"]['user']
    password = config["mysql"]['passwd']
    cmd = ['mysqldump','--skip-lock-tables',
           '-h',config['mysql']['host'],'-u',user,'--pass=' + password, opts, config['mysql']['db']]
    sys.stderr.write(" ".join(cmd)+"\n")
    subprocess.call(cmd)

class mysql:
    """Encapsulate a MySQL connection"""
    def __init__(self,config,mode='rw'):
        self.config        = config
        if mode=='ro':
            make_config_ro(self.config)
        self.conn          = None
        self.execute_count = 0  # count number of executes
        self.mysql_max_executes = DEFAULT_MAX_EXECUTES
        self.debug         = config.getint('mysql','debug')
        self.null          = config.getboolean('mysql','null', fallback=False) #  are we using the null driver?
        self.execute_total  = 0  # running total of how long each execute took
        self.execute_last = 0

    def connect(self,db=None):
        if self.null: return
        self.mysql = get_mysql_driver()
        if db==None:
            db = self.config.get("mysql","db")
        try:
            self.conn = self.mysql.connect(host=self.config.get("mysql","host"),
                                           port=self.config.getint("mysql",'port'),
                                           user=self.config.get("mysql",'user'),
                                           passwd=self.config.get("mysql",'passwd'),
                                           db=db)
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

    def log(self,value,level='INFO'):
        """Save value in the log table, return the log id"""
        vars = log_var_names() + ["level","value"]
        vals = log_vars() + [level,value]
        assert len(vars) == len(vals)
        plac = ",".join(["%s"] * len(vars))
        c = self.execute("INSERT INTO log (" + ",".join(vars) +" ) VALUES ( " + plac + " )",vals)
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
    parser.add_argument('--config',help='specify config file',required=True)
    parser.add_argument("--dumpschema",action='store_true',help="dump schema to stdout")
    parser.add_argument("--dumpdb",action='store_true',help="dump schema to stdout")
    parser.add_argument("--debuglog",action='store_true')

    args = parser.parse_args()
    config = get_mysql_config(args.config)

    if args.debuglog:
        print(log_vars())
        print(log_var_names())

    if args.dumpschema:
        mysql_dump_stdout(config,'-d')

    if args.dumpdb:
        mysql_dump_stdout(config,'-q')

