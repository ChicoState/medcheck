from django.core.management.base import BaseCommand

from medications.notifications import send_due_notifications


class Command(BaseCommand):
    help = "Send due medication, vitamin, and refill email notifications."

    def handle(self, *args, **options):
        sent = send_due_notifications()
        self.stdout.write(  # pyright: ignore[reportAttributeAccessIssue]
            self.style.SUCCESS(  # pyright: ignore[reportAttributeAccessIssue]
                f"Sent {sent} notification(s)."
            )
        )
