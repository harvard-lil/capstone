set -e

cd ../courtlistener
sudo pip2 install django celery git+https://github.com/freelawproject/judge-pics
python2 manage.py test cl/citations/tests.py
