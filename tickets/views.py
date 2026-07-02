from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
import json
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count

from django.contrib.messages.views import SuccessMessageMixin

from .models import Ticket, Comment, Category, TicketAuditLog
from .forms import TicketCreateForm, TicketUpdateForm, CommentForm, UserProfileForm

class CustomLoginView(LoginView):
    template_name = 'tickets/login.html'
    redirect_authenticated_user = True


class DashboardView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = 'tickets/dashboard.html'
    context_object_name = 'tickets'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            queryset = Ticket.objects.all()
        else:
            queryset = Ticket.objects.filter(created_by=user)

        # Filters
        status = self.request.GET.get('status')
        priority = self.request.GET.get('priority')
        category = self.request.GET.get('category')
        assigned_to = self.request.GET.get('assigned_to')
        q = self.request.GET.get('q')

        if status:
            queryset = queryset.filter(status=status)
        if priority:
            queryset = queryset.filter(priority=priority)
        if category:
            queryset = queryset.filter(category_id=category)
        if assigned_to:
            if assigned_to == 'unassigned':
                queryset = queryset.filter(assigned_to__isnull=True)
            else:
                queryset = queryset.filter(assigned_to_id=assigned_to)
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | 
                Q(description__icontains=q) |
                Q(id__icontains=q)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get base queryset for counters based on permission
        base_qs = Ticket.objects.all() if user.is_staff else Ticket.objects.filter(created_by=user)
        
        # Calculate dashboard metrics
        stats = base_qs.aggregate(
            total=Count('id'),
            open_count=Count('id', filter=Q(status='OPEN')),
            progress_count=Count('id', filter=Q(status='IN_PROGRESS')),
            resolved_count=Count('id', filter=Q(status='RESOLVED')),
            closed_count=Count('id', filter=Q(status='CLOSED')),
            urgent_count=Count('id', filter=Q(priority='URGENT'))
        )
        context.update(stats)
        
        # Pass filter lists
        context['agents'] = User.objects.filter(is_staff=True)
        context['categories'] = Category.objects.all()
        
        # Calculate Category breakdown for Chart.js
        cat_counts = base_qs.values('category__name').annotate(count=Count('id'))
        category_chart_data = {'labels': [], 'values': []}
        for item in cat_counts:
            cat_name = item['category__name'] or 'Uncategorized'
            category_chart_data['labels'].append(cat_name)
            category_chart_data['values'].append(item['count'])

        # Serialize charts data
        context['status_chart_json'] = json.dumps({
            'labels': ['Open', 'In Progress', 'Resolved', 'Closed'],
            'values': [stats['open_count'], stats['progress_count'], stats['resolved_count'], stats['closed_count']]
        })
        context['category_chart_json'] = json.dumps(category_chart_data)

        # Preserve filters in context for form elements
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_priority'] = self.request.GET.get('priority', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_assigned_to'] = self.request.GET.get('assigned_to', '')
        context['search_query'] = self.request.GET.get('q', '')

        return context


