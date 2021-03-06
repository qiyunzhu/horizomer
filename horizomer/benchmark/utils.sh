#!/bin/bash

# ----------------------------------------------------------------------------
# Copyright (c) 2015--, The Horizomer Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

# usage: contains multiple functions used by other scripts

# get command-line arguments
function get_args() {
    # convert arguments to --long-options
    # (e.g., input_file => --input-file)
    arg_str=$(IFS=,; echo "${args[*]/%/:}" | tr '_' '-')

    # use GNU getopt to retrieve arguments
    TEMP=`getopt -o "" -l "${arg_str}" -n "$0" -- "$@"`
    eval set -- "$TEMP"
    while true
    do
        case "$1" in
            # convert --long-options back to variable_name
            --?*) eval $(echo ${1:2} | tr '-' '_')=$2 ; shift 2 ;;
            --) shift ; break ;;
            *) echo "Internal error!" ; exit 1 ;;
        esac
    done

    # manipulate arguments
    for arg in ${args[@]}
    do
        # set undefined arguments to None
        if [ -z "${!arg+x}" ]
        then
            eval $(echo $arg)=None

        # convert files and directories to full paths
        elif [[ "$arg" == *_fp || "$arg" == *_dir ]]
        then
            # for Mac OS compatibility
            eval $(echo $arg)=$(readlink -m ${!arg} || greadlink -m ${!arg})
        fi
    done
}

# launch job
function submit_job {
    cmd=$1
    tool=$2
    if [ "${qsub_env}" == "true" ]
    then
        echo "source ${bash_config}; \
              ${cmd}" | qsub $qsub -N run_$tool; sleep 2
    else
        echo "${cmd}"
    fi
}
