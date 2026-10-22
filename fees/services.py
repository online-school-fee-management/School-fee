from academics.models import Student

from .models import FeeStructure, StudentFee


def _eligible_students(structure):
    """Active students in the structure's class + academic year."""
    return Student.objects.filter(
        school_id=structure.school_id,
        school_class_id=structure.school_class_id,
        academic_year_id=structure.academic_year_id,
        is_active=True,
    )


def generate_dues(structure):
    """
    Create a StudentFee for every eligible student who does not have one yet.
    Safe to run again and again: existing dues are never touched.
    Returns the number of new dues created.
    """
    if not structure.is_active:
        return 0

    have = set(
        StudentFee.objects.filter(structure=structure).values_list("student_id", flat=True)
    )
    new = [
        StudentFee(
            school_id=structure.school_id,
            student_id=student_id,
            structure=structure,
            amount=structure.amount,
        )
        for student_id in _eligible_students(structure).values_list("pk", flat=True)
        if student_id not in have
    ]
    StudentFee.objects.bulk_create(new, batch_size=500)
    return len(new)


def missing_students_count(structure):
    """How many eligible students do not have this due yet."""
    if not structure.is_active:
        return 0
    return _eligible_students(structure).exclude(fees__structure=structure).count()


def generate_dues_for_student(student):
    """Give one (new) student every active fee of their class + year."""
    structures = FeeStructure.objects.filter(
        school_id=student.school_id,
        school_class_id=student.school_class_id,
        academic_year_id=student.academic_year_id,
        is_active=True,
    )
    for structure in structures:
        StudentFee.objects.get_or_create(
            student=student, structure=structure,
            defaults={"school_id": student.school_id, "amount": structure.amount},
        )
