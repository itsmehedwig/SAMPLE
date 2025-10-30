from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
from datetime import timedelta
import csv
from io import TextIOWrapper
from .models import User, Student, Book, Transaction, TransactionItem, VerificationCode

from .models import User, Student, Book, Transaction, VerificationCode
from .forms import (LoginForm, StudentIDVerificationForm, StudentRegistrationForm,
                   EmailVerificationForm, CSVUploadForm, BookForm, POSUserForm,
                   StudentSearchForm, ISBNSearchForm, TransactionCodeForm, StudentForm)

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .models import Student, Book, Transaction, TransactionItem

def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                if user.user_type == 'admin':
                    return redirect('admin_dashboard')
                elif user.user_type == 'pos':
                    return redirect('pos_home')
                else:
                    return redirect('student_dashboard')
            else:
                messages.error(request, 'Invalid username or password')
    else:
        form = LoginForm()
    
    return render(request, 'library/login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('login')


def verify_student_id(request):
    if request.method == 'POST':
        form = StudentIDVerificationForm(request.POST)
        if form.is_valid():
            student_id = form.cleaned_data['student_id']
            try:
                student = Student.objects.get(student_id=student_id)
                if student.user is not None:
                    messages.error(request, 'This student ID is already registered')
                    return redirect('verify_student_id')
                request.session['student_id'] = student_id
                return redirect('student_registration')
            except Student.DoesNotExist:
                messages.error(request, 'Student ID not found in the system. Please contact the admin.')
    else:
        form = StudentIDVerificationForm()
    
    return render(request, 'library/verify_student_id.html', {'form': form})


def student_registration(request):
    student_id = request.session.get('student_id')
    if not student_id:
        return redirect('verify_student_id')
    
    student = get_object_or_404(Student, student_id=student_id)
    
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            try:
                with transaction.atomic():
                    student = form.save(commit=False)
                    student.save()
                    
                    user, created = User.objects.get_or_create(
                        username=student_id,
                        defaults={
                            'email': email,
                            'user_type': 'student',
                            'is_active': False
                        }
                    )
                    
                    if created:
                        user.set_password(password)
                        user.save()
                    
                    student.user = user
                    student.save()
                    
                del request.session['student_id']
                messages.success(request, 'Registration successful! Your account is pending admin approval. You will be able to login once approved.')
                return redirect('login')
                
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}. Please try again.')
                return render(request, 'library/student_registration.html', {
                    'form': form,
                    'student': student
                })
    else:
        form = StudentRegistrationForm(instance=student)
    
    return render(request, 'library/student_registration.html', {
        'form': form,
        'student': student
    })


def email_verification(request):
    student_id = request.session.get('student_id_for_verification')
    if not student_id:
        return redirect('verify_student_id')
    
    student = get_object_or_404(Student, student_id=student_id)
    
    if request.method == 'POST':
        form = EmailVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                verification = VerificationCode.objects.get(
                    student=student,
                    code=code,
                    is_used=False
                )
                if verification.is_valid():
                    verification.is_used = True
                    verification.save()
                    student.is_verified = True
                    student.save()
                    
                    del request.session['student_id']
                    del request.session['student_id_for_verification']
                    
                    messages.success(request, 'Email verified successfully! You can now login.')
                    return redirect('login')
                else:
                    messages.error(request, 'Verification code has expired. Please request a new one.')
            except VerificationCode.DoesNotExist:
                messages.error(request, 'Invalid verification code')
    else:
        form = EmailVerificationForm()
    
    return render(request, 'library/email_verification.html', {'form': form})


@login_required
def student_dashboard(request):
    if request.user.user_type != 'student':
        return redirect('dashboard')
    
    student = Student.objects.get(user=request.user)
    borrowed_books = Transaction.objects.filter(
        student=student,
        status='borrowed',
        approval_status='approved'
    ).prefetch_related('items__book')
    
    history = Transaction.objects.filter(
        student=student,
        approval_status='approved'
    ).prefetch_related('items__book').order_by('-borrowed_date')[:10]
    
    search_query = request.GET.get('search', '')
    category = request.GET.get('category', '')
    
    books = Book.objects.all()
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(isbn__icontains=search_query)
        )
    if category:
        books = books.filter(category=category)
    
    categories = Book.objects.values_list('category', flat=True).distinct()
    
    context = {
        'student': student,
        'borrowed_books': borrowed_books,
        'history': history,
        'books': books,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category
    }
    
    return render(request, 'library/student_dashboard.html', context)


