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
sudo yum install -y python34 python34-pytest python34-setuptools python34-scipy python34-requests python34-pytz
sudo pip install --upgrade pip
sudo pip3 install --upgrade pip3
sudo pip3 install matplotlib pytest bs4 lxml PyMySQL3
sudo pip3 install pytest

# Oh, this works better; it gets python3.6
# https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-local-programming-environment-on-centos-7
# sudo yum -y install https://centos7.iuscommunity.org/ius-release.rpm
# sudo yum -y install python36u

