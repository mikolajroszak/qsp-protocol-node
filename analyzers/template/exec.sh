#!/bin/bash

function run_analyzer()
    # TODO
    # Runs the analyzer based on the given INPUT_CONTRACT and INPUT_ARGS.
     echo "TODO: run_analyzer()"

if [[ ! -f "$STORAGE_DIR/.once" ]] ; then
    once
fi

$WRAPPER_HOME/pre_run

run_analyzer

$WRAPPER_HOME/post_run
