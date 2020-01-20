"""Reminder To Todoist Sync

Usage: reminder-to-todoist.py <label> [options]

Arguments:
  <label>       Todoist label for synced tasks

Options:
  -h --help     Show this screen.
  --version     Show version.
  --debug       Verbose logging

"""
from docopt import docopt

import os
import re
import sys
import datetime
import logging
import logging.handlers
import subprocess
from pathlib import Path

from todoist.api import TodoistAPI

reminder_timefmt = '%A, %B %d, %Y at %I:%M:%S %p'

def main(todoist_api_key, todoist_label_name):
    logger.debug('Start sync')
    reminders = load_reminders()

    api = TodoistAPI(todoist_api_key)
    api.sync()

    for label in api.state['labels']:
        if label['name'] == todoist_label_name:
            todoist_label_id = label['id']
            break
    else:
        raise Exception("Todoist label '%s' not found", todoist_label_name)

    todoist_items = {
        i['id']: i for i in api.state['items']
        if todoist_label_id in i['labels']
    }

    for reminder in reminders:
        if not reminder['todo_item_id']:
            todo_item = create_todoist_item(api, reminder, todoist_label_id)
            append_reminder_body(reminder, todo_item)
            continue

        todo_item = todoist_items.get(reminder['todo_item_id'])
        if not todo_item:
            logger.error('Todoist item not found: %d', reminder['todo_item_id'])
            continue

        if not equivalent(reminder, todo_item):
            update_reminder_to_todoist(reminder, todo_item)

    logger.debug('Finished Sync')

def equivalent(reminder, todo_item):
    if todo_item['due'] is None:
        todo_due_date = None
    else:
        if len(todo_item['due']['date']) == 10:
            todo_item['due']['date'] += "T12:00:00"

        if todo_item['due']['date'][-1] == 'Z':
            todo_item['due']['date'] = todo_item['due']['date'][:-1]

        todo_due_date = datetime.datetime.strptime(
            todo_item['due']['date'],
            '%Y-%m-%dT%H:%M:%S',
        )

    return (
        reminder['name'] == todo_item['content']
        and reminder['priority'] == todo_item['priority']
        and reminder['completed'] == todo_item['checked']
        and reminder['due date'] == todo_due_date)

def update_reminder_to_todoist(reminder, todo_item):
    logger.info('Sync todoist item: %d', todo_item['id'])

    if todo_item['due'] is None:
        new_duedate = "missing value"
    else:
        if len(todo_item['due']['date']) == 10:
            todo_item['due']['date'] += "T12:00:00"

        new_duedate = datetime.datetime.strptime(
            todo_item['due']['date'],
            '%Y-%m-%dT%H:%M:%S',
        ).strftime(reminder_timefmt)

    process = subprocess.run(
        [
            'osascript',
            'update-reminder.script',
            reminder['id'],
            todo_item['content'],
            {1: '0', 2: '9', 3: '5', 4: '1'}[todo_item['priority']],
            str(bool(todo_item['checked'])),
            new_duedate,
        ],
        cwd='osascripts',
        check=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    logger.info('Done syncing')

def create_todoist_item(api, reminder, label_id):
    logger.info('Create todoist item for reminder: %s', reminder['name'])
    due_date = {
        'timezone': None,
        'string': reminder['due date'].strftime('%Y-%m-%d at %H:%M'),
        'lang': 'en',
        'is_recurring': False,
    }
    item = api.items.add(
        content=reminder['name'],
        due=due_date,
        priority=reminder['priority'],
        labels=[label_id],
    )
    api.commit()
    api.notes.add(item['id'], '\n'.join(reminder['body']))
    api.commit()
    return item

def append_reminder_body(reminder, todo_item):
    logger.info('Add todoist URL to reminder')
    url = f"https://todoist.com/showTask?id={todo_item['id']}"
    process = subprocess.run(
        ['osascript', 'add-line-to-reminder.script', reminder['id'], url],
        cwd='osascripts',
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        universal_newlines=True,
    )

def load_reminders():
    reminders = []

    process = subprocess.run(
        ['osascript', 'list-reminders.script'],
        cwd='osascripts',
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        universal_newlines=True,
    )

    for line in process.stdout.splitlines():
        if not line:
            continue

        name, body_, priority_, completed_, duedate_, moddate_, id_, _ = line.split("\t")

        body = body_.split("Þ")[:-1]
        priority = {'0': 1, '9': 2, '5': 3, '1': 4}[priority_]
        completed = completed_ == 'true'
        if duedate_ != "missing value":
            duedate = datetime.datetime.strptime(duedate_, reminder_timefmt)
        else:
            duedate = None

        moddate = datetime.datetime.strptime(moddate_, reminder_timefmt)

        todo_item_id = None
        for line in body:
            m = re.match(
                r"https://todoist.com/showTask\?id=(\d+)",
                line,
            )
            if m:
                todo_item_id = int(m.groups()[0])

        reminders.append({
            'id': id_,
            'name': name,
            'body': body,
            'due date': duedate,
            'mod date': moddate,
            'completed': completed,
            'priority': priority,
            'todo_item_id': todo_item_id,
        })

    return reminders

def setup_logging(options):
    """Configure logging."""
    global logger
    logger = logging.getLogger(
        os.path.splitext(os.path.basename(sys.argv[0]))[0],
    )

    formatter = logging.Formatter(
        "%(asctime)s: %(levelname)s[%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(
        options['--debug'] and logging.DEBUG or
        logging.ERROR,
    ) # cron will send to mail
    stream_handler.setFormatter(formatter)

    logFilePath = "/tmp/reminder-to-todoist.log"
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=logFilePath, when='midnight', backupCount=30)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

def load_todoist_api_key():
    with Path(Path.home(), '.todoist_api_key').open() as f:
        return f.readline().strip()

if __name__ == "__main__":
    options = docopt(__doc__, version='reminder-to-todoist v0.1')
    setup_logging(options)
    todoist_api_key = load_todoist_api_key()
    label_name = options['<label>']

    try:
        main(todoist_api_key, label_name)
    except Exception as e:
        logger.exception("%s", e)
        sys.exit(1)
