from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from inventory.models import Inventory, UserProfile, Organization


class Command(BaseCommand):
    """
    Send email notifications to admins when inventory items are running low on stock.

    This command checks for items with quantity below the specified threshold
    and sends consolidated email notifications to all admin users, grouped by organization.
    """
    help = 'Send email notifications for low stock items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=int,
            default=5,
            help='Stock threshold for low stock alerts (default: 5)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails',
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        dry_run = options['dry_run']

        # Get low stock items
        low_stock_items = Inventory.objects.filter(quantity__lt=threshold)

        if not low_stock_items.exists():
            self.stdout.write(
                self.style.SUCCESS('No items are currently low on stock.')
            )
            return

        # Get all admin users to notify
        admin_profiles = UserProfile.objects.filter(user__is_staff=True)

        if not admin_profiles.exists():
            self.stdout.write(
                self.style.WARNING('No admin users found to notify.')
            )
            return

        # Group by organization
        org_notifications = {}
        for profile in admin_profiles:
            org_name = profile.organization.name if profile.organization else 'Default'
            if org_name not in org_notifications:
                org_notifications[org_name] = {
                    'admins': [],
                    'items': []
                }
            org_notifications[org_name]['admins'].append(profile.user)

        # Add low stock items to each organization
        for item in low_stock_items:
            # For now, send to all organizations (you could filter by organization if needed)
            for org_data in org_notifications.values():
                org_data['items'].append(item)

        # Send notifications
        total_emails_sent = 0

        for org_name, data in org_notifications.items():
            admins = data['admins']
            items = data['items']

            if not items:
                continue

            # Prepare email content
            subject = f'Low Stock Alert - {org_name}'

            item_list = '\n'.join([
                f"- {item.item_name}: {item.quantity} remaining (Category: {item.category})"
                for item in items
            ])

            message = f"""
Dear Admin,

The following items in your {org_name} inventory are running low on stock:

{item_list}

Please consider restocking these items soon.

This is an automated notification from StoreFlow Inventory System.

Best regards,
StoreFlow Team
"""

            # Get admin email addresses
            admin_emails = [admin.email for admin in admins if admin.email]

            if not admin_emails:
                self.stdout.write(
                    self.style.WARNING(f'No email addresses found for {org_name} admins.')
                )
                continue

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'[DRY RUN] Would send email to {", ".join(admin_emails)}')
                )
                self.stdout.write(f'Subject: {subject}')
                self.stdout.write(f'Message:\n{message}')
                self.stdout.write('-' * 50)
            else:
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=admin_emails,
                        fail_silently=False,
                    )
                    total_emails_sent += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Sent low stock notification to {len(admin_emails)} admin(s) for {org_name}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to send email for {org_name}: {str(e)}')
                    )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully sent {total_emails_sent} low stock notification email(s).')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Dry run completed. Would have sent {len(org_notifications)} email(s).')
            )