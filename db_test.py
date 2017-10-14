import py.test
import db

def test_get_mysql_driver():
    assert db.get_mysql_driver() != None

def test_get_mysql_config():
    config = db.get_mysql_config()
    assert int(config['mysql']['port']) == db.DEFAULT_MYSQL_PORT
    assert config['mysql']['db'] == db.DEFAULT_MYSQL_DB

def test_mysql():
    config = db.get_mysql_config("config.ini")
    d = db.mysql(config)
    d.connect()
    ver = d.mysql_version()
    assert type(ver)==str
    assert ver[0]>='5'
    assert 'DB' in ver
    

