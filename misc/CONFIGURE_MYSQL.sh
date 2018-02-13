# Set up the Centos Database
# This should only be run once. It requires mysql to be installed and running
sudo mysql_secure_installation
echo run the following commands
echo "mysql -uroot -p<yourpassword> // create database timedb"
echo "mysql -uroot -p<yourpassword> timedb < ../schema.sql"
echo "mysql -uroot"
echo "GRANT ALL PRIVILEGES on timedb.* to dbuser@'localhost' IDENTIFIED BY '<dbuserpassword>';"
echo "FLUSH PRIVILEGES"

