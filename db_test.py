import py.test
import db
from db import SCHEMA

def test_create_schema():
    """Test creating a database and upgrading it and killing it"""
    config = db.get_mysql_config("config.ini")
    testdb = config.get('mysql','testdb')

    assert config.get('mysql','db') != testdb # make sure that a different testdb was set

    # change the db to the test db
    config.set('mysql','db',testdb)

    mdb    = db.mysql( config )
    mdb.connect()

    # 
    # Make sure that we are in the correct database
    #
    assert mdb.select1("select database();")[0]==testdb

    # Make sure that log and metadata tables are not present
    mdb.execute("DROP TABLE IF EXISTS `metadata`")
    mdb.execute("DROP TABLE IF EXISTS `log`")

    # 
    # Send each schema
    #
    mdb.send_schema(db.file_contents(SCHEMA[0]))

    assert mdb.table_exists('dated')==True
    assert mdb.table_exists('xxx')==False

    # Upgrade the schema
    mdb.upgrade_schema()
    
    # 
    # Show that the second schema is present
    assert mdb.table_exists('metadata')==True
    assert mdb.select1("select value from metadata where name='schema';")[0]=='1'


def test_get_mysql_driver():
    assert db.get_mysql_driver() != None

def test_get_mysql_config():
    config = db.get_mysql_config()
    assert int(config['mysql']['port']) == db.DEFAULT_MYSQL_PORT
    assert config['mysql']['db'] == db.DEFAULT_MYSQL_DB

def test_mysql():
    mdb    = db.mysql( db.get_mysql_config("config.ini") )
    mdb.connect()
    ver = mdb.mysql_version()
    assert type(ver)==str
    assert ver[0]>='5'
    assert 'DB' in ver
    

