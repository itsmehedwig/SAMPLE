from django.contrib import admin
from .models import User, Student, Book, Transaction, TransactionItem, VerificationCode


class TransactionItemInline(admin.TabularInline):
    model = TransactionItem
    extra = 0
    fields = ['book', 'status', 'borrowed_date', 'return_date']
    readonly_fields = ['borrowed_date']


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'user_type', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_active']
    search_fields = ['username', 'email']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'get_full_name', 'course', 'year', 'section', 'is_verified']
    list_filter = ['course', 'year', 'is_verified']
    search_fields = ['student_id', 'first_name', 'last_name']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['isbn', 'title', 'author', 'category', 'copies_available', 'copies_total']
    list_filter = ['category']
    search_fields = ['isbn', 'title', 'author']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_code', 'student', 'get_book_count', 'borrowed_date', 'due_date', 'status', 'approval_status']
    list_filter = ['status', 'approval_status', 'borrowed_date']
    search_fields = ['transaction_code', 'student__student_id']
    date_hierarchy = 'borrowed_date'
    inlines = [TransactionItemInline]
    
    def get_book_count(self, obj):
        return obj.items.count()
    get_book_count.short_description = 'Books'


@admin.register(TransactionItem)
class TransactionItemAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'book', 'status', 'borrowed_date', 'return_date']
    list_filter = ['status', 'borrowed_date']
    search_fields = ['transaction__transaction_code', 'book__title']
    date_hierarchy = 'borrowed_date'


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ['student', 'code', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['student__student_id', 'code']
