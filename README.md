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
The postgres table (schedule of events) can be created with 
```bash
python scripts/create_table.py
```

Initiate a 
```bash
python yaml_to_db.py /path/to/schedules.yaml
``` 
It translates a `.yaml` schedule and adds the schedule to the database. 
See `res/` for an example `.yaml` file  (or just add events using the slack bot after it's set up).

### Aditional information
- `Procfile` contains run instructions for a Gunicorn/Uvicorn server 
(currently hosted on Heroku).
- `runtime.txt` specifies the Python version for Heroku.

After the uvicorn server has been started, visit the [automated documentation](http://localhost:8000/docs).
It also let's you test out the api endpoints.

## Testing
From repo root dir
```bash
pytest
```
