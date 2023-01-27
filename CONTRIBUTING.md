# Contributing to *sqlalchemy-history*

## **Instructions**

### Issues
- Add new requirement/issue/questions in issue tracker of repository.
- Issue(s) raised on repository should preferably have minimum reproducible code whereever relevant for others to reproduce and work on issue.

### Pull Requests
- Each PR should have a corresponding issue available in issue tracker of repository.
- To raise a PR, fork **sqlalchemy-history** 
- Clone the project in your local machine
```
git clone https://github.com/corridor/sqlalchemy-history.git
cd sqlalchemy-history
```
- Install Poetry in your local system
```
# Refer https://python-poetry.org/docs/#installation 
curl -sSL https://install.python-poetry.org | python3 -
```
- Install requirements of project into virtual environment.
```
poetry install   # Poetry creates a virtual environment in your local
# NOTE: If poetry is not set in your $PATH variable you can use
# '~/.local/share/pypoetry/venv/bin/poetry install' instead!
# Activate this virtual environment in your local by calling
source ./.venv/bin/activate
```
- Checkout branch with name relevant to issue issue you are working
```
git checkout -b short-issue-desc 
# OR
git checkout -b fix-issue-num
# OR 
git checkout -b add-issue-num
```
- Make changes as per the issue you are working on and add/modify testfile(s) if you are adding new feature or fixing bugs in existing code
- Before commiting, verify if the changes are working in your local system
```
export DB=sqlite # for local dev testing
pytest
# Lint
black .
```
- Add commit for your changes with message title and message description brifly explaining the approach
    - Keep commit message title 72 characters
    - The “type” has to be any one of:
        - feat: A new feature addition
        - fix: A bug being fix to an existing capability
        - test: A test case being added or changed
        - refactor: A code change that neither fixes a bug nor adds a feature
        - chore: Other changes that don’t modify src or test files
```
git commit
# The commit message should follow this structure
type(issue#Num): a short title goes here

A long description of what you are trying to change in this commit.
```
- Push the changes in your fork 
```
git push origin <branch-name>
```
- Got to github, and raise a PR `corridor/sqlalchemy-history:master` and wait for a review.
- Maintainer(s) of the project will review and approve the CI flow to validate changes across different environments.
- If changes are valid and passes all the tests, maintainer(s) will accept the PR(s)
