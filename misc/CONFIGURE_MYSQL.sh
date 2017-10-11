# Set up the Centos Databse
sudo mysql_secure_installation
echo run the following commands
echo "mysql -uroot -p<yourpassword> timedb < schema.sql"
echo "mysql -uroot"
echo "GRANT ALL PRIVILEGES on timedb.* to dbuser@'localhost' IDENTIFIED BY '<dbuserpassword>';"

