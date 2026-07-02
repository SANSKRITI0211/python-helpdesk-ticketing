from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('ticket/new/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('ticket/<int:pk>/', views.TicketDetailView.as_view(), name='ticket_detail'),
    path('ticket/<int:pk>/edit/', views.TicketEditView.as_view(), name='ticket_edit'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('api/classify/', views.ClassifyTicketView.as_view(), name='api_classify'),
    
    # Auth paths
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('logout/', auth_views.LogoutView.as_view(next_page='tickets:login'), name='logout'),
]
