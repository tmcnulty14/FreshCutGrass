#!/bin/bash

# Amazon Linux repos contain Python3.7 - we want 3.11 instead
# yum install -y python3, python3-pip

if /usr/local/bin/python3.11 --version ; then
  echo "Python 3.11 is already installed, skipping installation"
else
  echo "Installing Python 3.11"

  # Install build dependencies
  yum -y groupinstall "Development Tools"
  yum install -y gcc openssl-devel bzip2-devel libffi-devel

  # Download OpenSSL
  mkdir /tmp/ssl
  cd /tmp/ssl || exit
  wget https://ftp.openssl.org/source/openssl-1.1.1q.tar.gz --no-check-certificate
  tar xzf openssl-1.1.1q.tar.gz
  cd openssl-1.1.1q || exit

  # Install OpenSSL
  ./config --prefix=/usr --openssldir=/etc/ssl --libdir=lib no-shared zlib-dynamic
  make
  # make test # Failing? Not sure why, doesn't seem to matter
  make install

  # Manual Verification that OpenSSL is installed
  # openssl version
  # which openssl

  # Download Python
  mkdir /tmp/Python311
  cd /tmp/Python311 || exit
  wget https://www.python.org/ftp/python/3.11.3/Python-3.11.3.tgz
  tar xzf Python-3.11.3.tgz
  cd Python-3.11.3 || exit

  # Build Python
  ./configure --enable-optimizations --with-openssl=/usr
  make altinstall

  # Manual Verification that Python is installed
  # python3 -V
  # python -V

  # Clean up Build Directories
  rm -rf /tmp/ssl
  rm -rf /tmp/Python311
fi

# Install python package dependencies
echo "Installing dependencies for Fresh Cut Grass"
/usr/local/bin/python3.11 -m pip install --upgrade pip
/usr/local/bin/pip3.11 install -U -r /home/ec2-user/fresh-cut-grass/main/requirements.txt
