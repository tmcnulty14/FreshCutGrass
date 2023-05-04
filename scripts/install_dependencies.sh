#!/bin/bash

# Installing Python3 manually to get 3.11 instead of 3.7
# yum install -y python3, python3-pip

if /usr/local/bin/python3.11 --version ; then
  echo "Python 3.11 is already installed, skipping installation"
else
  echo "Installing Python 3.11"

  # Install build dependencies
  yum -y groupinstall "Development Tools"
  yum install -y gcc openssl-devel bzip2-devel libffi-devel

  # Download Python
  cd /opt || exit
  wget https://www.python.org/ftp/python/3.11.3/Python-3.11.3.tgz
  tar xzf Python-3.11.3.tgz

  # Build Python
  cd Python-3.11.3 || exit
  ./configure --enable-optimizations
  make altinstall

  rm -f /opt/Python-3.11.3.tgz
fi

# Install python package dependencies
echo "Installing dependencies for Fresh Cut Grass"
/usr/local/bin/python3.11 -m pip install --upgrade pip
/usr/local/bin/pip3.11 install -U -r /home/ec2-user/fresh-cut-grass/main/requirements.txt
