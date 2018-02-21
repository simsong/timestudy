import os
import py.test
import db
from db import SCHEMA

# Set this to be a config.ini that has a working "testdb"
CONFIG_INI_TEST="config_test.ini"

def get_test_database():
    assert os.path.exists(CONFIG_INI_TEST)
    config = db.get_mysql_config(CONFIG_INI_TEST)
    assert config.get('mysql','db') != config.get('mysql','testdb')
    dbc = db.mysql(config)
    dbc.connect(db=config.get('mysql','testdb'))
    return dbc

def test_create_schema():
    """Test creating a database and upgrading it and killing it"""
    config = db.get_mysql_config(CONFIG_INI_TEST)
    dbc = get_test_database()

    # 
    # Make sure that we are in the correct database
    #
    assert dbc.select1("select database();")[0]==config.get('mysql','testdb')

    # Make sure that log and metadata tables are not present
    dbc.execute("DROP TABLE IF EXISTS `metadata`")
    dbc.execute("DROP TABLE IF EXISTS `log`")

    # 
    # Send the schema
    #
    dbc.send_schema(db.file_contents(SCHEMA))

    assert dbc.table_exists('dated')==True
    assert dbc.table_exists('xxx')==False

def test_get_mysql_driver():
    assert db.get_mysql_driver() != None

def test_get_mysql_config():
    config = db.get_mysql_config()
    assert int(config['mysql']['port']) == db.DEFAULT_MYSQL_PORT
    assert config['mysql']['db'] == db.DEFAULT_MYSQL_DB

def test_mysql():
    dbc = get_test_database()
    ver = dbc.mysql_version()
    assert type(ver)==str
    assert ver[0]>='5'
    
def test_log():
    dbc = get_test_database()
    id = dbc.log("This is PID {}".format(os.getpid()))
    assert id>0

if __name__=="__main__":
    test_create_schema()
