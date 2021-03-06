#!/bin/bash
#
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
#
# This script shows the basic stats of changes in git repositories
# between the two series given as the first argument.

if [[ ! -d .tox/venv ]]; then
    tox -e venv --notest
fi
source .tox/venv/bin/activate

bindir="$(dirname $0)"
source "$bindir/functions"
setup_temp_space

START="$1"
shift
END="$1"
shift
REPOS="$@"

function get_branch_end() {
    local branch="$1"

    if git tag | grep -q ${branch}-eol; then
        # This branch is closed, use the EOL tag as the start
        echo "${branch}-eol"
    else
        echo "origin/stable/$branch"
    fi
}

function get_branch_base() {
    local branch="$1"
    local scan_start="$(get_branch_end $branch)"

    git log --decorate --oneline ..${scan_start} \
        | grep tag: \
        | tail -n 1 \
        | cut -f2 -d: \
        | cut -f1 -d')'
}

function count_lines() {
    git ls-files | xargs wc -l | tail -n 1 | awk '{print $1}'
}

function count_files() {
    git ls-files | wc -l
}

function git_ls_tree() {
    local tag="$1"
    local extension="$2"

    if [ -z "$extension" ]; then
        git ls-tree -lr $tag
    else
        git ls-tree -lr $tag | grep ${extension}'$'
    fi
}

function shas_at_tag() {
    # Produce a list of shas used by objects representing files with
    # real content at the tag point
    local tag="$1"
    local extension="$2"

    local mode
    local type
    local sha
    local size
    local filename

    git_ls_tree $tag $extension | while read mode type sha size filename; do
        if [ "$size" != "0" ]; then
            echo $sha
        fi
    done
}

function count_unchanged_files() {
    local start="$1"
    local end="$2"
    local extension="$3"

    comm -12 <( shas_at_tag $start "$extension" | sort  ) \
         <( shas_at_tag $end "$extension" | sort ) \
        | wc -l
}

for repo in $REPOS; do
    clone_repo $repo
    cd $repo

    # Find when the start branch was created
    base=$(echo $(get_branch_base $START))  # echo strips leading spaces

    # Compute the most recent tagged version on the ending series.
    latest=$(git describe --abbrev=0 $(get_branch_end $END))

    title "$repo $base .. $latest"
    echo

    git checkout $base 2>/dev/null
    echo $base lines: $(count_lines)
    echo $base files: $(count_files)
    echo

    git checkout $latest 2>/dev/null
    echo $latest lines: $(count_lines)
    echo $latest files: $(count_files)
    echo

    git diff --stat ${base}..${latest} | tail -n 1
    echo

    echo "Unchanged files: $(count_unchanged_files $base $latest)"
    echo "Unchanged .py files: $(count_unchanged_files $base $latest .py)"
    echo

    cd $MYTMPDIR
done
