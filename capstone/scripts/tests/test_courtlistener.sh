set -e

cd ../courtlistener
2to3 manage.py test cl/citations/