class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = 'tickets/detail.html'
    context_object_name = 'ticket'

    def get_object(self, queryset=None):
        ticket = super().get_object(queryset)
        if not self.request.user.is_staff and ticket.created_by != self.request.user:
            raise PermissionDenied("You do not have permission to view this ticket.")
        return ticket

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CommentForm(user=self.request.user)
        if self.request.user.is_staff:
            context['agents'] = User.objects.filter(is_staff=True)
        
        # Filter comments: clients only see public ones
        if self.request.user.is_staff:
            comments = self.object.comments.all()
        else:
            comments = self.object.comments.filter(is_internal=False)
            
        audit_logs = self.object.audit_logs.all()

        # Combine into unified chronological timeline
        timeline = []
        for comment in comments:
            timeline.append({
                'type': 'comment',
                'timestamp': comment.created_at,
                'item': comment
            })
        for log in audit_logs:
            timeline.append({
                'type': 'audit',
                'timestamp': log.changed_at,
                'item': log
            })
            
        # Sort oldest to newest for chronological conversation flow
        timeline.sort(key=lambda x: x['timestamp'])
        context['timeline'] = timeline

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Staff Actions (Status & Assignment changes)
        if request.user.is_staff:
            if 'update_status' in request.POST:
                new_status = request.POST.get('status')
                if new_status in dict(Ticket.STATUS_CHOICES) and new_status != self.object.status:
                    old_display = self.object.get_status_display()
                    self.object.status = new_status
                    self.object.save()
                    new_display = self.object.get_status_display()
                    
                    # Log Audit Entry
                    TicketAuditLog.objects.create(
                        ticket=self.object,
                        changed_by=request.user,
                        field_name='status',
                        old_value=old_display,
                        new_value=new_display
                    )
                    return redirect('tickets:ticket_detail', pk=self.object.pk)

            if 'assign_agent' in request.POST:
                agent_id = request.POST.get('assigned_to')
                old_assignee_name = self.object.assigned_to.username if self.object.assigned_to else 'Unassigned'
                
                if agent_id:
                    agent = get_object_or_404(User, id=agent_id, is_staff=True)
                    if self.object.assigned_to != agent:
                        self.object.assigned_to = agent
                        self.object.save()
                        TicketAuditLog.objects.create(
                            ticket=self.object,
                            changed_by=request.user,
                            field_name='assigned_to',
                            old_value=old_assignee_name,
                            new_value=agent.username
                        )
                else:
                    if self.object.assigned_to is not None:
                        self.object.assigned_to = None
                        self.object.save()
                        TicketAuditLog.objects.create(
                            ticket=self.object,
                            changed_by=request.user,
                            field_name='assigned_to',
                            old_value=old_assignee_name,
                            new_value='Unassigned'
                        )
                return redirect('tickets:ticket_detail', pk=self.object.pk)

        # Comment Actions
        form = CommentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = self.object
            comment.author = request.user
            comment.save()
            return redirect('tickets:ticket_detail', pk=self.object.pk)
        
        context = self.get_context_data()
        context['comment_form'] = form
        return render(request, self.template_name, context)


class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketCreateForm
    template_name = 'tickets/ticket_form.html'
    success_url = reverse_lazy('tickets:dashboard')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.status = 'OPEN'
        return super().form_valid(form)


class TicketEditView(LoginRequiredMixin, UpdateView):
    model = Ticket
    template_name = 'tickets/ticket_form.html'

    def get_form_class(self):
        if self.request.user.is_staff:
            return TicketUpdateForm
        return TicketCreateForm

    def get_object(self, queryset=None):
        ticket = super().get_object(queryset)
        is_owner = ticket.created_by == self.request.user
        is_staff = self.request.user.is_staff
        if not (is_staff or (is_owner and ticket.status == 'OPEN')):
            raise PermissionDenied("You do not have permission to edit this ticket.")
        return ticket

    def form_valid(self, form):
        ticket = form.save(commit=False)
        original = Ticket.objects.get(pk=ticket.pk)
        changes = []

        # Audit comparison
        if original.title != ticket.title:
            changes.append(('title', original.title, ticket.title))
        if original.description != ticket.description:
            changes.append(('description', 'Modified details', 'Modified details'))
        if original.priority != ticket.priority:
            changes.append(('priority', original.get_priority_display(), ticket.get_priority_display()))
        if original.category != ticket.category:
            changes.append(('category', original.category.name if original.category else 'None', ticket.category.name if ticket.category else 'None'))
        if original.status != ticket.status:
            changes.append(('status', original.get_status_display(), ticket.get_status_display()))
        if original.assigned_to != ticket.assigned_to:
            changes.append(('assigned_to', original.assigned_to.username if original.assigned_to else 'Unassigned', ticket.assigned_to.username if ticket.assigned_to else 'Unassigned'))

        response = super().form_valid(form)

        # Log audit entries
        for field, old, new in changes:
            TicketAuditLog.objects.create(
                ticket=self.object,
                changed_by=self.request.user,
                field_name=field,
                old_value=old,
                new_value=new
            )

        return response

    def get_success_url(self):
        return reverse('tickets:ticket_detail', kwargs={'pk': self.object.pk})


class UserProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = 'tickets/profile.html'
    success_url = reverse_lazy('tickets:profile')
    success_message = "Your profile details were updated successfully!"

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Calculate stats for the user
        if user.is_staff:
            assigned_qs = Ticket.objects.filter(assigned_to=user)
            context['total_tickets'] = assigned_qs.count()
            context['open_tickets'] = assigned_qs.filter(status='OPEN').count()
            context['progress_tickets'] = assigned_qs.filter(status='IN_PROGRESS').count()
            context['resolved_tickets'] = assigned_qs.filter(status__in=['RESOLVED', 'CLOSED']).count()
            context['recent_tickets'] = assigned_qs.order_by('-created_at')[:3]
        else:
            created_qs = Ticket.objects.filter(created_by=user)
            context['total_tickets'] = created_qs.count()
            context['open_tickets'] = created_qs.filter(status='OPEN').count()
            context['progress_tickets'] = created_qs.filter(status='IN_PROGRESS').count()
            context['resolved_tickets'] = created_qs.filter(status__in=['RESOLVED', 'CLOSED']).count()
            context['recent_tickets'] = created_qs.order_by('-created_at')[:3]
            
        return context


class ClassifyTicketView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            text = data.get('text', '').lower()
        except (json.JSONDecodeError, TypeError):
            text = ''

        predicted_category = None
        predicted_priority = 'MEDIUM'

        # Keyword mapping for Heuristic AI suggestion
        category_keywords = {
            'network': ['internet', 'wifi', 'router', 'vpn', 'connection', 'port', 'network', 'timeout', 'smtp', 'relay', 'offline'],
            'hardware': ['keyboard', 'mouse', 'printer', 'display', 'monitor', 'laptop', 'pc', 'broken', 'flicker', 'screen', 'paper jam', 'jam', 'cable', 'hardware'],
            'software': ['software', 'install', 'slack', 'jira', 'chrome', 'app', 'license', 'update', 'failing', 'error', 'webhooks', 'bug', 'crash'],
            'access-request': ['password', 'reset', 'access', 'permission', 'login', 'auth', 'account', 'unlock', 'ldap', 'active directory', 'credentials']
        }

        priority_keywords = {
            'URGENT': ['server down', 'emergency', 'crash', 'critical', 'blocked', 'urgent', 'relay denied', 'cannot work', 'outage'],
            'HIGH': ['failing', 'cannot login', 'timeout', 'no access', 'high', 'jammed', 'broken completely', 'dead'],
            'MEDIUM': ['slow', 'flickering', 'error', 'medium', 'webhook', 'warning'],
            'LOW': ['requesting', 'keyboard', 'mouse', 'new set', 'low', 'install', 'setup', 'update']
        }

        # Analyze keywords in text
        for cat_slug, keywords in category_keywords.items():
            if any(word in text for word in keywords):
                predicted_category = cat_slug
                break

        for prio_choice, keywords in priority_keywords.items():
            if any(word in text for word in keywords):
                predicted_priority = prio_choice
                break

        response_data = {
            'category_id': None,
            'category_name': None,
            'priority': predicted_priority
        }

        if predicted_category:
            try:
                cat_obj = Category.objects.get(slug=predicted_category)
                response_data['category_id'] = cat_obj.id
                response_data['category_name'] = cat_obj.name
            except Category.DoesNotExist:
                pass

        return JsonResponse(response_data)


from django.contrib import messages
from .forms import CustomUserCreationForm

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'tickets/signup.html'
    success_url = reverse_lazy('tickets:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Account created successfully! You can now log in.")
        return response


