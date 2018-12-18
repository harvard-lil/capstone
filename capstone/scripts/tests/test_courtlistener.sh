set -e

cd ../courtlistener
python2 manage.py test cl/citations/tests.py
