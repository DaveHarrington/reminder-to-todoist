# reminder-to-todoist
Sync Apple Reminders to Todoist

# Install
brew install pipenv
pipenv --three
pipenv install

# Crontab
* * * * * /usr/local/bin/pipenv run python3 /Users/dharrington/projects/reminder-to-todoist/reminder-to-todoist.py agenda
