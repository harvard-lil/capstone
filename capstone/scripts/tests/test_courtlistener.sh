set -e

cd ../courtlistener
sudo pip2 install django celery
python2 manage.py test cl/citations/tests.py
