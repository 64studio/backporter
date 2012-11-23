* Install dependencies

sudo apt-get install apache2 cowbuilder devscripts mini-dinstall rebuildd reprepro

* Set up apt user and local repository

sudo adduser --system --home /srv/apt --group apt

sudo mkdir -p /srv/apt/backports/conf

sudo mkdir -p /srv/apt/backports/incoming

* Configure reprepro

sudo nano /srv/apt/backports/conf/distributions

sudo nano /srv/apt/backports/conf/incoming

* Allow backporter group members to dput source packages

sudo addgroup backporter

sudo adduser apt backporter

sudo adduser myusername backporter

sudo chown -R apt.backporter /srv/apt/backports

chmod -R 775 /srv/apt/backports/incoming

nano ~/.dput.cf

* Set up crontab for reprepro, and duplicate existing gnupg archive signing key

sudo su apt

	crontab -e

	cd /srv/apt/

	scp !myusername@example.com:/srv/apt/gnupg-backup.tar.gz .

	chmod 600 gnupg-backup.tar.gz

	tar -xvzf gnupg-backup.tar.gz

	exit	

* Set up Apache
 
sudo nano /etc/apache2/conf.d/apt.conf

sudo /etc/init.d/apache2 reload

* Configure and init cowbuilder

sudo nano /etc/rebuildd/rebuilddrc

(Add COMPONENT="main universe" if building on Ubuntu, because cowdancer is in universe)

sudo cowbuilder --create

* Configure and init rebuildd

sudo nano /etc/default/rebuildd

sudo nano /etc/rebuildd/rebuilddrc

sudo nano /etc/rebuildd/maintenance/00_update_build_system

sudo rebuildd init

sudo rebuildd-init-build-system

sudo /etc/init.d/rebuildd start

sudo /etc/init.d/rebuildd-httpd start

telnet localhost 9999

sudo apt-get install build-essential cdbs debhelper docbook-xsl dpkg-buildpackage dpkg-dev fakeroot git-core python2.6 python-pysqlite2

mkdir -p ~/git

cd ~/git

git clone git://git.64studio.com/backporter.git

cd backporter

* Build and install the backporter package

dpkg-buildpackage -b -us -uc

cd ..

sudo dpkg -i backporter_0.1_all.deb
