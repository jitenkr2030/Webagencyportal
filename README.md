# PixelForge – Web Agency Portal v2 (Django)

Built from `web_development_agency_portal_demo_data.xlsx`, extended with a **client portal**,
a **staff console**, **messaging** and **secure document sharing**.

## Quick start
```bash
pip install -r requirements.txt
python manage.py makemigrations portal
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```
or run `./run.sh` (Linux/macOS) / `run.bat` (Windows). Open http://127.0.0.1:8000/ (index.html).

## Demo logins
| Who | URL | Username | Password |
|---|---|---|---|
| Staff | `/admin-login/` | `admin` | `admin123` |
| Client (Nova Retail) | `/portal/login/` | `client1001` | `client123` |
| Client (Mehta Foods) | `/portal/login/` | `client1002` | `client123` |
| Client (Verma Tech) | `/portal/login/` | `client1003` | `client123` |
| Client (Singh Mfg) | `/portal/login/` | `client1005` | `client123` |

## Pages
**Public:** `/` index.html, `/admin-login/` admin_login.html, `/portal/login/` client_login.html

**Client portal** (each client sees only their own data)
| URL | Page |
|---|---|
| `/portal/` | client_dashboard – progress, alerts, meetings, messages, files, tickets |
| `/portal/projects/` , `/portal/projects/<id>/` | projects; approve designs & change requests |
| `/portal/messages/` | chat with the team (+ file attachments) |
| `/portal/documents/` | browse / download / upload files |
| `/portal/invoices/` | invoices & payments |
| `/portal/support/` | raise & track tickets |
| `/portal/meetings/` | meetings + request a meeting |
| `/notifications/` | notification centre |

**Staff console** (staff only)
| URL | Page |
|---|---|
| `/staff/` | dashboard – unread messages, approvals, meeting requests, tickets, leads |
| `/staff/inbox/` | all client conversations, reply with attachments |
| `/staff/documents/` | share files with a client or keep internal-only |
| `/staff/tickets/` | update ticket status / assignee |
| `/staff/clients/` | client directory (clients.html) |
| `/staff/accounts/` | create / reset / disable client logins |
| `/admin/` | full Django admin for every table |

## Security notes
* Every client query is filtered by the logged-in client; other clients' projects/documents return 404.
* Files are stored in `media/` and are **never** served directly – downloads go through a permission-checked view.
* Uploads: allowed types only (pdf, office, images, txt, csv, zip…), max 10 MB (`MAX_UPLOAD_MB`).
* Logout is POST-only; `?next=` redirects are validated.
* Before going live: change `SECRET_KEY`, set `DEBUG=False`, set `ALLOWED_HOSTS`, change demo passwords.

Run tests: `python manage.py test` · Reset demo data: `python manage.py seed_demo --reset`
