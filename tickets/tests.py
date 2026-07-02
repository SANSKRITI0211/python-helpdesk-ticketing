from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
import json

from tickets.models import Ticket, Comment, Category, TicketAuditLog

class AdvancedHelpdeskTestCase(TestCase):
    def setUp(self):
        # Create test users
        self.client_user = User.objects.create_user(
            username='client_user', 
            email='client@example.com', 
            password='password123'
        )
        self.agent_user = User.objects.create_user(
            username='agent_user', 
            email='agent@example.com', 
            password='password123'
        )
        self.agent_user.is_staff = True
        self.agent_user.save()

        # Create Categories
        self.cat_hardware = Category.objects.create(name='Hardware', slug='hardware')
        self.cat_network = Category.objects.create(name='Network', slug='network')

        # Create base tickets
        self.ticket1 = Ticket.objects.create(
            title='Client Hardware Issue',
            description='Broken laptop key.',
            category=self.cat_hardware,
            status='OPEN',
            priority='MEDIUM',
            created_by=self.client_user
        )

    def test_sla_calculation_on_creation(self):
        """SLA due dates are automatically calculated based on Priority."""
        now = timezone.now()
        
        # Test Urgent (4 Hours)
        t_urgent = Ticket.objects.create(
            title='Urgent Server Down',
            description='Down.',
            priority='URGENT',
            created_by=self.client_user
        )
        self.assertAlmostEqual(t_urgent.due_date, now + timedelta(hours=4), delta=timedelta(seconds=5))
        self.assertFalse(t_urgent.is_sla_breached)

        # Test High (1 Day)
        t_high = Ticket.objects.create(
            title='High Priority request',
            description='Description.',
            priority='HIGH',
            created_by=self.client_user
        )
        self.assertAlmostEqual(t_high.due_date, now + timedelta(days=1), delta=timedelta(seconds=5))

        # Test Low (7 Days)
        t_low = Ticket.objects.create(
            title='Low Priority issue',
            description='Description.',
            priority='LOW',
            created_by=self.client_user
        )
        self.assertAlmostEqual(t_low.due_date, now + timedelta(days=7), delta=timedelta(seconds=5))

    def test_sla_breached_property(self):
        """Ticket property is_sla_breached correctly returns true for past due dates."""
        t_overdue = Ticket.objects.create(
            title='Overdue ticket',
            description='Overdue.',
            priority='MEDIUM',
            created_by=self.client_user
        )
        # Manually backdate the due_date
        t_overdue.due_date = timezone.now() - timedelta(hours=1)
        t_overdue.save()
        
        self.assertTrue(t_overdue.is_sla_breached)

        # SLA breach should NOT be true if Resolved or Closed
        t_overdue.status = 'RESOLVED'
        t_overdue.save()
        self.assertFalse(t_overdue.is_sla_breached)

    def test_internal_note_visibility(self):
        """Internal notes can only be viewed in detail view timeline by staff/agents."""
        # Create normal comment
        Comment.objects.create(
            ticket=self.ticket1,
            author=self.agent_user,
            content='This is a public comment.',
            is_internal=False
        )
        # Create internal comment
        internal_comment = Comment.objects.create(
            ticket=self.ticket1,
            author=self.agent_user,
            content='This is an internal note.',
            is_internal=True
        )

        detail_url = reverse('tickets:ticket_detail', kwargs={'pk': self.ticket1.pk})

        # Login as Client
        self.client.login(username='client_user', password='password123')
        response = self.client.get(detail_url)
        timeline_items = [event['item'] for event in response.context['timeline'] if event['type'] == 'comment']
        
        # Client should see public comment but NOT internal note
        self.assertEqual(len(timeline_items), 1)
        self.assertEqual(timeline_items[0].content, 'This is a public comment.')

        # Login as Agent
        self.client.login(username='agent_user', password='password123')
        response = self.client.get(detail_url)
        timeline_items = [event['item'] for event in response.context['timeline'] if event['type'] == 'comment']
        
        # Agent should see BOTH comments
        self.assertEqual(len(timeline_items), 2)
        self.assertIn(internal_comment, timeline_items)

    def test_file_upload_ticket_and_comments(self):
        """File attachments are uploaded and stored successfully."""
        self.client.login(username='client_user', password='password123')
        
        # Mock file
        test_file = SimpleUploadedFile("log.txt", b"error file contents", content_type="text/plain")
        
        create_url = reverse('tickets:ticket_create')
        data = {
            'title': 'Ticket with upload',
            'category': self.cat_network.id,
            'description': 'Description with attachment.',
            'priority': 'LOW',
            'attachment': test_file
        }
        
        response = self.client.post(create_url, data)
        self.assertEqual(response.status_code, 302)
        
        # Verify ticket and attachment exist in database
        ticket = Ticket.objects.get(title='Ticket with upload')
        self.assertTrue(ticket.attachment.name.endswith('log.txt'))
        
        # Clean up files created
        ticket.attachment.delete()

    def test_audit_logging_on_detail_quick_actions(self):
        """Status and assignment updates generate TicketAuditLog entries."""
        self.client.login(username='agent_user', password='password123')
        detail_url = reverse('tickets:ticket_detail', kwargs={'pk': self.ticket1.pk})

        # 1. Test Quick Status Update Audit
        data = {
            'update_status': '1',
            'status': 'RESOLVED'
        }
        response = self.client.post(detail_url, data)
        self.assertEqual(response.status_code, 302)

        audit_logs = TicketAuditLog.objects.filter(ticket=self.ticket1, field_name='status')
        self.assertEqual(audit_logs.count(), 1)
        self.assertEqual(audit_logs[0].old_value, 'Open')
        self.assertEqual(audit_logs[0].new_value, 'Resolved')
        self.assertEqual(audit_logs[0].changed_by, self.agent_user)

        # 2. Test Quick Reassignment Audit
        data = {
            'assign_agent': '1',
            'assigned_to': self.agent_user.id
        }
        response = self.client.post(detail_url, data)
        self.assertEqual(response.status_code, 302)

        assign_logs = TicketAuditLog.objects.filter(ticket=self.ticket1, field_name='assigned_to')
        self.assertEqual(assign_logs.count(), 1)
        self.assertEqual(assign_logs[0].old_value, 'Unassigned')
        self.assertEqual(assign_logs[0].new_value, 'agent_user')

    def test_category_filtering_on_dashboard(self):
        """Dashboard filters querysets correctly by category."""
        # Create second ticket under self.cat_network
        t_net = Ticket.objects.create(
            title='Client Network Issue',
            description='No internet.',
            category=self.cat_network,
            status='OPEN',
            priority='HIGH',
            created_by=self.client_user
        )

        self.client.login(username='client_user', password='password123')
        
        # Filter by Hardware Category
        response = self.client.get(reverse('tickets:dashboard'), {'category': self.cat_hardware.id})
        tickets = response.context['tickets']
        self.assertIn(self.ticket1, tickets)
        self.assertNotIn(t_net, tickets)

        # Filter by Network Category
        response = self.client.get(reverse('tickets:dashboard'), {'category': self.cat_network.id})
        tickets = response.context['tickets']
        self.assertNotIn(self.ticket1, tickets)
        self.assertIn(t_net, tickets)

    def test_user_profile_view_and_update(self):
        """User profile page restricts unauthorized access and saves updates."""
        profile_url = reverse('tickets:profile')
        
        # 1. Anonymous user redirect
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 302)
        
        # 2. Login client and retrieve page
        self.client.login(username='client_user', password='password123')
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_tickets'], 1) # client_user has ticket1
        
        # 3. Post profile changes
        data = {
            'first_name': 'Testy',
            'last_name': 'User',
            'email': 'new_test_email@example.com'
        }
        response = self.client.post(profile_url, data)
        self.assertEqual(response.status_code, 302) # Redirect to success url
        
        # Verify db record update
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.first_name, 'Testy')
        self.assertEqual(self.client_user.last_name, 'User')
        self.assertEqual(self.client_user.email, 'new_test_email@example.com')

    def test_ai_classification_api(self):
        """AI Classification API returns correct predictions based on keyword matches."""
        classify_url = reverse('tickets:api_classify')
        self.client.login(username='client_user', password='password123')

        # 1. Test Hardware & Low Priority keywords
        data = {'text': 'I need a new keyboard and wireless mouse for my office.'}
        response = self.client.post(classify_url, json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.content)
        self.assertEqual(res_data['category_id'], self.cat_hardware.id)
        self.assertEqual(res_data['category_name'], 'Hardware')
        self.assertEqual(res_data['priority'], 'LOW')

        # 2. Test Network & Urgent Priority keywords
        data = {'text': 'Critical server down VPN connection timeout outage! Help.'}
        response = self.client.post(classify_url, json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.content)
        self.assertEqual(res_data['category_id'], self.cat_network.id)
        self.assertEqual(res_data['category_name'], 'Network')
        self.assertEqual(res_data['priority'], 'URGENT')

    def test_signup_flow(self):
        """Visitors can create accounts successfully."""
        signup_url = reverse('tickets:signup')
        
        # Test Get request
        response = self.client.get(signup_url)
        self.assertEqual(response.status_code, 200)
        
        # Test Post request with valid data
        data = {
            'username': 'newly_registered_user',
            'password1': 'strongpass123',
            'password2': 'strongpass123'
        }
        response = self.client.post(signup_url, data)
        self.assertEqual(response.status_code, 302) # Redirects to login on success
        
        # Verify user is created in database
        user_exists = User.objects.filter(username='newly_registered_user').exists()
        self.assertTrue(user_exists)



