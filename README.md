# HelpDesk - IT Ticketing System

A robust, full-stack IT Helpdesk Ticketing System built using **Python**, **Django**, and **SQLite (SQL)**. This application features a modern, high-aesthetic single-page interface styled with Vanilla CSS and implements comprehensive ticket life-cycle management, user access roles, discussion timelines, and automated testing.

Designed specifically as a portfolio demonstration for a **Fresher Python / Django Developer** role to showcase production-grade engineering principles.

---

## 🚀 Key Features

- **Role-Based Access Control (RBAC)**: 
  - **Clients (Submitters)**: Can create new tickets, view/edit their own tickets, and add comments to their own tickets.
  - **Agents (Staff)**: Can view all tickets, reassign tickets, update statuses (Open ➔ In Progress ➔ Resolved ➔ Closed), and view full metrics.
  - **Admins (Superusers)**: Full database administrative control through a customized Django Admin portal.
- **Service Dashboard**: Dynamic counters for ticket stats (Total, Open, In Progress, Resolved, and Urgent) and advanced search/filtering by priority, status, and assignment.
- **Activity Timeline**: Complete audit trail showing user comments and automated system logs (e.g., assignment changes or status updates).
- **Custom Admin Interface**: Configured filters, searches, and list-editable columns for database administration.
- **Automated Tests**: Unit and integration test coverage for authentication, permissions, ticket lifecycles, and comments.

---

## 🛠️ Tech Stack & Architecture

- **Backend Web Framework**: Django 5.x (MTV Architecture)
- **Database**: SQLite (SQL engine managed cleanly via Django ORM)
- **Frontend**: Django Template Engine (semantic HTML5), Vanilla CSS (Modern dark/indigo glassmorphism design), and Vanilla JS (micro-interactions)
- **Authentication**: Built-in Django Auth system with customized login views and secure HTTP POST-based logout

---

## 📂 Project Structure

```
proud-archimedes/
├── requirements.txt            # Python dependencies (Django)
├── manage.py                   # Django CLI tool
├── seed_db.py                  # Database seeding script
├── helpdesk_project/           # Project settings & routing
│   ├── settings.py             # Project configurations (DB, static files, auth)
│   └── urls.py                 # Global URLs routing
└── tickets/                    # Main Ticketing Application
    ├── admin.py                # Customized Django Admin Layout
    ├── forms.py                # Safe input validation (Ticket submission & comments)
    ├── models.py               # SQL database schemas (Ticket, Comment)
    ├── tests.py                # Automated Pytest-compatible tests
    ├── urls.py                 # App specific URL routes
    ├── views.py                # Business logic (Dashboard, Details, Edit, Creation)
    ├── static/tickets/
    │   ├── style.css           # Premium Responsive CSS Design System
    │   └── app.js              # Client-side UI enhancements
    └── templates/tickets/
        ├── base.html           # Shared layout (navbar, footer, sidebar)
        ├── dashboard.html      # Ticket feed with stats grid & search filters
        ├── detail.html         # Conversation timeline & sidebar controls
        ├── ticket_form.html    # Create/Edit form layout
        └── login.html          # Portal login layout
```

---

## 📝 Resume Talking Points (For Freshers)

When presenting this project in an interview or on your resume, highlight these technical achievements:

1. **Relational Database Design**: Showed capability in database modeling, defining proper Primary Keys, Foreign Keys (`on_delete` behaviors), field choices, and indexes via Django migrations.
2. **Security & Data Isolation**: Implemented query filtering at the view level to ensure regular clients can never see or modify other users' support tickets, while allowing agents full read/write capabilities (RBAC).
3. **Clean Code & Separation of Concerns**: Used standard Class-Based Views (CBVs) for business logic and decoupled user input validation using Django forms.
4. **Test-Driven Mentality**: Wrote automated integration tests covering security permissions, edge cases, authentication redirection, and database persistence, rather than relying solely on manual testing.
5. **Modern Frontend Aesthetics**: Avoided bloated JavaScript frameworks, demonstrating full-stack capacity by writing clean semantic HTML5 and a responsive glassmorphic dark-theme design using CSS Grid, Flexbox, variables, and animations.

---

## ⚡ Quick Start / Setup Instructions

### 1. Install Dependencies
Make sure Python is installed, clone the repo, and run:
```bash
pip install -r requirements.txt
```

### 2. Apply Database Migrations
Run the migrations command to build the SQLite SQL database tables:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Seed Demo Data
Populate the database with pre-configured accounts (admin, agents, clients) and realistic support tickets:
```bash
python seed_db.py
```

### 4. Run Automated Tests
Verify code correctness and security permissions:
```bash
python manage.py test tickets
```

### 5. Start the Server
Launch the local web server:
```bash
python manage.py runserver
```
Visit the ticketing system at: `http://127.0.0.1:8000/`

---

## 🔑 Default Accounts (Seeded)
You can sign in with any of the following accounts:

| Role | Username | Password | Privileges |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | Can access `http://127.0.0.1:8000/admin` to edit any record. |
| **Agent (Staff)** | `agent1` | `agent123` | Can view all tickets, assign agents, and change ticket status. |
| **Client** | `client1` | `client123` | Can only view and edit their own tickets. |
