#!/bin/bash
echo "Installing dependencies for Fresh Cut Grass"

# Installing Python3 manually to get 3.9 instead of 3.7
# yum install -y python3, python3-pip

# Install build dependencies
yum -y groupinstall "Development Tools"
yum install -y gcc openssl-devel bzip2-devel libffi-devel

# Download Python
cd /opt || exit
wget https://www.python.org/ftp/python/3.9.6/Python-3.9.6.tgz
tar xzf Python-3.9.6.tgz

# Build Python
cd Python-3.9.6 || exit
./configure --enable-optimizations
make altinstall

rm -f /opt/Python-3.9.6.tgz

# Install python package dependencies
/usr/local/bin/python3.9 -m pip install --upgrade pip
/usr/local/bin/pip3.9 install -U discord discord.py discord-py-interactions discord-py-slash-command python-dateutil python-dotenv regex typing-extensions
