import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'helpdesk_project.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import Ticket, Comment, Category, TicketAuditLog

def seed():
    print("Seeding database...")
    
    # 1. Create Users
    # Admin
    if not User.objects.filter(username='admin').exists():
        admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("Created superuser: admin (pw: admin123)")
    else:
        admin = User.objects.get(username='admin')

    # Agents (Staff)
    agents = []
    agent_data = [
        ('agent1', 'agent1@example.com', 'agent123'),
        ('agent2', 'agent2@example.com', 'agent123'),
    ]
    for username, email, password in agent_data:
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(username, email, password)
            user.is_staff = True
            user.save()
            print(f"Created Agent: {username} (pw: {password})")
            agents.append(user)
        else:
            agents.append(User.objects.get(username=username))

    # Clients (Submitters)
    clients = []
    client_data = [
        ('client1', 'client1@example.com', 'client123'),
        ('client2', 'client2@example.com', 'client123'),
    ]
    for username, email, password in client_data:
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(username, email, password)
            print(f"Created Client: {username} (pw: {password})")
            clients.append(user)
        else:
            clients.append(User.objects.get(username=username))

    # Clear old tickets & comments & categories
    TicketAuditLog.objects.all().delete()
    Comment.objects.all().delete()
    Ticket.objects.all().delete()
    Category.objects.all().delete()
    print("Cleared existing database records.")

    # 2. Create Categories
    categories = {}
    cat_list = [
        ('Network', 'network', 'Issues related to WiFi, VPN, routers, and switches.'),
        ('Hardware', 'hardware', 'Issues with keyboards, monitors, laptops, and printers.'),
        ('Software', 'software', 'Issues with corporate software, operating systems, and installations.'),
        ('Access Request', 'access-request', 'Requests for directory access, tool permissions, or password resets.')
    ]
    for name, slug, desc in cat_list:
        cat = Category.objects.create(name=name, slug=slug, description=desc)
        print(f"Created category: {name}")
        categories[slug] = cat

    # 3. Create Tickets
    tickets_to_create = [
        {
            'title': 'Email server not sending external emails',
            'description': 'Since this morning, we are unable to send emails outside our domain. The error message is SMTP 550 Relay Denied.',
            'status': 'OPEN',
            'priority': 'URGENT',
            'category': categories['network'],
            'created_by': clients[0],
            'assigned_to': None,
            'comments': []
        },
        {
            'title': 'Requesting new keyboard and mouse set',
            'description': 'My current keyboard has a broken Enter key. Looking for a standard replacement, preferably wireless.',
            'status': 'OPEN',
            'priority': 'LOW',
            'category': categories['hardware'],
            'created_by': clients[1],
            'assigned_to': agents[0],
            'comments': [
                (agents[0], 'I will check the inventory in the IT closet. If we have one, I will drop it off today.', False)
            ]
        },
        {
            'title': 'VPN connection timeout issues',
            'description': 'Every time I try to connect to the corporate VPN from home, it hangs at "Connecting" and then times out after 2 minutes.',
            'status': 'IN_PROGRESS',
            'priority': 'HIGH',
            'category': categories['network'],
            'created_by': clients[0],
            'assigned_to': agents[1],
            'comments': [
                (agents[1], 'Could you please check your router firewall? Sometimes NAT blocks IPSec traffic.', False),
                (agents[1], 'System log: Checked Active Directory state for client1. Account status: Active.', True),
                (clients[0], 'I disabled my router firewall temporarily, but the timeout still occurs.', False),
                (agents[1], 'Thanks for checking. I will review the VPN concentrator logs for your IP next.', False)
            ]
        },
        {
            'title': 'Printer paper jam in Room 402',
            'description': 'The main multi-function printer in Room 402 is showing a "Jam at Tray 2" error and won\'t print.',
            'status': 'RESOLVED',
            'priority': 'MEDIUM',
            'category': categories['hardware'],
            'created_by': clients[1],
            'assigned_to': agents[0],
            'comments': [
                (agents[0], 'I cleared the jammed paper from the roller and ran a test page. Printer is working.', False),
                (clients[1], 'Tested it and it is working. Thank you!', False)
            ]
        },
        {
            'title': 'Slack integration with Jira failing',
            'description': 'The webhooks between Jira and Slack seem to be broken. Ticket notifications are no longer appearing in the #tech-alerts channel.',
            'status': 'CLOSED',
            'priority': 'MEDIUM',
            'category': categories['software'],
            'created_by': clients[0],
            'assigned_to': admin,
            'comments': [
                (admin, 'The webhook URL in Jira settings was outdated. I have updated it with the new active URL.', False),
                (clients[0], 'Awesome, verified. Notifications are appearing again. Closing this out.', False)
            ]
        }
    ]

    for item in tickets_to_create:
        ticket = Ticket.objects.create(
            title=item['title'],
            description=item['description'],
            status=item['status'],
            priority=item['priority'],
            category=item['category'],
            created_by=item['created_by'],
            assigned_to=item['assigned_to']
        )
        print(f"Created ticket: {ticket.title}")

        # Seed audit entries to show some history logs in detail views
        if ticket.assigned_to:
            TicketAuditLog.objects.create(
                ticket=ticket,
                changed_by=admin,
                field_name='assigned_to',
                old_value='Unassigned',
                new_value=ticket.assigned_to.username
            )
        if ticket.status != 'OPEN':
            TicketAuditLog.objects.create(
                ticket=ticket,
                changed_by=ticket.assigned_to or admin,
                field_name='status',
                old_value='Open',
                new_value=ticket.get_status_display()
            )

        for author, content, is_int in item['comments']:
            Comment.objects.create(
                ticket=ticket,
                author=author,
                content=content,
                is_internal=is_int
            )
            print(f"  Added comment from {author.username} (Internal: {is_int})")

    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed()
