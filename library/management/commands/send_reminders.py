from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from library.models import Transaction


class Command(BaseCommand):
    help = 'Send email reminders to students 2 days after borrowing books'

    def handle(self, *args, **options):
        two_days_ago = timezone.now() - timedelta(days=2)
        start_of_day = two_days_ago.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = two_days_ago.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        transactions = Transaction.objects.filter(
            status='borrowed',
            borrowed_date__gte=start_of_day,
            borrowed_date__lte=end_of_day,
            reminder_sent=False
        ).select_related('student', 'book', 'student__user')
        
        sent_count = 0
        
        for transaction in transactions:
            if transaction.student.user and transaction.student.user.email:
                try:
                    subject = 'Reminder: Return Your Borrowed Book'
                    message = f"""Dear {transaction.student.get_full_name()},

This is a reminder that you borrowed the following book 2 days ago:

Book: {transaction.book.title}
Author: {transaction.book.author}
ISBN: {transaction.book.isbn}
Transaction Code: {transaction.transaction_code}
Due Date: {transaction.due_date.strftime('%Y-%m-%d')}

Please remember to return the book by the due date.

Thank you,
Library Management System
"""
                    
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [transaction.student.user.email],
                        fail_silently=False,
                    )
                    
                    transaction.reminder_sent = True
                    transaction.save()
                    sent_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Sent reminder to {transaction.student.get_full_name()} for book "{transaction.book.title}"'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to send reminder: {str(e)}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully sent {sent_count} reminder(s)')
        )
