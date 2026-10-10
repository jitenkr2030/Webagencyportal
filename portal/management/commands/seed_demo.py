"""Load the demo data from the Excel workbook (portal/seed_data.py).

Usage:
    python manage.py seed_demo           # load data (skips rows that already exist)
    python manage.py seed_demo --reset   # wipe all portal tables first
"""
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from portal import models as m
from portal.seed_data import SEED


def D(value):
    return Decimal(str(value or 0))


def parse_date(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def parse_time(value):
    if isinstance(value, time):
        return value
    h, mi = str(value).split(":")[:2]
    return time(int(h), int(mi))


class Command(BaseCommand):
    help = "Load demo data for the Web Development Agency Portal"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing portal data first")
        parser.add_argument("--no-admin", action="store_true", help="Do not create the demo admin user")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["reset"]:
            User = get_user_model()
            for doc in m.Document.objects.all():
                doc.delete()          # also removes the stored file
            m.Message.objects.all().delete()
            m.Notification.objects.all().delete()
            User.objects.filter(client_profile__isnull=False).delete()
            for model in [m.Timesheet, m.Meeting, m.AMCPlan, m.SupportTicket, m.Payment, m.Invoice,
                          m.ChangeRequest, m.Website, m.Bug, m.Design, m.Task, m.Project, m.Proposal,
                          m.Requirement, m.Service, m.Lead, m.Employee, m.Client]:
                model.objects.all().delete()
            self.stdout.write(self.style.WARNING("Existing portal data deleted."))

        S = SEED
        for r in S["Clients"]:
            m.Client.objects.update_or_create(pk=r[0], defaults=dict(
                contact_name=r[1], email=r[2], company=r[3], city=r[4], status=r[5]))

        for r in S["Leads"]:
            m.Lead.objects.update_or_create(pk=r[0], defaults=dict(
                company=r[1], requirement=r[2], lead_source=r[3], status=r[4], estimated_value=D(r[5])))

        for r in S["Services"]:
            m.Service.objects.update_or_create(pk=r[0], defaults=dict(
                name=r[1], category=r[2], starting_price=D(r[3]), delivery_days=r[4], status=r[5]))

        for r in S["Requirements"]:
            m.Requirement.objects.update_or_create(pk=r[0], defaults=dict(
                client_id=r[1], requirement=r[2], technology=r[3], approval_status=r[4]))

        for r in S["Proposals"]:
            m.Proposal.objects.update_or_create(pk=r[0], defaults=dict(
                client_id=r[1], project_name=r[2], subtotal=D(r[3]), tax=D(r[4]),
                discount=D(r[5]), total=D(r[6]), status=r[7]))

        for r in S["Projects"]:
            m.Project.objects.update_or_create(pk=r[0], defaults=dict(
                proposal_id=r[1], client_id=r[2], name=r[3], project_manager=r[4],
                status=r[5], completion=r[6], value=D(r[7])))

        for r in S["Tasks"]:
            m.Task.objects.update_or_create(pk=r[0], defaults=dict(
                project_id=r[1], task=r[2], assigned_to=r[3], priority=r[4], status=r[5],
                estimated_hours=D(r[6]), actual_hours=D(r[7])))

        for r in S["Designs"]:
            m.Design.objects.update_or_create(pk=r[0], defaults=dict(
                project_id=r[1], design=r[2], version=r[3], approval_status=r[4]))

        for r in S["Bugs_QA"]:
            m.Bug.objects.update_or_create(pk=r[0], defaults=dict(
                project_id=r[1], bug=r[2], priority=r[3], assigned_to=r[4], status=r[5]))

        for r in S["Websites"]:
            m.Website.objects.update_or_create(pk=r[0], defaults=dict(
                client_id=r[1], project_id=r[2] or None, url=r[3], technology=r[4], deployment_status=r[5]))

        for r in S["Change_Requests"]:
            m.ChangeRequest.objects.update_or_create(pk=r[0], defaults=dict(
                project_id=r[1], client_id=r[2], request=r[3], additional_cost=D(r[4]),
                additional_days=r[5], status=r[6]))

        for r in S["Invoices"]:
            m.Invoice.objects.update_or_create(pk=r[0], defaults=dict(
                client_id=r[1], project_id=r[2], amount=D(r[3]), amount_paid=D(r[4]), status=r[5]))

        for r in S["Payments"]:
            m.Payment.objects.update_or_create(pk=r[0], defaults=dict(
                client_id=r[1], project_id=r[2], invoice_id=r[3], amount=D(r[4]), method=r[5], status=r[6]))

        for r in S["Support_Tickets"]:
            m.SupportTicket.objects.update_or_create(pk=r[0], defaults=dict(
                client_id=r[1], project_id=r[2], subject=r[3], priority=r[4], assigned_to=r[5], status=r[6]))

        for r in S["AMC_Maintenance"]:
            m.AMCPlan.objects.update_or_create(pk=r[0], defaults=dict(
                client_id=r[1], plan_name=r[2], billing_cycle=r[3], fee=D(r[4]), status=r[5]))

        for r in S["Employees"]:
            m.Employee.objects.update_or_create(pk=r[0], defaults=dict(
                name=r[1], role=r[2], department=r[3], status=r[4]))

        for r in S["Timesheets"]:
            m.Timesheet.objects.update_or_create(pk=r[0], defaults=dict(
                employee_id=r[1], project_id=r[2], task_id=r[3], hours=D(r[4]), billable=bool(r[5])))

        for r in S["Meetings"]:
            m.Meeting.objects.update_or_create(pk=r[0], defaults=dict(
                client_id=r[1], project_id=r[2], meeting=r[3], date=parse_date(r[4]),
                time=parse_time(r[5]), platform=r[6], status=r[7]))

        User = get_user_model()
        staff_user = None
        if not opts["no_admin"]:
            staff_user = User.objects.filter(username="admin").first()
            if staff_user is None:
                staff_user = User.objects.create_superuser("admin", "admin@agency.example", "admin123")
                self.stdout.write(self.style.SUCCESS("Created staff user    ->  admin / admin123"))

        self.seed_portal(staff_user)

        self.stdout.write(self.style.SUCCESS("Demo data loaded:"))
        for label, model in [("clients", m.Client), ("leads", m.Lead), ("services", m.Service),
                             ("projects", m.Project), ("tasks", m.Task), ("invoices", m.Invoice),
                             ("payments", m.Payment), ("tickets", m.SupportTicket)]:
            self.stdout.write(f"  {label:<10}{model.objects.count()}")

    # ------------------------------------------------------------------
    def seed_portal(self, staff_user):
        """Client logins, demo conversations, shared documents and notifications."""
        User = get_user_model()
        now = timezone.now()
        client_users = {}

        for client in m.Client.objects.filter(status="Active"):
            username = f"client{client.pk}"
            user = User.objects.filter(username=username).first()
            if user is None:
                first, _, last = client.contact_name.partition(" ")
                user = User.objects.create_user(username, client.email, "client123",
                                                first_name=first, last_name=last)
                self.stdout.write(self.style.SUCCESS(f"Created client login   ->  {username} / client123  ({client.company})"))
            m.ClientProfile.objects.get_or_create(user=user, defaults={"client": client, "job_title": "Primary contact"})
            client_users[client.pk] = user

        # ---- shared documents (small text files so downloads work out of the box)
        if not m.Document.objects.exists():
            docs = [
                # client, project, title, category, filename, from_staff, visible, hours_ago, text
                (1001, 6001, "Nova Retail E-commerce Proposal", "Proposal", "Nova_Retail_Proposal_5001.txt", True, True, 400,
                 "PROPOSAL #5001 - Nova Retail E-commerce Revamp\nSubtotal: Rs 145,000\nTax: Rs 26,100\nTotal: Rs 171,100\nStatus: Accepted\n"),
                (1001, 6001, "Signed Service Agreement", "Contract", "Nova_Service_Agreement.txt", True, True, 380,
                 "SERVICE AGREEMENT (demo)\nBetween PixelForge and Nova Retail Pvt Ltd.\nScope: React / Node.js e-commerce revamp.\n"),
                (1001, 6001, "Invoice INV-2026-001", "Invoice", "INV-2026-001.txt", True, True, 300,
                 "INVOICE INV-2026-001\nAmount: Rs 85,550\nPaid: Rs 85,550\nStatus: Paid\n"),
                (1001, 6001, "Invoice INV-2026-002", "Invoice", "INV-2026-002.txt", True, True, 100,
                 "INVOICE INV-2026-002\nAmount: Rs 85,550\nPaid: Rs 50,000\nOutstanding: Rs 35,550\nStatus: Partially Paid\n"),
                (1001, 6001, "Homepage UI v3 - design notes", "Design", "Homepage_UI_v3_notes.txt", True, True, 60,
                 "Homepage UI v3\n- Hero banner with seasonal offers\n- Sticky header, mobile-first navigation\n- Wishlist icon (see change request 11001)\n"),
                (1001, 6001, "Brand assets - logo & colours", "Content", "Nova_brand_assets.txt", False, True, 250,
                 "Brand colours: #0B5FFF, #101828\nLogo files will be shared via the portal.\n"),
                (1001, 6001, "Internal QA checklist", "Report", "Nova_QA_checklist_internal.txt", True, False, 40,
                 "INTERNAL ONLY - not visible to the client.\nRegression plan for checkout, wishlist, mobile menu.\n"),
                (1002, 6002, "Mehta Foods Website Proposal", "Proposal", "Mehta_Foods_Proposal_5002.txt", True, True, 500,
                 "PROPOSAL #5002 - Mehta Foods Corporate Website\nSubtotal: Rs 78,000\nDiscount: Rs 5,000\nTotal: Rs 87,040\n"),
                (1002, 6002, "Invoice INV-2026-003", "Invoice", "INV-2026-003.txt", True, True, 200,
                 "INVOICE INV-2026-003\nAmount: Rs 87,040\nStatus: Paid\n"),
                (1002, 6002, "Final demo checklist", "Report", "Final_demo_checklist.txt", True, True, 30,
                 "Final Website Demo - 8 Oct 2026, 15:30 (Zoom)\n1. Homepage  2. Catalogue filter  3. Contact form  4. Mobile view\n"),
                (1002, 6002, "Product photo list", "Content", "Product_photos_list.txt", False, True, 220,
                 "List of 24 product photos supplied by Mehta Foods (demo).\n"),
                (1003, 6003, "Verma Tech Client Portal Proposal", "Proposal", "Verma_Portal_Proposal_5003.txt", True, True, 350,
                 "PROPOSAL #5003 - Verma Tech Client Portal\nSubtotal: Rs 240,000\nDiscount: Rs 10,000\nTotal: Rs 273,200\nStatus: Negotiation\n"),
                (1003, 6003, "Invoice INV-2026-004", "Invoice", "INV-2026-004.txt", True, True, 90,
                 "INVOICE INV-2026-004\nAmount: Rs 136,600\nPaid: Rs 0\nStatus: Unpaid\n"),
                (1003, 6003, "API requirements from client", "Other", "Verma_API_requirements.txt", False, True, 150,
                 "Required endpoints: auth, orders, invoices, export to Excel (demo notes).\n"),
                (1005, None, "Singh Manufacturing Proposal (draft)", "Proposal", "Singh_Mfg_Proposal_5004.txt", True, True, 120,
                 "PROPOSAL #5004 - Singh Manufacturing Website\nSubtotal: Rs 95,000\nTotal: Rs 112,100\nStatus: Draft\n"),
                (1005, None, "Maintenance Starter plan terms", "Contract", "Maintenance_Starter_terms.txt", True, True, 70,
                 "Maintenance Starter - monthly Rs 8,000. Status: Pending.\n"),
            ]
            for cid, pid, title, cat, fname, from_staff, visible, hours, text in docs:
                uploader = staff_user if from_staff else client_users.get(cid)
                doc = m.Document(client_id=cid, project_id=pid, title=title, category=cat,
                                 description="Demo document", uploaded_by=uploader, from_staff=from_staff,
                                 visible_to_client=visible, created_at=now - timedelta(hours=hours))
                doc.file.save(fname, ContentFile(text.encode("utf-8")), save=False)
                doc.save()

        # ---- demo conversations
        if not m.Message.objects.exists():
            convo = [
                # client, project, from_staff, hours_ago, is_read, text
                (1001, 6001, True, 70, True, "Hi Aarav, Homepage UI v3 is ready. Please review it in the Projects page."),
                (1001, 6001, False, 66, True, "Looks great! Can we add a wishlist icon in the header?"),
                (1001, 6001, True, 64, True, "Sure - raised as change request 11001 (+Rs 15,000, +3 days). Please approve it in the portal."),
                (1001, 6001, False, 20, True, "Approved. Also, the checkout page shows a wrong total on my phone."),
                (1001, 6001, True, 5, False, "Thanks for reporting. Ticket 13001 is in progress - the fix will be live today."),
                (1002, 6002, True, 52, True, "Hello Priya, the final demo is scheduled for 8 Oct at 15:30 on Zoom."),
                (1002, 6002, False, 48, True, "Perfect. Please update the company address in the footer before the demo."),
                (1002, 6002, True, 46, True, "Done - ticket 13002 is resolved. Please check the footer."),
                (1002, 6002, False, 3, False, "Looks good! One last question - when can we go live?"),
                (1003, 6003, True, 30, True, "Hi Rohan, the staging portal is ready for review (meeting on 9 Oct, 12:00)."),
                (1003, 6003, False, 8, False, "I cannot open the staging portal. It says access denied."),
                (1005, None, True, 12, False, "Hello Vikram, your draft proposal for the manufacturing website is in the Documents page."),
            ]
            for cid, pid, from_staff, hours, is_read, text in convo:
                m.Message.objects.create(
                    client_id=cid, project_id=pid, from_staff=from_staff, body=text, is_read=is_read,
                    sender=staff_user if from_staff else client_users.get(cid),
                    created_at=now - timedelta(hours=hours))

        # ---- notifications
        if not m.Notification.objects.exists():
            for cid, user in client_users.items():
                m.Notification.objects.create(user=user, title="Welcome to your PixelForge client portal", link="/portal/",
                                              created_at=now - timedelta(days=5), is_read=True)
                m.Notification.objects.create(user=user, title="New message from the PixelForge team",
                                              link="/portal/messages/", created_at=now - timedelta(hours=5))
            if 1001 in client_users:
                m.Notification.objects.create(user=client_users[1001], title="Design 'Product Listing UI v2' is waiting for your approval",
                                              link="/portal/projects/6001/", created_at=now - timedelta(hours=18))
            if 1003 in client_users:
                m.Notification.objects.create(user=client_users[1003], title="Change request 'Add export to Excel' needs your approval",
                                              link="/portal/projects/6003/", created_at=now - timedelta(hours=26))
            if staff_user:
                m.Notification.objects.create(user=staff_user, title="New message from Nova Retail Pvt Ltd",
                                              link="/staff/inbox/?client=1001", created_at=now - timedelta(hours=20))
                m.Notification.objects.create(user=staff_user, title="New Critical ticket from Verma Tech Solutions",
                                              link="/staff/tickets/", created_at=now - timedelta(hours=8))
