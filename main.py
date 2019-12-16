import requests
import sys
import os
import yaml
import copy
import json


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RED = "\033[1;31m"
    BLUE = "\033[1;34m"
    CYAN = "\033[1;36m"
    GREEN = "\033[0;32m"
    RESET = "\033[0;0m"
    REVERSE = "\033[;7m"


def find_ressource_index(ressources, value_to_find):
    for i, ressource in enumerate(ressources):
        if ressource['name'] == value_to_find:
            return i
    return -1


def main():
    # Definition des variablies provenant de l'environnement
    project = os.getenv('PROJECT')
    git_type = os.getenv('GIT_TYPE')
    git_api = os.getenv('GIT_API')
    repo = os.getenv('REPO')
    ressource_to_replace = os.getenv('REPLACED_RESSOURCE')
    out_folder = os.getenv('OUT_FOLDER')
    pipeline_file = os.pardir + '/' + os.getenv('PIPELINE_FILENAME')
    try:
        username = os.getenv('API_USERNAME')
        password = os.getenv('API_PASSWORD')
    except:
        username = ""
        password = ""

    # Ouverture du fichier de configuration de pipeline
    print(bcolors.HEADER + 'Opening the file {} to replace the ressource : {}'.format(
        pipeline_file, ressource_to_replace) + bcolors.ENDC)

    with open(pipeline_file, 'r') as f:
        template_yml = yaml.load(f, Loader=yaml.FullLoader)

    # Definition de la variable contenant le nouveau pipeline
    new_yaml = copy.deepcopy(template_yml)
    new_yaml['jobs'] = []

    # Recuperation des branches du repo
    print(bcolors.UNDERLINE + 'Gathering branch info from repository' + bcolors.ENDC)
    if username != "" and password != "":
        res = requests.get(
            git_api, auth=requests.auth.HTTPBasicAuth(username, password))
    else:
        res = requests.get(git_api)
    if(res.status_code != 200):
        print(bcolors.FAIL + 'Error with branches gathering request' + bcolors.ENDC)
        print(res.json())
        sys.exit(1)
    j = res.json()
    if git_type == 'bitbucket':
        j = j['values']

    # Recuperation de l'index de la ressource que l'on veut remplacer
    ressource_i = find_ressource_index(
        template_yml['resources'], ressource_to_replace)
    if(ressource_i == -1):
        print(bcolors.FAIL +
              'Ressource that needs to be changed doesn\'t exist' + bcolors.ENDC)

    # Configuration de chacun des ligne de pipeline pour chaque branche
    for branch_info in j:
        # Definition du nom de la branche selon le type de repo

        if git_type == 'bitbucket':
            branch_id = 'displayId'

        else:
            branch_id = 'name'

        branch_name = branch_info[branch_id]
        print(bcolors.BLUE +
              'Creating job for branch name : {}'.format(branch_name) + bcolors.ENDC)

        # Verification si la ressource a changer existe, sinon prendre la ressource par defaut
        if ressource_i == -1:
            ressource_position = find_ressource_index(
                template_yml['resources'], 'git-master')
        else:
            ressource_position = ressource_i

        # Verifier si la ressource existe deja
        temp_check = find_ressource_index(
            template_yml['resources'], 'git-{}'.format(branch_name))
        if temp_check == -1:
            ressource_position = temp_check
            # Faire la copie de la ressource et la definition de cette derniere
            new_ressource = copy.deepcopy(
                template_yml['resources'][ressource_position])
            new_ressource['source']['branch'] = branch_name
            new_ressource['name'] = 'git-' + branch_name

            # Ajout de la ressource
            print(
                ' - New ressource name : {}'.format(new_yaml['resources'][ressource_position]['name']))
            new_yaml['resources'].append(new_ressource)

        # Verification si des groupes existes, sinon ajout d'un group main
        if not new_yaml.get('groups'):
            new_yaml['groups'] = [{'name': 'main', 'jobs': []}]

        # Verification de chacune des jobs pour être fonctionnel avec la nouvelle ressource
        for job in template_yml['jobs']:
            new_job = copy.deepcopy(job)
            if '-' + branch_name in job['name']:
                new_yaml['jobs'].append(new_job)
                new_yaml['groups'][0]['jobs'].append(job['name'])
                continue
            job_to_update = True
            for b in j:
                if '-master' in job['name']:
                    new_job['name'] = new_job['name'].replace('-master', '')
                    break
                if '-' + b[branch_id] in job['name']:
                    job_to_update = False
                    break
            if not job_to_update:
                continue
            # Remplacement de chacunes des ressources pour la bonne ressource
            new_job = json.dumps(new_job)
            new_job = new_job.replace(
                job['name'], job['name'] + '-' + branch_name)
            new_job = new_job.replace(
                ressource_to_replace, 'git-' + branch_name)
            print(
                ' - New job name : {}'.format(job['name'] + '-' + branch_name))
            new_yaml['groups'][0]['jobs'].append(
                job['name'] + '-' + branch_name)
            new_job = json.loads(new_job)
            for j, plan in enumerate(new_job['plan']):
                if plan.get('task') and plan.get('file'):
                    new_job['plan'][j]['input_mapping'] = {
                        ressource_to_replace: 'git-' + branch_name}
                    new_job['plan'][j]['output_mapping'] = {
                        ressource_to_replace: 'git-' + branch_name}
                    print(' - I/O mapping for task file {}'.format(plan.get('file')))
            new_yaml['jobs'].append(new_job)
    new_yaml['resources'].pop(ressource_i)

    print(bcolors.BLUE + 'New groups :' + bcolors.ENDC)

    for group in new_yaml['groups']:
        print(' - {}'.format(group['name']))
    print(bcolors.GREEN + 'New pipeline creation done' + bcolors.ENDC)
    print(bcolors.UNDERLINE + 'The pipeline will be written in {}/{}/new_pipeline.yaml'.format(
        os.pardir, out_folder) + bcolors.ENDC)

    with open('{}/{}/new_pipeline.yaml'.format(os.pardir, out_folder), 'w') as f:
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        yaml.dump(new_yaml, f, default_flow_style=False, Dumper=noalias_dumper)

    print(bcolors.GREEN + 'Job done !!!' + bcolors.ENDC)


if __name__ == '__main__':
    main()
