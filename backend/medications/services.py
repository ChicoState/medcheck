from datetime import time

from django.db import transaction

from .models import MedicationDose, MedicationSchedule

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

DEFAULT_DOSES = (
    (0, "Vitamin D", time(8, 0), True),
    (0, "Lisinopril", time(8, 30), False),
    (1, "Vitamin D", time(8, 0), True),
    (1, "Lisinopril", time(8, 30), False),
    (2, "Vitamin D", time(8, 0), True),
    (2, "Lisinopril", time(8, 30), False),
    (2, "Atorvastatin", time(21, 0), False),
    (3, "Vitamin D", time(8, 0), True),
    (3, "Lisinopril", time(8, 30), False),
    (4, "Vitamin D", time(8, 0), True),
    (4, "Lisinopril", time(8, 30), False),
    (5, "Vitamin D", time(8, 0), True),
)


@transaction.atomic
def get_or_create_schedule(user):
    schedule, created = MedicationSchedule.objects.get_or_create(user=user)
    if created:
        MedicationDose.objects.bulk_create(
            [
                MedicationDose(
                    schedule=schedule,
                    day_of_week=day,
                    medication_name=name,
                    time=dose_time,
                    with_food=with_food,
                )
                for day, name, dose_time, with_food in DEFAULT_DOSES
            ]
        )
    return schedule


def serialize_schedule(schedule):
    schedule_by_day = {day: [] for day in DAY_NAMES}
    for dose in schedule.doses.all():
        schedule_by_day[DAY_NAMES[dose.day_of_week]].append(
            {
                "id": dose.pk,
                "name": dose.medication_name,
                "time": dose.time.strftime("%I:%M %p").lstrip("0"),
                "food": "with food" if dose.with_food else "without food",
            }
        )
    return schedule_by_day