@login_required
def admin_dashboard(request):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    total_students = Student.objects.count()
    total_books = Book.objects.count()
    total_borrowed = Transaction.objects.filter(status='borrowed', approval_status='approved').count()
    total_available = Book.objects.filter(copies_available__gt=0).count()
    pending_registrations = Student.objects.filter(user__isnull=False, is_approved=False).count()
    pending_borrowing = Transaction.objects.filter(approval_status='pending').count()
    
    recent_transactions = Transaction.objects.filter(approval_status='approved').select_related('student').prefetch_related('items__book').order_by('-borrowed_date')[:10]
    
    context = {
        'total_students': total_students,
        'total_books': total_books,
        'total_borrowed': total_borrowed,
        'total_available': total_available,
        'pending_registrations': pending_registrations,
        'pending_borrowing': pending_borrowing,
        'recent_transactions': recent_transactions
    }
    
    return render(request, 'library/admin_dashboard.html', context)


@login_required
def import_books_csv(request):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            decoded_file = TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.DictReader(decoded_file)
            
            success_count = 0
            error_count = 0
            
            for row in reader:
                try:
                    isbn = row.get('isbn', '').strip()
                    title = row.get('title', '').strip()
                    author = row.get('author', '').strip()
                    category = row.get('category', '').strip()
                    publisher = row.get('publisher', '').strip()
                    year_published = row.get('year_published', '').strip()
                    copies_total = row.get('copies_total', '1').strip()
                    description = row.get('description', '').strip()
                    
                    if isbn and title and author and category:
                        book, created = Book.objects.get_or_create(
                            isbn=isbn,
                            defaults={
                                'title': title,
                                'author': author,
                                'category': category,
                                'publisher': publisher,
                                'year_published': int(year_published) if year_published else None,
                                'copies_total': int(copies_total) if copies_total else 1,
                                'copies_available': int(copies_total) if copies_total else 1,
                                'description': description
                            }
                        )
                        if created:
                            success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
            
            messages.success(request, f'Successfully imported {success_count} books. {error_count} errors.')
            return redirect('manage_books')
    else:
        form = CSVUploadForm()
    
    return render(request, 'library/import_books_csv.html', {'form': form})


@login_required
def import_students_csv(request):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            decoded_file = TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.DictReader(decoded_file)
            
            success_count = 0
            error_count = 0
            
            for row in reader:
                try:
                    student_id = row.get('student_id', '').strip()
                    last_name = row.get('last_name', '').strip()
                    first_name = row.get('first_name', '').strip()
                    middle_name = row.get('middle_name', '').strip()
                    course = row.get('course', '').strip()
                    year = row.get('year', '').strip()
                    section = row.get('section', '').strip()
                    
                    if student_id and last_name and first_name and course and year and section:
                        Student.objects.get_or_create(
                            student_id=student_id,
                            defaults={
                                'last_name': last_name,
                                'first_name': first_name,
                                'middle_name': middle_name,
                                'course': course,
                                'year': year,
                                'section': section
                            }
                        )
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
            
            messages.success(request, f'Successfully imported {success_count} students. {error_count} errors.')
            return redirect('admin_dashboard')
    else:
        form = CSVUploadForm()
    
    return render(request, 'library/import_students.html', {'form': form})


@login_required
def manage_books(request):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    books = Book.objects.all().order_by('title')
    search_query = request.GET.get('search', '')
    
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(isbn__icontains=search_query)
        )
    
    return render(request, 'library/manage_books.html', {
        'books': books,
        'search_query': search_query
    })


@login_required
def add_book(request):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            book.copies_available = book.copies_total
            book.save()
            messages.success(request, 'Book added successfully!')
            return redirect('manage_books')
    else:
        form = BookForm()
    
    return render(request, 'library/add_book.html', {'form': form})

def add_borrow_book(request):
    isbn = request.POST.get('isbn')
    borrow_books = request.session.get('borrow_books', [])
    if isbn not in borrow_books:
        borrow_books.append(isbn)
        request.session['borrow_books'] = borrow_books

@login_required
def edit_book(request, book_id):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    book = get_object_or_404(Book, id=book_id)
    
    if request.method == 'POST':
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, 'Book updated successfully!')
            return redirect('manage_books')
    else:
        form = BookForm(instance=book)
    
    return render(request, 'library/edit_book.html', {'form': form, 'book': book})


