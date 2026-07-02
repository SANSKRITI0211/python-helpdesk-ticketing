from django.contrib import admin
from .models import Ticket, Comment, Category, TicketAuditLog

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'status', 'priority', 'created_by', 'assigned_to', 'due_date', 'created_at')
    list_filter = ('status', 'priority', 'category', 'created_at')
    search_fields = ('title', 'description', 'created_by__username', 'assigned_to__username')
    list_editable = ('status', 'priority', 'assigned_to', 'category')
    date_hierarchy = 'created_at'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'author', 'is_internal', 'created_at')
    list_filter = ('is_internal', 'created_at')
    search_fields = ('content', 'author__username', 'ticket__title')


@admin.register(TicketAuditLog)
class TicketAuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'changed_by', 'field_name', 'old_value', 'new_value', 'changed_at')
    list_filter = ('field_name', 'changed_at')
    search_fields = ('ticket__title', 'changed_by__username')
