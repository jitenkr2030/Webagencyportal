#!/usr/bin/env bash
# One-command setup + start for Linux / macOS
set -e
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations portal
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
