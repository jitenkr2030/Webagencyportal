"""Django admin registration - every table is manageable from /admin/."""
from django.contrib import admin

from . import models as m


@admin.register(m.Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "contact_name", "email", "city", "status")
    list_filter = ("status", "city")
    search_fields = ("company", "contact_name", "email")


@admin.register(m.Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "requirement", "lead_source", "status", "estimated_value", "created_at")
    list_filter = ("status", "lead_source")
    search_fields = ("company", "requirement", "email", "contact_name")
    list_editable = ("status",)


@admin.register(m.Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "starting_price", "delivery_days", "status")
    list_filter = ("status", "category")
    search_fields = ("name", "category")


@admin.register(m.Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "requirement", "technology", "approval_status")
    list_filter = ("approval_status",)
    search_fields = ("requirement", "technology", "client__company")


@admin.register(m.Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ("id", "project_name", "client", "subtotal", "tax", "discount", "total", "status")
    list_filter = ("status",)
    search_fields = ("project_name", "client__company")


class TaskInline(admin.TabularInline):
    model = m.Task
    extra = 0


@admin.register(m.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "client", "project_manager", "status", "completion", "value")
    list_filter = ("status", "project_manager")
    search_fields = ("name", "client__company")
    inlines = [TaskInline]


@admin.register(m.Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "project", "assigned_to", "priority", "status", "estimated_hours", "actual_hours")
    list_filter = ("status", "priority", "assigned_to")
    search_fields = ("task", "project__name")


@admin.register(m.Design)
class DesignAdmin(admin.ModelAdmin):
    list_display = ("id", "design", "project", "version", "approval_status")
    list_filter = ("approval_status",)


@admin.register(m.Bug)
class BugAdmin(admin.ModelAdmin):
    list_display = ("id", "bug", "project", "priority", "assigned_to", "status")
    list_filter = ("status", "priority")
    search_fields = ("bug",)


@admin.register(m.Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ("id", "url", "client", "project", "technology", "deployment_status")
    list_filter = ("deployment_status",)


@admin.register(m.ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "project", "client", "additional_cost", "additional_days", "status")
    list_filter = ("status",)


@admin.register(m.Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_no", "client", "project", "amount", "amount_paid", "status")
    list_filter = ("status",)
    search_fields = ("invoice_no", "client__company")


@admin.register(m.Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice", "client", "project", "amount", "method", "status")
    list_filter = ("status", "method")


@admin.register(m.SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "client", "project", "priority", "assigned_to", "status")
    list_filter = ("status", "priority")
    search_fields = ("subject", "client__company")


@admin.register(m.AMCPlan)
class AMCPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "plan_name", "client", "billing_cycle", "fee", "status")
    list_filter = ("status", "billing_cycle")


@admin.register(m.Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "role", "department", "status")
    list_filter = ("department", "status")
    search_fields = ("name", "role")


@admin.register(m.Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "project", "task", "hours", "billable")
    list_filter = ("billable", "employee")


@admin.register(m.Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("id", "meeting", "client", "project", "date", "time", "platform", "status")
    list_filter = ("status", "platform")


@admin.register(m.ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "client", "job_title", "phone")
    search_fields = ("user__username", "client__company")


@admin.register(m.Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "client", "project", "category", "from_staff", "visible_to_client", "created_at")
    list_filter = ("category", "from_staff", "visible_to_client")
    search_fields = ("title", "client__company")


@admin.register(m.Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "project", "from_staff", "short_body", "is_read", "created_at")
    list_filter = ("from_staff", "is_read")
    search_fields = ("body", "client__company")

    @admin.display(description="Message")
    def short_body(self, obj):
        return obj.body[:60]


@admin.register(m.Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read",)
