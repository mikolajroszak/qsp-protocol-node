## Developing QSP-Protocol-Node
1. Checkout a branch off `develop`

1. Make changes

1. Run `make test`. Fix any issues or update the tests if applicable

1. [Run the node](https://github.com/quantstamp/qsp-protocol-node#running-the-node) and check if there are any issues

1. Open a pull request from your branch into `develop`

1. Wait for CI tests to finish and pass

1. Update changelog file for related release

## Bug report

First of all, if you find a security vulnerability or suspect a problem to be security-related, 
please do NOT open an issue and do NOT discuss it in anywhere public. 
Email dev-support@quantstamp.com instead.

In other cases, 
please follow the steps that will certainly help us and will also help you solve the bug faster:
1. Search if your bug has been reported or not. 
2. Check if you are using the latest version.
3. Make sure what you're describing is really a bug.


Once you're certain that you should submit the bug, 
we highly recommend filing an issue through Github to get a timely response. 

To submit an issue, please include the following information in your post:
1. What is the version that you are using?
2. What OS are you using? Please include its version as well for reference.
3. What is your goal when performing the actions?
4. What did you do?
5. What did you expect to see?
6. What did you see instead?
7. Other information you think would be helpful and related to the issue.

## Feature suggestion

### Before you make a suggestion:
1. Check if the latest version already supports the feature.
2. Search in the issue list to see if this has been suggested before.

### To make a suggestion:
We'll track the suggestion using Github issues, to make an effective suggestion:

* The issue title should be descriptive and clear.
* Describe the feature as clear as possible.
* Provide an example to demonstrate the feature step-by-step.
* Explain why this feature would be useful to the community 
* Specify the environment that you're using: which version of the software / what OS / etc.

## Pull Request Guideline

[Guidelines for github contribution](https://gist.github.com/Chaser324/ce0505fbed06b947d962)

To make a pull request:
1. Ensure that all tests have passed.
2. Write new tests that cover the new codes.
2. Follow the coding guidelines.
3. Update the documents accordingly to describe the interface and feature change

We will review the pull requests when we have availability and 
will give you feedback based on your changes. We expect responses of the feedback within 2 weeks.
After 2 weeks, we may close the pull request due to inactivity.

### Making a release
1. Run `make bundle`. If successful, this creates `qsp-protocol-<version>.zip`
   file under deployment/local.
1. If an authorized developer, put the bundle under the "Releases" page on
   Github.

### Code walkthrough

* Main file: `src/qsp_protocol_node/__main__.py`

* Target environments are defined in `resources/config.yaml`, which are
  passed on to the audit node

* Main files
  - `src/config/config.py`
    - provides an interface for accessing configured components
    instantiated from the settings in the YAML file
  - `src/audit/audit.py`
    - contains the program's main loop. See the `run()` method
    - contains the logic for audit computation; calls each analyzer by its
    wrapper plugin.
    - report is put into JSON format, compressed, and posted to Ethereum
  - `src/audit/wrapper.py`:
    - wraps the execution of a target analyzer according to a [plugin
    interface](https://github.com/quantstamp/qsp-protocol-node/blob/develop/plugins/analyzers/README.md). 
  - `src/audit/analyzer.py`
    - abstracts an analyzer tool, invoking its corresponding wrapper

### Coding style

The general codestyle builds on PEP8 and includes the following:

1. Indentation is done using spaces in multiples of 4
2. Lines are broken after 100 characters, longer lines are allowed in exceptional cases only
3. Methods are separated with 2 blank lines
4. Do not use parentheses when not necessary
5. `import` statements come before `from import` statements
6. Import only one module per line
7. Remove unused imports
8. Use lowercase_underscore naming for variables
9. Use `is` and `is not` when comparing to `None`
10. Beware of overriding built-ins

Before comitting code, run `make stylecheck` to whether you code adheres to our
style guide. If not, your commit will automatically fail in CI.

## Contributor's code of conduct
# Code Of Conduct

Please note we have a code of conduct, please follow it in all your interactions with the project.

## Our Pledge

In the interest of fostering an open and welcoming environment, we as
contributors and maintainers pledge to making participation in our project and
our community a harassment-free experience for everyone, regardless of age, body
size, disability, ethnicity, gender identity and expression, level of experience,
nationality, personal appearance, race, religion, or sexual identity and
orientation.

## Our Standards

Examples of behavior that contributes to creating a positive environment
include:

* Using welcoming and inclusive language
* Being respectful of differing viewpoints and experiences
* Gracefully accepting constructive criticism
* Focusing on what is best for the community
* Showing empathy towards other community members

Examples of unacceptable behavior by participants include:

* The use of sexualized language or imagery and unwelcome sexual attention or
advances
* Trolling, insulting/derogatory comments, and personal or political attacks
* Public or private harassment
* Publishing others' private information, such as a physical or electronic
  address, without explicit permission
* Other conduct which could reasonably be considered inappropriate in a
  professional setting

## Our Responsibilities

Project maintainers are responsible for clarifying the standards of acceptable
behavior and are expected to take appropriate and fair corrective action in
response to any instances of unacceptable behavior.

Project maintainers have the right and responsibility to remove, edit, or
reject comments, commits, code, wiki edits, issues, and other contributions
that are not aligned to this Code of Conduct, or to ban temporarily or
permanently any contributor for other behaviors that they deem inappropriate,
threatening, offensive, or harmful.

## Scope

This Code of Conduct applies both within project spaces and in public spaces
when an individual is representing the project or its community. Examples of
representing a project or community include using an official project e-mail
address, posting via an official social media account, or acting as an appointed
representative at an online or offline event. Representation of a project may be
further defined and clarified by project maintainers.

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported by contacting the project team. All
complaints will be reviewed and investigated and will result in a response that
is deemed necessary and appropriate to the circumstances. The project team is
obligated to maintain confidentiality with regard to the reporter of an incident.
Further details of specific enforcement policies may be posted separately.

Project maintainers who do not follow or enforce the Code of Conduct in good
faith may face temporary or permanent repercussions as determined by other
members of the project's leadership.

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage], version 1.4,
available at [http://contributor-covenant.org/version/1/4][version]

[homepage]: http://contributor-covenant.org
[version]: http://contributor-covenant.org/version/1/4/

