# Integrating new analyzers

This document explains the integration of new analyzers in the audit node. Basically, it
requires two steps:

- Wrap the analyzer
- Register the analyzer in `config.yaml`

## Wrapping analyzers

To be able to integrate different analyzers, they must be wrapped according to some conventions.
Essentially, a wrapper must:
    - Expect the same parameters as the target analyzer.
    - Format output according to the [analyzer_integration.json](analyzer_integration.json) schema.
    
Wrappers comprise difference executables, provided either as a binary or a script. The executables
comprising a wrapper named `foo` are stored in the `analyzers/foo` directory. These binaries (if existent),
must follow speficic naming conventions and responsibilities:
    - `once`: contains the logic for setting up the execution environment in which the analyzer executes.
    This executable runs each time the environment in which the analyzer run changes. Calling `once` resets any previous call.
    - `pre_run`: contains the logic for setting up each run of the target analyzer.
    - `run`: contains the logic for invoking the analyzer executable and formatting its output.
    - `post_run`: contains the logic to clean-up each run of the target analyzer (e.g., temporary files, docker images, etc).

Each executable comprising the wrapper has access to three environment variables:
    - `STORAGE_DIR`: informs the volume (an absolute directory path) in which analyzers can create temporary or persistent files. By default, files are persistent per session, i.e., they are not removed after the analyzer executes. However, persistent
    files may be removed upon rebooting (e.g., if stored inside `/tmp`).
    - `INPUT_CONTRACT`: the filename (full path) containing the contract to be analyzed.
    - `WRAPPER_HOME`: the full path in where the wrapper is installed. This is the same folder
    where all wrapping binaries (`once`, `pre_run`, `run`, and `post_run`) are located.

The `exec` executable has a third varible `ANALYZER_ARGS` containing specific arguments on how to execute the analyzer.

## Registering analyzers

After wrapping an analyzer, the latter must be registered in the [`config.yaml` file](../../config.yaml),
under the `analyzers` entry. Analyzer-specific command-line attributes, in turn, are passed in by means of the `args` attribute. As an illustrarting snippet, registering `oyente` look as:

```
- analyzers:
    - oyente:
        - args: "--depthlimit 50 --looplimit 20"
```