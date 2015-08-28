Panopta CLI
===========

# Installation
```bash
python setup.py install
```

# Usage
**Note**: Currently, the Panopta CLI only offers the ability to batch enter a
set of servers into a maintenance period. Stay tuned for more features!

## Maintenance
```bash
panopta your-api-token maintenance \
--customer-keys "customer-1,customer-2" \
--fqdn-pattern ".*\.edu$" \
--tags linux \
--start "2015-12-24 23:59:00" \
--end "December 25, 2015 00:00:00"
```

The above example command will put servers for the customers with customer keys
`customer-1` and `customer-2` that have a fully qualified domain name that ends
in ".edu" and that have the tag "linux" applied them into a maintenance period
starting at 11:59pm on Christmas Eve until midnight on Christmas morning.

### Dry Run
Using the `--dry-run` option will retrieve data but will make not execute any
creations, updates, or deletions. 

## Help
To view all usage options:
```bash
panopta --help
```

# Development
## Setup
You must have [*python*](https://www.python.org/) (obviously),
[*git*](https://git-scm.com/), and
[*virtualenv*](https://github.com/pypa/virtualenv) installed.

1. Check out the *scripts* repository and enter the project directory:
```bash
git clone git@github.com:Panopta/scripts.git scripts && cd scripts/panopta-cli/ 
```
2. Create a *virtualenv* environment:
```bash
virtualenv env
```
3. Activate the environment:
```bash
source env/bin/activate
```
4. Install the required development dependencies:
```bash
pip install --requirement dev-requirements.txt
```

**Note**: You can name your virtual environment anything you like; it doesn't
have to be `env`; you may want to name it after the version of Python you
would like to run in it, eg. `py2.7`. Just be sure to add your custom-named
environment directory to your global gitignore file (`~/.gitignore`) so that it
doesn't accidentally get checked into the repo.

## Managing Dependencies
We use [*pip*](https://github.com/pypa/pip) to install/uninstall dependencies.
```bash
pip install --requirement dev-requirements.txt
```

## Testing
We use [*nose*](http://nose.readthedocs.org) to discover and run tests.
```bash
nosetests tests/
```

**TIP**: It is recommended that you add the above command to your pre-commit
hooks file (`.git/hooks/pre-commit`), so that you can ensure you're not checking
in code that causes failing tests.
