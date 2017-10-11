#!/usr/bin/python3

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

# Read the configuration file
def get_config(args):
    import configparser
    config = configparser.ConfigParser()
    config["mysql"] = {"host":"",
                       "user":"",
                       "passwd":"",
                       "port":DEFAULT_MYSQL_PORT,
                       "db":DEFAULT_MYSQL_DB,
                       "mysqldump":"mysqldump" }
    config.read(args.config)
    return config

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
