import os
import csv
import paramiko
from capi_project.models import Case
from paramiko import SSHClient
from scp import SCPClient
from capi_project import settings

def create_metadata_from_csv():
    csv_doc = settings.METADATA_FILE_PATH
    if os.path.exists(csv_doc):
        with open(csv_doc, 'rb') as f:
            reader = csv.DictReader(f)
            try:
                map(Case.create_from_row, reader)
            except Exception as e:
                print "Error on metadata row creation:", e
                pass
        os.remove(csv_doc)

def format_filename(case_id):
    cdir, cpgnumber = case_id.split('_')
    cdirname = cdir + '_redacted'
    return settings.CAP_DATA_DIR_VAR + '/' + cdirname+'/casemets/' + cdirname + '_CASEMETS_' + cpgnumber + settings.CASE_FILE_TYPE

def scp_get(requester_id, list_of_files):
    try:
        ssh = SSHClient()
        list_of_files = map(format_filename, list_of_files)
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        private_key = paramiko.RSAKey.from_private_key_file(settings.PRIVATE_KEY_FILENAME)
        ssh.connect(settings.CAP_SERVER_TO_CONNECT_TO, port=22, pkey=private_key, username='capuser')
        stdin, stdout, stderr = ssh.exec_command("sleep 5; echo working!!!")
        print(stdout.read())
        string_list = str(list_of_files)
        zip_file_name = "%s_files.zip" % requester_id
        ssh.exec_command("touch %s" % zip_file_name)
        stdin, stdout, stderr = ssh.exec_command('python testing_gzip.py %s \"%s\"' % (zip_file_name, string_list))
        if stderr.read():
            raise Exception('Uh Oh! Something went wrong')
        scp_client = SCPClient(ssh.get_transport())
        scp_client.get("%s" % zip_file_name)

        scp_client.close()
    except Exception as e:
        return e

if __name__ == '__main___':
    create_metadata_from_csv()
