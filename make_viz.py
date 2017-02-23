import os
import subprocess
import shutil
from helpers import get_pg_config

### README ###

# This file generates a visualization of the current state of the capstone database,
# and publishes it to https://harvard-ftl-public.s3.amazonaws.com/capstone/capstone.html

# This depends on two packages being installed:
# sudo yum install postgresql_autodoc graphviz

# This assumes that get_pg_config() can load the postgres connection settings,
# and that writing to /mnt/harvard-ftl-public will write to the harvard-ftl-public bucket.


### CODE ###

config = get_pg_config()

# generate capstone.png using the postgresql_autodoc and doc commands
subprocess.call(['postgresql_autodoc', '-u', config['user'], '-d', config['dbname'], '--password='+config['password'], '-h', config['host'], '-t', 'dot'])
subprocess.call(['dot', '-Tpng', 'capstone.dot', '-o', 'capstone.png'])
os.remove('capstone.dot')

# retrieve count of rows in each table of the database
result = subprocess.check_output(['/usr/bin/psql', 'service=db', '-c',
                                  'SELECT schemaname,relname,n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;'],
                                 env = {'PGSERVICEFILE':'/ftldata/misc/pg.capstone.cnf'})

# write HTML file
with open('capstone.html', 'w') as out:
    out.write("""
        <html>
            <body>
                <p><img src='capstone.png'></p>
                <p><pre>%s</pre></p>
            </body>
        </html>
    """ % result.decode('utf8'))

# copy file to public s3 bucket
dest = "/mnt/harvard-ftl-public/capstone/"
for fname in ['capstone.png', 'capstone.html']:
    shutil.move(fname, os.path.join(dest, fname))