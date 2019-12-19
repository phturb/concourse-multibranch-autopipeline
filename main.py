'''
    This script allows to gather information from a concourse pipeline and replicate the pipeline
    for all the branches included in a git repository. Works with github and bitbucket
    Only uses basic auth or no auth. 
'''
import requests
import sys
import os
import yaml
import copy
import json


class bcolors:
    '''
    Terminal colors
    Start your text with a {clolor} then end your string with ENDC
    '''
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
    '''
    Find the index for the ressource that has the name of the value_to_find
    '''
    for i, ressource in enumerate(ressources):
        if ressource['name'] == value_to_find:
            return i
    return -1


def find_group_index(groups, value_to_find):
    '''
    Find the index for the ressource that has the name of the value_to_find
    '''
    for i, g in enumerate(groups):
        if g['name'] == value_to_find:
            return i
    return -1


def get_jobs_list(groups, group_name):
    group_index = find_group_index(groups, group_name)
    return groups[group_index]['jobs']


def main():
    # Definition of variables from ENV variables
    try:
        project = os.getenv('PROJECT')
        git_type = os.getenv('GIT_TYPE')
        git_api = os.getenv('GIT_API')
        repo = os.getenv('REPO')
        ressource_to_replace = os.getenv('REPLACED_RESSOURCE')
        out_folder = os.getenv('OUT_FOLDER')
        pipeline_file = os.pardir + '/' + os.getenv('PIPELINE_FILENAME')
    except:
        print(bcolors.FAIL +
              'Missing ENV variables' + bcolors.ENDC)
        sys.exit(1)
    # Checking if there is branch exception
    try:
        branch_exception = os.getenv('BRANCH_EXCEPTION')
        branch_exception = branch_exception.split(" ")
    except:
        branch_exception = []

    try:
        group = os.getenv('GROUP')
    except:
        group = ""

    # Checking if there is an api username and password
    try:
        username = os.getenv('API_USERNAME')
        password = os.getenv('API_PASSWORD')
    except:
        username = ""
        password = ""

    # Opening the files to update the configuration
    print(bcolors.HEADER + 'Opening the file {} to replace the ressource : {}'.format(
        pipeline_file, ressource_to_replace) + bcolors.ENDC)
    with open(pipeline_file, 'r') as f:
        template_yml = yaml.load(f, Loader=yaml.FullLoader)
    new_yaml = copy.deepcopy(template_yml)
    new_yaml['jobs'] = []

    # Gathering information on branches from the repository
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

    # Process the request answer
    res_json = res.json()
    if git_type == 'bitbucket':
        res_json = res_json['values']

    # Verify that the resource that needs to be changed exist
    ressource_i = find_ressource_index(
        template_yml['resources'], ressource_to_replace)
    if(ressource_i == -1):
        print(template_yml)
        print(bcolors.FAIL +
              'Ressource that needs to be changed doesn\'t exist' + bcolors.ENDC)
        print(template_yml['resources'])
        sys.exit(1)
    job_list = []
    if not template_yml.get('groups'):
        new_yaml['groups'] = [{'name': 'main', 'jobs': []}]
        for job in template_yml['jobs']:
            job_list.append(job['name'])
        group_index = 0
    elif group != '':
        job_list = get_jobs_list(template_yml['groups'], group)
        group_index = find_group_index(template_yml['groups'], group)
        group_index = group_index if group_index != -1 else 0
    else:
        for job in template_yml['jobs']:
            job_list.append(job['name'])
        group_index = 0
    new_yaml['groups'][group_index]['jobs'] = []

    print(bcolors.BLUE + 'The group that will be replicated is :' + bcolors.ENDC)
    print(' - {}'.format(new_yaml['groups'][group_index]['name']))
    print(bcolors.BLUE +
          'The jobs that will be replicated for each branch are :' + bcolors.ENDC)
    for job in job_list:
        print(' - {}'.format(job))
    # For each branch in the repository
    for branch_info in res_json:
        # Get the branch name
        if git_type == 'bitbucket':
            name_id = 'displayId'
        else:
            name_id = 'name'
        branch_name = branch_info[name_id]

        # Verify that the branch is not in the exception list
        if branch_name in branch_exception:
            print(bcolors.WARNING +
                  'Skipping branch : {}'.format(branch_name) + bcolors.ENDC)
            continue

        # Creation of the job for the branch
        print(bcolors.BLUE +
              'Creating job for branch name : {}'.format(branch_name) + bcolors.ENDC)
        # Cration of the resource for the branch
        new_resource_name = 'git-' + branch_name
        new_resource = copy.deepcopy(template_yml['resources'][ressource_i])
        new_resource['source']['branch'] = branch_name
        new_resource['name'] = new_resource_name

        print(
            ' - New ressource name : {}'.format(new_yaml['resources'][ressource_i]['name']))

        # Appending the resource to the new config file
        new_yaml['resources'].append(new_resource)

        # Create a group if the config file has no group
        # Creating new task to match the branch information
        for job in template_yml['jobs']:
            if job['name'] in job_list:
                new_job = copy.deepcopy(job)
                new_job = json.dumps(new_job)

                # Replacing the resource name with the new one
                new_job_name = job['name'] + '-' + branch_name
                new_job = new_job.replace(
                    job['name'], new_job_name)
                new_job = new_job.replace(
                    ressource_to_replace, new_resource_name)
                print(' - New job name : {}'.format(new_job_name))
                for j in job_list:
                    if j != job['name']:
                        print('  - Replacing {} with {}'.format(j,
                                                                j + '-' + branch_name))
                        new_job = new_job.replace(
                            j, j + '-' + branch_name)
                # Add the job to the group
                new_yaml['groups'][group_index]['jobs'].append(new_job_name)

                # Add the mapping of input for the new resource to match in the tasks
                # Replace the name for the new resource name
                new_job = json.loads(new_job)
                for res_json, plan in enumerate(new_job['plan']):
                    if plan.get('task') and plan.get('file'):
                        # Map the old resource with the new resource for input
                        new_job['plan'][res_json]['input_mapping'] = {
                            ressource_to_replace: new_resource_name}
                        # Map the old resource with the new resource for output
                        new_job['plan'][res_json]['output_mapping'] = {
                            ressource_to_replace: new_resource_name}
                        print(
                            ' - I/O mapping for task file {}'.format(plan.get('file')))
                        print('   - {} to {}'.format(
                            ressource_to_replace, new_resource_name))
                # Add the task to the new job task list
                new_yaml['jobs'].append(new_job)
    # Add the job that are not changed
    print(bcolors.BLUE + 'Adding unaltered job' + bcolors.ENDC)
    for job in template_yml['jobs']:
        if not job['name'] in job_list:
            print(' - Adding {}'.format(job['name']))
            new_job = copy.deepcopy(job)
            new_yaml['jobs'].append(new_job)

    # Remove the original resource that has been updated
    new_yaml['resources'].pop(ressource_i)

    # Show infromation about the new group created
    print(bcolors.BLUE + 'New groups :' + bcolors.ENDC)

    for group in new_yaml['groups']:
        print(' - {}'.format(group['name']))
    print(bcolors.GREEN + 'New pipeline creation done' + bcolors.ENDC)
    print(bcolors.UNDERLINE + 'The pipeline will be written in {}/{}/new_pipeline.yaml'.format(
        os.pardir, out_folder) + bcolors.ENDC)

    # Write the pipeline config in a new file defined by the env variables
    with open('{}/{}/new_pipeline.yaml'.format(os.pardir, out_folder), 'w') as f:
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        yaml.dump(new_yaml, f, default_flow_style=False, Dumper=noalias_dumper)

    print(bcolors.BLUE + 'Here is the new configuration for the pipeline' + bcolors.ENDC)
    print(yaml.dump(new_yaml))
    # Jobs done
    print(bcolors.GREEN + 'Job done !!!' + bcolors.ENDC)


if __name__ == '__main__':
    main()
