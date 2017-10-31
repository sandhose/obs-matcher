OBS-Matcher
===========

## Dependencies
* python3
* python3-dev
* python3-venv
* libpq-dev
* git
* build-essential

## Install

### Debian
```bash
git clone https://github.com/sandhose/obs-matcher
cd obs-matcher
virtualenv venv
source venv/bin/activate
python3 setup.py develop
```

#### Create Postgresql Database
```bash
sudo -u postgres psql
CREATE DATABASE matcher
GRANT ALL PRIVILEGES ON DATABASE matcher TO user
```
Ctrl+D

```bash
matcher db upgrade
matcher runserver
```
