from django.db.models.signals import post_save
from django.dispatch import receiver

from academics.models import Student

from .services import generate_dues_for_student


@receiver(post_save, sender=Student)
def give_new_student_their_dues(sender, instance, created, **kwargs):
    """A student added by hand automatically gets the class's existing fees."""
    if created and instance.is_active:
        generate_dues_for_student(instance)
