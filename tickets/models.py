from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Categories'


class Ticket(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='tickets'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='OPEN'
    )
    priority = models.CharField(
        max_length=20, 
        choices=PRIORITY_CHOICES, 
        default='MEDIUM'
    )
    attachment = models.FileField(
        upload_to='ticket_attachments/', 
        null=True, 
        blank=True
    )
    due_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_tickets'
    )
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_tickets'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"#{self.id} - {self.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Auto-calculate SLA due date on ticket creation if not already set
        if not self.pk and not self.due_date:
            now = timezone.now()
            if self.priority == 'URGENT':
                self.due_date = now + timedelta(hours=4)
            elif self.priority == 'HIGH':
                self.due_date = now + timedelta(days=1)
            elif self.priority == 'MEDIUM':
                self.due_date = now + timedelta(days=3)
            else: # LOW
                self.due_date = now + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_sla_breached(self):
        if self.status not in ['RESOLVED', 'CLOSED'] and self.due_date:
            return timezone.now() > self.due_date
        return False

    class Meta:
        ordering = ['-created_at']


class Comment(models.Model):
    ticket = models.ForeignKey(
        Ticket, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='ticket_comments'
    )
    content = models.TextField()
    attachment = models.FileField(
        upload_to='comment_attachments/', 
        null=True, 
        blank=True
    )
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on #{self.ticket.id}"

    class Meta:
        ordering = ['created_at']


class TicketAuditLog(models.Model):
    ticket = models.ForeignKey(
        Ticket, 
        on_delete=models.CASCADE, 
        related_name='audit_logs'
    )
    changed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='ticket_audit_logs'
    )
    field_name = models.CharField(max_length=50)
    old_value = models.CharField(max_length=255, blank=True, null=True)
    new_value = models.CharField(max_length=255, blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Audit log on #{self.ticket.id}: {self.field_name} updated by {self.changed_by.username}"

    class Meta:
        ordering = ['-changed_at']
