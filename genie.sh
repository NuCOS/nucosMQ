#!/bin/bash
VENV=./venv
if [ -d "$VENV" ]; then
  echo "remove virtual env first"
  sleep 2
  rm -rf "$VENV"
fi


###################################
echo "----------------------------------------------------"
virtualenv -p $(which python3) $VENV/py3
source $VENV/py3/bin/activate
pip install --upgrade pip
pip install nose2
python setup.py sdist
###################################
echo "----------------------------------------------------"
sleep 1
echo "python used: "
which python
python info.py
###################################
echo "----------------------------------------------------"
sleep 1
echo "now install the nucosMQ in python 3"
python setup.py install
####################################
echo "----------------------------------------------------"
sleep 1
echo "now run test in py3"
nose2 --plugin nose2.plugins.junitxml --junit-xml
#mv nose2-junit.xml nose2-py3.xml
python aftermath.py nose2-junit.xml py3
echo "test done in:"
python info.py
sleep 3

deactivate
echo "after deactivate"
python info.py
sleep 3
###################################
echo "----------------------------------------------------"
virtualenv -p $(which python) venv/py2
source $VENV/py2/bin/activate
pip install --upgrade pip
pip install nose2
python setup.py sdist
###################################
echo "----------------------------------------------------"
sleep 1
echo "python used: "
which python
python info.py
###################################
echo "----------------------------------------------------"
sleep 1
echo "now install the nucosMQ"
python setup.py install
####################################
echo "----------------------------------------------------"
sleep 1
echo "now run test in py2"
nose2 --plugin nose2.plugins.junitxml --junit-xml
#mv nose2-junit.xml nose2-py2.xml
python aftermath.py nose2-junit.xml py2
echo "test done in:"
python info.py
sleep 3


#sleep 2
#echo "deactivate"
#deactivate
