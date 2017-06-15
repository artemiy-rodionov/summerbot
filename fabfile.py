from fabric.api import *


env.use_ssh_config = True
env.hosts = ["snalg1"]


folder = '/home/snoopt/summer'



def deploy():
    local('git archive -o /tmp/latest.zip HEAD')
    with cd(folder):
        put('/tmp/latest.zip', folder)
        run('unzip latest.zip')
        run('./venv3/bin/pip install -r requirements.txt')
    sudo('supervisorctl restart summer_bot')
    local('rm /tmp/latest.zip')
