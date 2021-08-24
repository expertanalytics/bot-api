# bot-api
FastAPI-based Python api for slack bots. Currently hosted on Heroku using Gunicorn/Uvicorn.

## Setup
### Clone the repo
Everything below is done in the root directory of the repo, so 
```bash
cd bot-api
```

### Set up a virtualenv and install requirements
```bash
python3.8 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Install the bot-api Python package
```
pip install -e .
```

### Source environmental variables
Fill out the variables below and add to a `.env` file, then `source .env`.
```bash
SLACK_SIGNING_SECRET=<from api.slack.com>
SLACK_BOT_TOKEN=<from api.slack.com>
DATABASE_URL=<from your hosted or local postgresql database>
```

### Test server
Start a test server
```bash
uvicorn bot_api.main:app --reload
```

### Database
The current edition of the bot-api uses a free-tier PostgreSQL database from Heroku. 
Setting up a postgres database is outside the scope of this readme.
The following therefore relies on a database already being set up,
and the `DATABASE_URL` environmental variable being set correctly.

The postgres table (schedule of events) can be created with 
```bash
python scripts/create_table.py
```

Add additional data using the following command
```bash
python yaml_to_db.py /path/to/schedules.yaml
``` 
It translates a `.yaml` schedule and adds the schedule to the database. 
See `res/` for an example `.yaml` file.
If you want to start with a blank calendar, just add events using the slack bot after it's set up.

### Aditional information
- `Procfile` contains run instructions for a Gunicorn/Uvicorn server (currently hosted on Heroku).
- `runtime.txt` specifies the Python version for Heroku.

After the uvicorn server has been started, visit the [automated documentation](http://localhost:8000/docs).
It also let's you test out the api endpoints.

## Testing
From the repository's root directory
```bash
pytest
```

## Deployment
The API and the PostgreSQL database are both hosted on Heroku with a free license.
Details on how to set up deployment may or may not be added at a later time.
