set -e

cd ../courtlistener
sudo apt install python2.7 python-pip
pip2 install django
python2 manage.py test cl/citations/tests.py