@login_required
def manage_students(request):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    pending_students = Student.objects.filter(user__isnull=False, is_approved=False).order_by('-created_at')
    
    students = Student.objects.all().order_by('last_name')
    search_query = request.GET.get('search', '')
    
    if search_query:
        students = students.filter(
            Q(student_id__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    return render(request, 'library/manage_students.html', {
        'students': students,
        'pending_students': pending_students,
        'search_query': search_query
    })


@login_required
def pending_students(request):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    pending = Student.objects.filter(user__isnull=False, is_approved=False).order_by('-created_at')
    
    return render(request, 'library/pending_students.html', {
        'pending_students': pending
    })


@login_required
def approve_student(request, student_id):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    if request.method == 'POST':
        student = get_object_or_404(Student, id=student_id)
        student.is_approved = True
        student.save()
        
        if student.user:
            student.user.is_active = True
            student.user.save()
        
        messages.success(request, f'Student {student.get_full_name()} has been approved and can now login.')
        return redirect('manage_students')
    
    return redirect('manage_students')


@login_required
def reject_student(request, student_id):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    if request.method == 'POST':
        student = get_object_or_404(Student, id=student_id)
        
        if student.user:
            user = student.user
            student.user = None
            student.save()
            user.delete()
        
        messages.success(request, f'Student {student.get_full_name()} registration has been rejected.')
        return redirect('manage_students')
    
    return redirect('manage_students')


@login_required
def create_pos_account(request):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = POSUserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            User.objects.create_user(
                username=username,
                password=password,
                user_type='pos'
            )
            messages.success(request, 'POS account created successfully!')
            return redirect('admin_dashboard')
    else:
        form = POSUserForm()
    
    return render(request, 'library/create_pos_account.html', {'form': form})


@login_required
def pos_home(request):
    if request.user.user_type != 'pos':
        return redirect('dashboard')
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        try:
            student = Student.objects.get(student_id=student_id, is_approved=True)
            request.session['pos_student_id'] = student_id
            return redirect('pos_options')
        except Student.DoesNotExist:
            messages.error(request, 'Student ID not found or not approved')
    
    return render(request, 'library/pos_home.html')



@login_required
def pending_transactions(request):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    pending = Transaction.objects.filter(approval_status='pending').select_related('student', 'created_by').prefetch_related('items__book').order_by('-borrowed_date')
    
    return render(request, 'library/pending_transactions.html', {
        'pending_transactions': pending
    })


@login_required
def approve_transaction(request, transaction_id):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    if request.method == 'POST':
        transaction = Transaction.objects.get(id=transaction_id)
        
        for item in transaction.items.all():
            item.book.copies_available -= 1
            item.book.save()
        
        transaction.approval_status = 'approved'
        transaction.approved_by = request.user
        transaction.approved_at = timezone.now()
        transaction.save()
        
        book_count = transaction.items.count()
        messages.success(request, f'{book_count} book(s) borrowing approved for {transaction.student.get_full_name()}')
    
    return redirect('pending_transactions')


@login_required
def reject_transaction(request, transaction_id):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    if request.method == 'POST':
        transaction = Transaction.objects.get(id=transaction_id)
        
        transaction.approval_status = 'rejected'
        transaction.approved_by = request.user
        transaction.approved_at = timezone.now()
        transaction.save()
        
        messages.success(request, f'Book borrowing request rejected')
    
    return redirect('pending_transactions')


@login_required
def dashboard(request):
    if request.user.user_type == 'admin':
        return redirect('admin_dashboard')
    elif request.user.user_type == 'pos':
        return redirect('pos_home')
    else:
        return redirect('student_dashboard')


@login_required
def student_settings(request):
    if request.user.user_type != 'student':
        return redirect('dashboard')
    
    student = Student.objects.get(user=request.user)
    
    if request.method == 'POST':
        student.phone_number = request.POST.get('phone_number', student.phone_number)
        
        if 'profile_photo' in request.FILES:
            student.profile_photo = request.FILES['profile_photo']
        
        email = request.POST.get('email')
        if email and email != request.user.email:
            request.user.email = email
            request.user.save()
        
        password = request.POST.get('password')
        if password:
            request.user.set_password(password)
            request.user.save()
            messages.success(request, 'Password updated. Please login again.')
            return redirect('login')
        
        student.save()
        messages.success(request, 'Settings updated successfully!')
        return redirect('student_settings')
    
    return render(request, 'library/student_settings.html', {'student': student})


@login_required
def admin_settings(request):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            request.user.email = email
            request.user.save()
        
        password = request.POST.get('password')
        if password:
            request.user.set_password(password)
            request.user.save()
            messages.success(request, 'Password updated. Please login again.')
            return redirect('login')
        
        messages.success(request, 'Settings updated successfully!')
        return redirect('admin_settings')
    
    return render(request, 'library/admin_settings.html')


@login_required
def delete_book(request, book_id):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    book = get_object_or_404(Book, id=book_id)
    
    if request.method == 'POST':
        book_title = book.title
        book.delete()
        messages.success(request, f'Book "{book_title}" deleted successfully!')
        return redirect('manage_books')
    
    return render(request, 'library/delete_book.html', {'book': book})


@login_required
def add_student(request):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student added successfully!')
            return redirect('manage_students')
    else:
        form = StudentForm()
    
    return render(request, 'library/add_student.html', {'form': form})


@login_required
def edit_student(request, student_id):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully!')
            return redirect('manage_students')
    else:
        form = StudentForm(instance=student)
    
    return render(request, 'library/edit_student.html', {'form': form, 'student': student})


@login_required
def delete_student(request, student_id):
    if request.user.user_type != 'admin':
        return redirect('dashboard')
    
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        student_name = student.get_full_name()
        if student.user:
            student.user.delete()
        student.delete()
        messages.success(request, f'Student "{student_name}" deleted successfully!')
        return redirect('manage_students')
    
    return render(request, 'library/delete_student.html', {'student': student})


# views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from .models import Student

@login_required
def validate_student_id(request):
    student_id = request.GET.get('student_id', '').strip()
    try:
        student = Student.objects.get(student_id=student_id)
        if student.is_approved:
            return JsonResponse({"valid": True, "approved": True})
        else:
            return JsonResponse({"valid": True, "approved": False, "reason": "You must register first."})
    except Student.DoesNotExist:
        return JsonResponse({"valid": False, "approved": False, "reason": "Student not registered."})


from django.shortcuts import render, redirect
from .models import Student

def pos_options(request):
    student_id = request.GET.get('student_id')
    if not student_id:
        return redirect('pos_student_login')  # send back if missing

    try:
        student = Student.objects.get(student_id=student_id)
        if not student.is_approved:
            return redirect('pos_student_login')
    except Student.DoesNotExist:
        return redirect('pos_student_login')

    # ✅ If we reach here, student is valid
    return render(request, 'library/pos_options.html', {
        'student': student
    })


from django.shortcuts import render, redirect
from .models import Student

def pos_options(request):
    # Try to get student_id from GET or session
    student_id = request.GET.get('student_id') or request.session.get('student_id')
    if not student_id:
        print("⚠ No student_id found, redirecting to POS login")
        return redirect('pos_student_login')  # go back if missing

    try:
        student = Student.objects.get(student_id=student_id)
        if not student.is_approved:
            print("⚠ Student not approved, redirecting")
            return redirect('pos_student_login')
    except Student.DoesNotExist:
        print("❌ Student not found, redirecting")
        return redirect('pos_student_login')

    # ✅ Keep session active for POS navigation
    request.session['student_id'] = student.student_id

    print("✅ Access granted to:", student.get_full_name())
    return render(request, 'library/pos_options.html', {'student': student})


#####BORROW BOOKS
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Student, Book, Transaction, TransactionItem
import re

@login_required
@csrf_exempt
def pos_borrow_book(request):
    if request.user.user_type != 'pos':
        return redirect('dashboard')

    student_id = request.GET.get('student_id') or request.session.get('pos_student_id')
    if not student_id:
        return redirect('pos_home')

    try:
        student = Student.objects.get(student_id=student_id, is_approved=True)
        request.session['pos_student_id'] = student_id
    except Student.DoesNotExist:
        messages.error(request, 'Student not found or not approved.')
        return redirect('pos_home')

    # Initialize book list in session
    if 'pos_books' not in request.session:
        request.session['pos_books'] = []
    books = request.session['pos_books']

    # ✅ AJAX auto-scan add (GET request with ISBN)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        isbn_raw = request.GET.get('isbn', '').strip()
        if not isbn_raw:
            return JsonResponse({'success': False, 'message': 'Missing ISBN.'})

        isbn = re.sub(r'[^0-9A-Za-z]', '', isbn_raw).upper()
        found_book = None
        for book in Book.objects.all():
            db_isbn = re.sub(r'[^0-9A-Za-z]', '', (book.isbn or '')).upper()
            if db_isbn == isbn:
                found_book = book
                break

        if not found_book:
            return JsonResponse({'success': False, 'message': f'Book not found ({isbn_raw})'})

        # Check if already added
        if any(b['id'] == found_book.id for b in books):
            return JsonResponse({'success': False, 'message': 'Book already added.'})

        # Append to session
        books.append({
            'id': found_book.id,
            'title': found_book.title,
            'isbn': found_book.isbn,
            'author': found_book.author
        })
        request.session['pos_books'] = books
        request.session.modified = True
        return JsonResponse({'success': True, 'message': f'Added: {found_book.title}'})

    # ✅ Manual "Add Book" button
    if request.method == 'POST' and 'add_book' in request.POST:
        isbn_raw = request.POST.get('isbn', '').strip()
        isbn = re.sub(r'[^0-9A-Za-z]', '', isbn_raw).upper()
        found_book = None

        for book in Book.objects.all():
            db_isbn = re.sub(r'[^0-9A-Za-z]', '', (book.isbn or '')).upper()
            if db_isbn == isbn:
                found_book = book
                break

        if not found_book:
            messages.error(request, f'Book not found: {isbn_raw}')
        elif any(b['id'] == found_book.id for b in books):
            messages.warning(request, 'Book already added.')
        else:
            books.append({
                'id': found_book.id,
                'title': found_book.title,
                'isbn': found_book.isbn,
                'author': found_book.author
            })
            request.session['pos_books'] = books
            request.session.modified = True
            messages.success(request, f'Added: {found_book.title}')
            
            

        return render(request, 'library/pos_borrow_book.html', {
            'student': student,
            'books': books,
            'step': 'add_books'
        })

    # ✅ Continue and Confirm borrow
    if request.method == 'POST':
        if 'continue_borrow' in request.POST:
            return render(request, 'library/pos_borrow_book.html', {
                'student': student,
                'books': books,
                'step': 'confirm'
            })

        elif 'confirm_borrow' in request.POST:
            if not books:
                messages.error(request, 'No books selected.')
                return render(request, 'library/pos_borrow_book.html', {
                    'student': student,
                    'books': books,
                    'step': 'add_books'
                })

            transaction = Transaction.objects.create(
                student=student,
                transaction_code=Transaction.generate_transaction_code(),
                due_date=timezone.now() + timedelta(days=7),
                created_by=request.user
            )

            for b in books:
                book = Book.objects.get(id=b['id'])
                TransactionItem.objects.create(transaction=transaction, book=book)

            request.session.pop('pos_books', None)
            request.session.pop('pos_student_id', None)
            return redirect('pos_borrow_success', transaction_id=transaction.id)

    # Default
    return render(request, 'library/pos_borrow_book.html', {
        'student': student,
        'books': books,
        'step': 'add_books'
    })

@login_required
def pos_borrow_success(request, transaction_id):
    try:
        transaction = Transaction.objects.get(id=transaction_id)
    except Transaction.DoesNotExist:
        messages.error(request,'Transaction not found')
        return redirect('pos_home')
    return render(request,'library/pos_borrow_success.html',{'transaction':transaction,'student':transaction.student,'books':transaction.items.all()})

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Student

@csrf_exempt
def validate_student_id(request):
    # Only allow GET requests
    if request.method != "GET":
        return JsonResponse({"error": "Invalid request method."}, status=405)

    student_id = request.GET.get('student_id', '').strip()
    print("📥 Student ID received:", student_id)  # Debug output

    if not student_id:
        return JsonResponse({
            "valid": False,
            "approved": False,
            "reason": "Missing student ID."
        }, status=400)

    try:
        student = Student.objects.get(student_id=student_id)
        print("✅ Student found:", student)

        if getattr(student, "is_approved", False):
            # ✅ Save student in session so Django remembers them
            request.session['student_id'] = student_id
            print(f"💾 Session saved for student: {student_id}")

            return JsonResponse({
                "valid": True,
                "approved": True
            })
        else:
            return JsonResponse({
                "valid": True,
                "approved": False,
                "reason": "Magregister ka muna boiii!!."
            })
    except Student.DoesNotExist:
        return JsonResponse({
            "valid": False,
            "approved": False,
            "reason": "You are not registered. Please register first."
        })
    except Exception as e:
        print("❌ Unexpected error:", e)
        return JsonResponse({
            "valid": False,
            "approved": False,
            "reason": "Server error: " + str(e)
        }, status=500)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from library.models import Book

@csrf_exempt
def validate_book_isbn(request):
    raw_isbn = request.GET.get("isbn", "").strip()
    if not raw_isbn:
        return JsonResponse({"valid": False, "reason": "Missing ISBN."})

    # Normalize ISBN (remove spaces, dashes, etc.)
    normalized_isbn = ''.join(filter(str.isalnum, raw_isbn)).upper()

    book = None
    try:
        # Try exact match first
        book = Book.objects.get(isbn__iexact=raw_isbn)
    except Book.DoesNotExist:
        # Then try normalized match
        for b in Book.objects.all():
            db_isbn = ''.join(filter(str.isalnum, b.isbn)).upper()
            if db_isbn == normalized_isbn:
                book = b
                break

    if not book:
        return JsonResponse({"valid": False, "unavailable": False, "reason": "Book not found."})

    # Check availability
    unavailable = not book.is_available() if hasattr(book, "is_available") else False

    return JsonResponse({
        "valid": True,
        "unavailable": unavailable,
        "book": {
            "id": book.id,
            "title": book.title,
            "isbn": book.isbn,
            "author": book.author
        }
    })

@login_required
def pos_return_book(request):
    if request.user.user_type != 'pos':
        return redirect('dashboard')
    
    student_id = request.GET.get('student_id') or request.session.get('pos_student_id')
    if not student_id:
        return redirect('pos_home')
    
    try:
        student = Student.objects.get(student_id=student_id, is_approved=True)
    except Student.DoesNotExist:
        messages.error(request, 'Student not found')
        return redirect('pos_home')
    
    if request.method == 'POST':
        if 'review_return' in request.POST:
            book_ids = request.POST.getlist('book_ids')
            if not book_ids:
                messages.error(request, 'Please select at least one book to return')
                borrowed_items = TransactionItem.objects.filter(
                    transaction__student=student,
                    status='borrowed',
                    transaction__approval_status='approved'
                ).select_related('book', 'transaction')
                return render(request, 'library/pos_return_book.html', {
                    'student': student,
                    'borrowed_items': borrowed_items,
                    'step': 'select_books'
                })
            
            selected_items = TransactionItem.objects.filter(
                id__in=book_ids,
                transaction__student=student,
                status='borrowed'
            ).select_related('book', 'transaction')
            
            return render(request, 'library/pos_return_book.html', {
                'student': student,
                'selected_items': selected_items,
                'step': 'confirm'
            })
        
        elif 'confirm_return' in request.POST:
            book_ids = request.POST.getlist('book_ids')
            if not book_ids:
                messages.error(request, 'No books selected for return')
                return redirect('pos_home')
            
            selected_items = TransactionItem.objects.filter(
                id__in=book_ids,
                transaction__student=student,
                status='borrowed'
            ).select_related('book', 'transaction')
            
            return_date = timezone.now()
            returned_items = []
            
            for item in selected_items:
                item.status = 'returned'
                item.return_date = return_date
                item.save()
                
                item.book.copies_available += 1
                item.book.save()
                returned_items.append(item)
                
                transaction = item.transaction
                all_returned = not transaction.items.filter(status='borrowed').exists()
                if all_returned:
                    transaction.status = 'returned'
                    transaction.return_date = return_date
                    transaction.save()
            
            still_borrowed_items = TransactionItem.objects.filter(
                transaction__student=student,
                status='borrowed',
                transaction__approval_status='approved'
            ).select_related('book', 'transaction')
            
            return render(request, 'library/pos_return_success.html', {
                'student': student,
                'returned_items': returned_items,
                'still_borrowed_items': still_borrowed_items,
                'return_date': return_date
            })
    
    borrowed_items = TransactionItem.objects.filter(
        transaction__student=student,
        status='borrowed',
        transaction__approval_status='approved'
    ).select_related('book', 'transaction')
    
    return render(request, 'library/pos_return_book.html', {
        'student': student,
        'borrowed_items': borrowed_items,
        'step': 'select_books'
    })
    
@login_required
def remove_borrow_book(request):
    if request.user.user_type != 'pos':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        if not book_id:
            return JsonResponse({'success': False, 'error': 'No book ID provided'}, status=400)

        books = request.session.get('pos_books', [])
        books = [b for b in books if str(b['id']) != str(book_id)]
        request.session['pos_books'] = books
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
