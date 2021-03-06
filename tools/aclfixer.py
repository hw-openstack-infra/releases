#!/usr/bin/python
#
# Tool to generate a patch to remove direct tagging / branch-creating
# rights for official OpenStack deliverables
#
# Copyright 2018 Thierry Carrez <thierry@openstack.org>
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import argparse
import os
import re
import sys

import yaml


TEAM_EXCEPTIONS = [
    'Infrastructure',
    'OpenStack Charms',
    'Chef OpenStack',
    'OpenStack-Helm',
    'rally',
    'RefStack',
]

WILDCARD_REPO_EXCEPTIONS = [
]

REPO_EXCEPTIONS = [
    'openstack-dev/bashate',
    'openstack-infra/tripleo-ci',
    'openstack/dib-utils',
    'openstack/diskimage-builder',
    'openstack/dragonflow',
    'openstack/ec2-api',
    'openstack/eslint-config-openstack',
    'openstack/heat-cfntools',
    'openstack/karma-subunit-reporter',
    'openstack/manila-image-elements',
    'openstack/manila-test-image',
    'openstack/murano-apps',
    'openstack/networking-powervm',
    'openstack/nova-powervm',
    'openstack/swift-bench',
    'openstack/yaql',
]


def is_a_repo_exception(repo):
    for pattern in WILDCARD_REPO_EXCEPTIONS:
        if re.match(pattern, repo):
            return True
    return repo in REPO_EXCEPTIONS


def is_a_team_exception(team):
    return team in TEAM_EXCEPTIONS


def acl_patch(repo, fullfilename):

    newcontent = ""
    with open(fullfilename) as aclfile:
        skip = False
        for line in aclfile:
            # Skip until start of next section if in skip mode
            if skip:
                if line.startswith('['):
                    skip = False
                else:
                    continue

            # Remove [access ref/tags/*] sections
            if line.startswith('[access "refs/tag'):
                skip = True
                continue

            # Remove 'create' lines
            if line.startswith('create ='):
                continue

            # Copy the current line over
            newcontent += line

    with open(fullfilename, 'w') as aclfile:
        aclfile.write(newcontent)


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('project_config_repo')
    parser.add_argument('governance_repo')
    parser.add_argument(
        '--dryrun',
        default=False,
        help='do not actually do anything',
        action='store_true')
    args = parser.parse_args(args)

    # Load repo/aclfile mapping from Gerrit config
    projectsyaml = os.path.join(args.project_config_repo, 'gerrit', 'projects.yaml')
    acl = {}
    config = yaml.load(open(projectsyaml))
    for project in config:
        aclfilename = project.get('acl-config')
        if aclfilename:
            (head, tail) = os.path.split(aclfilename)
            acl[project['project']] = os.path.join(os.path.basename(head),
                                                   tail)
        else:
            acl[project['project']] = project['project'] + '.config'

    aclbase = os.path.join(args.project_config_repo, 'gerrit', 'acls')
    governanceyaml = os.path.join(args.governance_repo, 'reference', 'projects.yaml')
    teams = yaml.load(open(governanceyaml))
    for tname, team in teams.iteritems():
        if is_a_team_exception(tname):
            print('--- %s --- (SKIPPED)' % tname)
            continue
        print('=== %s ===' % tname)
        for dname, deliverable in team['deliverables'].iteritems():
            for repo in deliverable.get('repos'):
                if is_a_repo_exception(repo):
                    print('%s - Skipping' % repo)
                else:
                    print('%s - Patching %s' % (repo, acl[repo]))
                    if not args.dryrun:
                        acl_patch(repo, os.path.join(aclbase, acl[repo]))


if __name__ == '__main__':
    main()
