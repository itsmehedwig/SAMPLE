from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('verify/', views.verify_student_id, name='verify_student_id'),
    path('register/', views.student_registration, name='student_registration'),
    
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/settings/', views.student_settings, name='student_settings'),
    
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/import-students/', views.import_students_csv, name='import_students_csv'),
    path('admin/import-books/', views.import_books_csv, name='import_books_csv'),
    path('admin/books/', views.manage_books, name='manage_books'),
    path('admin/books/add/', views.add_book, name='add_book'),
    path('admin/books/edit/<int:book_id>/', views.edit_book, name='edit_book'),
    path('admin/books/delete/<int:book_id>/', views.delete_book, name='delete_book'),
    path('admin/students/', views.manage_students, name='manage_students'),
    path('admin/students/pending/', views.pending_students, name='pending_students'),
    path('admin/students/approve/<int:student_id>/', views.approve_student, name='approve_student'),
    path('admin/students/reject/<int:student_id>/', views.reject_student, name='reject_student'),
    path('admin/students/add/', views.add_student, name='add_student'),
    path('admin/students/edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('admin/students/delete/<int:student_id>/', views.delete_student, name='delete_student'),
    path('admin/transactions/pending/', views.pending_transactions, name='pending_transactions'),
    path('admin/transactions/approve/<int:transaction_id>/', views.approve_transaction, name='approve_transaction'),
    path('admin/transactions/reject/<int:transaction_id>/', views.reject_transaction, name='reject_transaction'),
    path('admin/create-pos/', views.create_pos_account, name='create_pos_account'),
    path('admin/settings/', views.admin_settings, name='admin_settings'),
    
    path('pos/home/', views.pos_home, name='pos_home'),
    path('pos/options/', views.pos_options, name='pos_options'),
    path('pos/borrow/', views.pos_borrow_book, name='pos_borrow_book'),
    path('pos/return/', views.pos_return_book, name='pos_return_book'),
]
