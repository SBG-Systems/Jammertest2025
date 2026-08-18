# SBG Systems - INS Monitoring system

Quick'n'Dirty Dashboard created fo follow INS data during Jammertest 2025

## Install

Ensure to have python and [Poetry](https://python-poetry.org/docs/#installation) installed and available in path.

```sh
# Install dependencies (creates the virtual env automatically)
poetry install
```


## Configure

Create `config.json` from `config_template.json`
Ensure each `id` field is unique upon all configured INS.

`config.json` expects an array of INS configuration objects. Available fields are :

- `id` **mandatory** Unique ID for the system
- `name` **mandatory** Display name
- `connection_type` **mandatory**
    - `ethernet` Connect to INS through INS Rest API
    - `fake` Use local file at `<project source>/app/monitoring/collectors/fake_data.json` to send data
- `ip_address` **madatory** if `connection_type` is set to `ethernet`
- `color` Color as hex code (for map display)


## Run

```sh
poetry run python app.py
```

Go to [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
