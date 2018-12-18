set -e

cd ../courtlistener
sudo apt install python2.7 python-pip
python2 manage.py test cl/citations/tests.py
