# Integrating new analyzers

This document explains the integration of new analyzers in the audit node. Basically, it
requires two steps:

- Wrap the analyzer
- Register the analyzer in `config.yaml`

## Wrapping analyzers

Integrating different analyzers require wrapping them according to an execution
interface and data schema. As such, for each analyzer one creates a
corresponding plugin wrapper. Essentially, a wrapper must:
- Expect the same parameters as the target analyzer.
- Format output according to the [analyzer_integration.json](https://github.com/quantstamp/qsp-protocol-node/blob/develop/plugins/analyzers/schema/analyzer_integration.json) schema.
    
Wrappers provide difference executables, either as a binary or a script. The executables
comprising a wrapper named `foo` are stored in the `plugins/analyzers/wrappers/foo` directory. These binaries (if existent),
must follow specific naming conventions and responsibilities:
- `metadata`: contains the logic to produce analyzer metadata 
Outputs to stdout name, version, command, and a list of the vulnerabilities it
aims to detect (one per line).
- `pull_analyzer`: pulls the Docker image of the target analyzer
- `run`: executes the target wrapper

Each of these scripts are given a base environment with the following
variables setup:
  - `STORAGE_DIR`: informs the volume (an absolute directory path) in which analyzers can create temporary or persistent files. By default, files are persistent per session, i.e., they are not removed after the analyzer executes. However, persistent
    files may be removed upon rebooting (e.g., if stored inside `/tmp`)
- `ANALYZER_NAME`: the analyzer name
- `ANALYZER_ARGS`: the arguments on how to invoke the target analyzer
- `WRAPPER_HOME`: a folder containing all the binaries comprising the wrapper, namely `once`, `metadata`, `pull_analyzer`, `pre_run`, `run`, and/or `post_run`

In the case of `run`, three other variables appear in its executing environment:
- `CONTRACT_PATH`: the path where the target contract is located
- `CONTRACT_FILE_NAME`: the filename of the target contract
- `ORIGINAL_FILE_NAME`: the original filename of the target contract (i.e.,
    prior to flattening)

`run` is generally broken into a sequence of steps, whose
logic is broken in four scripts:
- `once`: contains the logic for setting up the execution environment in which
  the analyzer executes. This executable runs each time the environment in which
  the analyzer run changes. Calling `once` resets any previous call.
- `pre_run`: contains the logic for setting up each run of the target analyzer.
- `run`: contains the logic for invoking the analyzer executable and formatting its output.
- `post_run`: contains the logic to clean-up each run of the target analyzer
(e.g., temporary files, docker images, etc).

## Registering analyzers

After an analyzer wrapper pluing is created, it must be registered in the [`config.yaml` file](https://github.com/quantstamp/qsp-protocol-node/blob/develop/resources/config.yaml),
under the `analyzers` entry. Analyzer-specific command-line attributes, in turn,
are passed in by means of the `args` attribute. As an illustrating snippet,
registering `mythril` looks as follows:

```
- analyzers:
    - mythril:
        args: "--depthlimit 50 --looplimit 20"
        storage_dir: ~/.mythril
        timeout_sec: 120
```
