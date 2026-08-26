# Contributing to *sqlalchemy-history*

## **Instructions**

### Issues

- Add new requirement/issue/questions in issue tracker of repository.
- Issues should preferably include a minimal reproducible example where relevant.

### Documentation

Documentation content lives in the `docs/` directory and the site is configured
in `zensical.toml`. Start a local documentation server with live reload by
running:

```sh
uv run zensical serve
```

`uv run` automatically synchronizes the project environment, including the
documentation dependencies. Open the URL shown in the terminal to preview your
changes. Before submitting a documentation change, ensure the site builds
without warnings:

```sh
uv run zensical build --strict
```

### Pull Requests

- Each PR should have a corresponding issue available in issue tracker of repository.
- To raise a PR, fork **sqlalchemy-history**
- Clone the project in your local machine

```sh
git clone https://github.com/corridor/sqlalchemy-history.git
cd sqlalchemy-history
```

- Install uv in your local system

```sh
# Refer https://docs.astral.sh/uv/getting-started/installation
curl -LsSf https://astral.sh/uv/install.sh | sh
```

- Install requirements of project into virtual environment.

```sh
uv sync
```

- Install Git hooks with `prek`.

```sh
uv run prek install --prepare-hooks
```

- Checkout a branch with a name relevant to the issue you are working on.

```sh
git checkout -b short-issue-desc 
# OR
git checkout -b fix-issue-num
# OR 
git checkout -b add-issue-num
```

- Make changes as per the issue you are working on and add/modify testfile(s) if you are adding new feature or fixing bugs in existing code

- Before committing, verify that the changes work locally.

```sh
# Run tests locally
DB=sqlite uv run pytest

# Run local hooks and formatting checks
uv run prek run --all-files
```

- Commit your changes with a title and description briefly explaining the approach.
  - Keep commit message title 72 characters
  - The “type” has to be any one of:
    - feat: A new feature addition
    - fix: A bug being fix to an existing capability
    - test: A test case being added or changed
    - refactor: A code change that neither fixes a bug nor adds a feature
    - chore: Other changes that don’t modify src or test files

```sh
git commit
# The commit message should follow this structure
type(issue#Num): a short title goes here

A long description of what you are trying to change in this commit.

```

- Push the changes in your fork 

```sh
git push origin <branch-name>
```

- Go to GitHub, open a PR against `corridor/sqlalchemy-history:main`, and wait for a review.
- Maintainer(s) of the project will review and approve the CI flow to validate changes across different environments.
- If changes are valid and passes all the tests, maintainer(s) will accept the PR(s)
