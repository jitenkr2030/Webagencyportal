import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ChangeRequest, Design, Document, Lead, Message, Notification
from .services import dashboard_metrics

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class PortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    # ------------------------------------------------ public pages
    def test_index_is_home(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "portal/index.html")

    def test_enquiry_creates_lead(self):
        before = Lead.objects.count()
        self.client.post("/", {"contact_name": "Test", "company": "Acme", "email": "t@acme.example",
                               "service": 3001, "message": "Hi"})
        self.assertEqual(Lead.objects.count(), before + 1)

    def test_dashboard_matches_excel(self):
        m = dashboard_metrics()
        self.assertEqual(m["total_clients"], 5)
        self.assertEqual(m["active_projects"], 1)
        self.assertEqual(int(m["invoice_value"]), 394740)
        self.assertEqual(int(m["collected"]), 222590)
        self.assertEqual(int(m["outstanding"]), 172150)

    # ------------------------------------------------ access control
    def test_clients_page_is_staff_only(self):
        self.assertEqual(self.client.get(reverse("clients")).status_code, 302)
        self.client.login(username="client1001", password="client123")
        self.assertEqual(self.client.get(reverse("clients")).status_code, 302)
        self.client.login(username="admin", password="admin123")
        self.assertContains(self.client.get(reverse("clients")), "Nova Retail")

    def test_portal_requires_login(self):
        r = self.client.get(reverse("client_dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("client_login"), r["Location"])

    def test_staff_cannot_open_client_portal_and_client_cannot_open_staff(self):
        self.client.login(username="admin", password="admin123")
        self.assertEqual(self.client.get(reverse("client_dashboard")).status_code, 302)
        self.client.logout()
        self.client.login(username="client1001", password="client123")
        self.assertEqual(self.client.get(reverse("staff_dashboard")).status_code, 302)
        self.assertEqual(self.client.get(reverse("staff_inbox")).status_code, 302)

    def test_client_login_flow(self):
        r = self.client.post(reverse("client_login"), {"username": "client1001", "password": "client123"})
        self.assertRedirects(r, reverse("client_dashboard"), fetch_redirect_response=False)
        page = self.client.get(reverse("client_dashboard"))
        self.assertContains(page, "Nova Retail")
        self.assertNotContains(page, "Mehta Foods")

    def test_staff_login_flow(self):
        r = self.client.post(reverse("admin_login"), {"username": "admin", "password": "admin123"})
        self.assertRedirects(r, reverse("staff_dashboard"), fetch_redirect_response=False)

    def test_client_cannot_use_staff_login(self):
        self.client.post(reverse("admin_login"), {"username": "client1001", "password": "client123"})
        self.assertEqual(self.client.get(reverse("staff_dashboard")).status_code, 302)

    # ------------------------------------------------ data isolation
    def test_client_sees_only_own_project(self):
        self.client.login(username="client1001", password="client123")
        self.assertEqual(self.client.get(reverse("client_project_detail", args=[6001])).status_code, 200)
        self.assertEqual(self.client.get(reverse("client_project_detail", args=[6002])).status_code, 404)

    def test_document_permissions(self):
        mine = Document.objects.filter(client_id=1001, visible_to_client=True).first()
        other = Document.objects.filter(client_id=1002).first()
        internal = Document.objects.filter(client_id=1001, visible_to_client=False).first()
        self.client.login(username="client1001", password="client123")
        self.assertEqual(self.client.get(reverse("document_download", args=[mine.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("document_download", args=[other.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("document_download", args=[internal.pk])).status_code, 404)
        self.client.logout()
        self.client.login(username="admin", password="admin123")
        self.assertEqual(self.client.get(reverse("document_download", args=[internal.pk])).status_code, 200)

    # ------------------------------------------------ communication
    def test_client_sends_message_and_staff_is_notified(self):
        self.client.login(username="client1001", password="client123")
        r = self.client.post(reverse("client_messages"), {"body": "Hello team", "project": 6001})
        self.assertEqual(r.status_code, 302)
        msg = Message.objects.filter(client_id=1001, from_staff=False, body="Hello team").first()
        self.assertIsNotNone(msg)
        admin = get_user_model().objects.get(username="admin")
        self.assertTrue(Notification.objects.filter(user=admin, title__contains="Nova Retail").exists())

    def test_empty_message_rejected(self):
        self.client.login(username="client1001", password="client123")
        before = Message.objects.count()
        self.client.post(reverse("client_messages"), {"body": "   "})
        self.assertEqual(Message.objects.count(), before)

    def test_staff_reply_notifies_client_and_marks_read(self):
        self.client.login(username="admin", password="admin123")
        self.client.post(f"{reverse('staff_inbox')}?client=1001", {"body": "Reply from staff"})
        self.assertTrue(Message.objects.filter(client_id=1001, from_staff=True, body="Reply from staff").exists())
        user = get_user_model().objects.get(username="client1001")
        self.assertTrue(Notification.objects.filter(user=user, title__contains="New message").exists())
        self.assertFalse(Message.objects.filter(client_id=1001, from_staff=False, is_read=False).exists())

    # ------------------------------------------------ documents
    def test_client_upload_and_type_validation(self):
        self.client.login(username="client1001", password="client123")
        good = SimpleUploadedFile("brief.pdf", b"%PDF-1.4 demo", content_type="application/pdf")
        r = self.client.post(reverse("client_documents"), {"title": "Brief", "category": "Other", "file": good})
        self.assertEqual(r.status_code, 302)
        doc = Document.objects.get(title="Brief")
        self.assertFalse(doc.from_staff)
        bad = SimpleUploadedFile("evil.exe", b"MZ", content_type="application/octet-stream")
        self.client.post(reverse("client_documents"), {"title": "Bad", "category": "Other", "file": bad})
        self.assertFalse(Document.objects.filter(title="Bad").exists())

    def test_client_cannot_delete_staff_document(self):
        staff_doc = Document.objects.filter(client_id=1001, from_staff=True).first()
        self.client.login(username="client1001", password="client123")
        self.assertEqual(self.client.post(reverse("document_delete", args=[staff_doc.pk])).status_code, 404)
        self.assertTrue(Document.objects.filter(pk=staff_doc.pk).exists())

    # ------------------------------------------------ approvals
    def test_design_approval(self):
        self.client.login(username="client1001", password="client123")
        self.client.post(reverse("design_respond", args=[8002]), {"decision": "approve", "feedback": "Nice"})
        self.assertEqual(Design.objects.get(pk=8002).approval_status, "Client Approved")

    def test_client_cannot_answer_other_clients_change_request(self):
        self.client.login(username="client1001", password="client123")
        r = self.client.post(reverse("change_request_respond", args=[11003]), {"decision": "approve"})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(ChangeRequest.objects.get(pk=11003).status, "Pending Client Approval")

    def test_logout_requires_post(self):
        self.client.login(username="client1001", password="client123")
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.client.post(reverse("logout"))
        self.assertEqual(self.client.get(reverse("client_dashboard")).status_code, 302)

    # ------------------------------------------------ every page renders
    def test_all_client_pages_render(self):
        self.client.login(username="client1003", password="client123")
        for name in ["client_dashboard", "client_projects", "client_invoices", "client_messages",
                     "client_documents", "client_support", "client_meetings", "notifications"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get(reverse("client_project_detail", args=[6003])).status_code, 200)

    def test_all_staff_pages_render(self):
        self.client.login(username="admin", password="admin123")
        for name in ["staff_dashboard", "staff_inbox", "staff_documents", "staff_tickets",
                     "staff_accounts", "clients", "notifications"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get(f"{reverse('staff_inbox')}?client=1003").status_code, 200)
        self.assertEqual(self.client.get(f"{reverse('clients')}?client=1001").status_code, 200)

    def test_staff_can_create_client_login(self):
        self.client.login(username="admin", password="admin123")
        self.client.post(reverse("staff_accounts"), {"action": "create", "client_id": 1004, "username": "kapoor"})
        self.assertTrue(get_user_model().objects.filter(username="kapoor", client_profile__client_id=1004).exists())
