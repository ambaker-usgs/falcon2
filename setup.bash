#!/usr/bin/env bash
LQ_VERSION=3.5.3
PG_VERSION=42.1.1
VENV=venv
echo "Setting up virtualenv"
virtualenv -p python3 $VENV

echo "Downloading liquibase"
wget https://github.com/liquibase/liquibase/releases/download/liquibase-parent-$LQ_VERSION/liquibase-$LQ_VERSION-bin.tar.gz

echo "Setting up liquibase"
mkdir $VENV/liquibase
tar -xzf liquibase-$LQ_VERSION-bin.tar.gz -C $VENV/liquibase
rm liquibase-$LQ_VERSION-bin.tar.gz
ln -s ../liquibase/liquibase $VENV/bin/.

echo "Downloading postgres JDBC driver"
wget http://jdbc.postgresql.org/download/postgresql-$PG_VERSION.jar
mv postgresql-$PG_VERSION.jar $VENV/liquibase/lib/

source $VENV/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

