# Configure CENTOS as necessary for Simson and this package
# Designed to be run on a clean VM
sudo yum -y install git         # you probably already did this
sudo yum -y update
sudo yum -y makecache fast 
sudo yum -y install deltarpm yum-cron
sudo yum -y install emacs
sudo yum -y install zlib zlib-static

sudo yum -y install mariadb mariadb-server mariadb-devel mariadb-libs 
sudo yum -y install httpd
sudo yum -y install gcc
sudo yum -y groupinstall 'Development Tools'
sudo systemctl start mariadb
sudo systemctl status mariadb
sudo systemctl enable mariadb

## Now figure out how to install Python3
if grep Amazon /etc/system-release ; then
  sudo amazon-linux-extras install python3=lates
else
  # Install Python3 from EPEL Repository
  # http://ask.xmodulo.com/install-python3-centos.html
  # It only has Python3.4! Ick. 
  sudo yum install -y epel-release
  sudo yum install -y python34 python34-pytest python34-setuptools python34-scipy python34-requests python34-pytz python34-tkinter python34-pip

  # Oh, this works better; it gets python3.6
  # https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-local-programming-environment-on-centos-7
  # sudo yum -y install https://centos7.iuscommunity.org/ius-release.rpm
  # sudo yum -y install python36u
fi

# Fix Python3 release
sudo pip3 install --upgrade pip
sudo pip3 install matplotlib pytest bs4 lxml dnspython pytest requests
  # https://stackoverflow.com/questions/46215390/unable-to-find-protobuf-include-directory-when-i-use-pip-install-mysql-connec
sudo pip3 install mysql-connector==2.1.4


# Fix for selinux
# https://serverfault.com/questions/322117/selinux-letting-apache-talk-to-mysql-on-centos
sudo setsebool -P httpd_enable_cgi 1
sudo setsebool -P httpd_can_network_connect 1
