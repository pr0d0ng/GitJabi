#!/bin/bash

# * 초기 인프라 자동 구축
#
# Ubuntu 24.04에서 사용되었습니다.
#
echo Updating system...
sudo apt update
sudo apt upgrade -y

echo Installing git...
sudo apt install git -y

echo Installing python ...
sudo apt install python3 python3-pip python3-venv -y
sudo apt install python3.12 python3.12-venv python3.12-distutils python3-pip -y

echo Fetching PIP...
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.12

echo Creating a virtual env...
sudo python3 -m venv .venv

echo Starting to install requirements libraries...
source .venv/bin/activate
pip install --upgrade pip
pip install -r ./src/app/requirements.txt

deactivate

echo End of task.