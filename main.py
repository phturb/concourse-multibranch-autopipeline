import requests
import sys
import os
import yaml
import copy
import json


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
    pipeline_file = os.getenv('PIPELINE_FILENAME')
    print('Opening the file {} to replace the ressource : {}'.format(
        pipeline_file, ressource_to_replace))
    with open('pipeline.yml', 'r') as f:
        template_yml = yaml.load(f, Loader=yaml.FullLoader)
    print('Gathering branch info from repository')
    res = requests.get(
        "https://api.github.com/repos/{}/{}/branches".format(project, repo))
    j = res.json()
    ressource_i = find_ressource_index(
        template_yml['resources'], ressource_to_replace)
    for branch_info in j:
        branch_name = branch_info['name']
        print('Creating job for branch name : {}'.format(branch_name))
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
        print('New groups :')
        for group in new_yaml['groups']:
            print(' - {}'.format(group['name']))
    print('New pipeline done, the pipeline will be written in {}/{}/new_pipeline.yaml'.format(os.pardir, out_folder))
    with open('{}/{}/new_pipeline.yaml'.format(os.pardir, out_folder), 'w') as f:
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        yaml.dump(new_yaml, f, default_flow_style=False, Dumper=noalias_dumper)
    print('Job done !!!')


if __name__ == '__main__':
    main()
