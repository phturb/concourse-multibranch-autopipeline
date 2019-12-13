import requests
import sys
import os
import yaml
import copy
import json

new_yaml = {'resources': [], 'jobs': []}
with open('pipeline.yml', 'r') as f:
    template_yml = yaml.load(f, Loader=yaml.FullLoader)
    # print(template_yml)
project = os.getenv('PROJECT')
repo = os.getenv('REPO')
res = requests.get(
    "https://api.github.com/repos/{}/{}/branches".format(project, repo))
j = res.json()
for branch_info in j:
    branch_name = branch_info['name']
    new_ressource = copy.deepcopy(template_yml['resources'][0])
    new_ressource['source']['branch'] = branch_name
    new_yaml['resources'].append(new_ressource)
    for job in template_yml['jobs']:
        new_job = copy.deepcopy(job)
        new_job['name'] = new_job['name'] + '-' + branch_name
        for pos, item in enumerate(new_job['plan']):
            if item.get('get') and item.get('get') == template_yml['resources'][0]['name']:
                new_job['plan'][pos]['get'] = branch_name
        new_yaml['jobs'].append(new_job)
with open('../pipeline/new_pipeline.yaml', 'w') as f:
    noalias_dumper = yaml.dumper.SafeDumper
    noalias_dumper.ignore_aliases = lambda self, data: True
    yaml.dump(new_yaml, f, default_flow_style=False, Dumper=noalias_dumper)
