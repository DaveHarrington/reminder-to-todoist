# reminder-to-todoist
Sync Apple Reminders to Todoist

# Install
```
brew install pipenv
pipenv --three
pipenv install
```

# Configure
echo TODOIST_API_KEY > ~/.todoist_api_key

# Crontab
* * * * * /usr/local/bin/pipenv run python3 /<PATH>/reminder-to-todoist/reminder-to-todoist.py <tagname(agenda)>
