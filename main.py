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
    new_yaml = {'resources': [], 'jobs': [], 'groups': []}
    project = os.getenv('PROJECT')
    repo = os.getenv('REPO')
    ressource_to_replace = os.getenv('REPLACED_RESSOURCE')
    out_folder = os.getenv('OUT_FOLDER')
    pipeline_file = os.pardir + os.getenv('PIPELINE_FILENAME')
    print(bcolors.HEADER + 'Opening the file {} to replace the ressource : {}'.format(
        pipeline_file, ressource_to_replace) + bcolors.ENDC)
    with open(pipeline_file, 'r') as f:
        template_yml = yaml.load(f, Loader=yaml.FullLoader)
    print(bcolors.UNDERLINE + 'Gathering branch info from repository' + bcolors.ENDC)
    res = requests.get(
        "https://api.github.com/repos/{}/{}/branches".format(project, repo))
    if(res.status_code != 200):
        print(bcolors.FAIL + 'Error with branches gathering request' + bcolors.ENDC)
        sys.exit(1)
    j = res.json()
    ressource_i = find_ressource_index(
        template_yml['resources'], ressource_to_replace)
    if(ressource_i == -1):
        print(bcolors.FAIL +
              'Ressource that needs to be changed doesn\'t exist' + bcolors.ENDC)
        sys.exit(1)
    for branch_info in j:
        branch_name = branch_info['name']
        print(bcolors.BLUE +
              'Creating job for branch name : {}'.format(branch_name) + bcolors.ENDC)
        new_ressource = copy.deepcopy(template_yml['resources'][ressource_i])
        new_ressource['source']['branch'] = branch_name
        new_ressource['name'] = 'git-' + branch_name
        print(' - New ressource name : {}'.format(new_ressource['name']))
        new_yaml['resources'].append(new_ressource)
        new_group = {'name': branch_name, 'jobs': []}
        for job in template_yml['jobs']:
            new_job = copy.deepcopy(job)
            new_job['name'] = new_job['name'] + '-' + branch_name
            print(' - New job name : {}'.format(new_job['name']))
            for pos, item in enumerate(new_job['plan']):
                if item.get('get') and item.get('get') == template_yml['resources'][0]['name']:
                    new_job['plan'][pos]['get'] = 'git-'+branch_name
            new_yaml['jobs'].append(new_job)
            new_group['jobs'].append(new_job['name'])
        new_yaml['groups'].append(new_group)
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
