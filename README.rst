OBS-Matcher
===========

Dependencies
------------
* python3
* python3-dev
* python3-venv
* libpq-dev
* git
* build-essential
* postgresql

Install
-------

* Unix
```bash
git clone https://github.com/sandhose/obs-matcher
cd obs-matcher
virtualenv venv
source venv/bin/activate
python3 setup.py install
python3 setup.py develop
```

* Create Postgresql Database
```bash
# You may need to create the postgresql database before all :
#sudo su - postgres -c "initdb --locale en_US. UTF-8 -D 'var/lib/postgres/data'"
systemctl start postgresql
sudo -u postgres psql
>>> CREATE ROLE "user" INHERIT LOGIN;
>>> CREATE DATABASE matcher;
>>> GRANT ALL PRIVILEGES ON DATABASE matcher TO "user";
Ctrl+D
# Upgrade database i
matcher db upgrade
# Run server
matcher runserver
```

Usage
-----

```bash
# Initiate virtualenv
source venv/bin/activate
# Run local server
matcher runserver
# Delete object entries (not the platforms)
matcher nuke
```

Documentation
-------------

```bash
# Compile documentation
cd doc
make html
```
* Browse to /path/to/obs-matcher/doc
