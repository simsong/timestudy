# Configure CENTOS as necessary for Simson and this package
# Designed to be run on a clean VM
sudo yum -y makecache fast 
sudo yum -y install deltarpm yum-cron
sudo yum -y install emacs
sudo yum -y install zlib zlib-static
# Making it work with sqlite3 is harder than just installing MySQL
sudo yum -y install mariadb mariadb-server mariadb-devel mariadb-libs MySQL-python
sudo yum -y install httpd
sudo systemctl start mariadb
sudo systemctl status mariadb
sudo systemctl enable mariadb

# Install Python3 from EPEL Repository
# http://ask.xmodulo.com/install-python3-centos.html
# It only has Python3.4! Ick. 
sudo yum install -y epel-release
sudo yum install -y python34 python34-pytest python34-setuptools python34-scipy
sudo pip3 install matplotlib

# Set up the Centos Databse
sudo mysql_secure_installation
echo run the following commands
echo "mysql -uroot -p<yourpassword> timedb < schema.sql"
echo "mysql -uroot"
echo "GRANT ALL PRIVILEGES on timedb.* to dbuser@'localhost' IDENTIFIED BY '<dbuserpassword>';"

