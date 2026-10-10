@echo off
REM One-command setup + start for Windows
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations portal
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
