from django.shortcuts import render

from accounts.decorators import role_required
from academics.models import AcademicYear, SchoolClass, Student


@role_required("admin", "accountant", "teacher")
def home(request):
    school = request.school
    return render(request, "dashboard/home.html", {
        "student_count": Student.objects.filter(school=school).count(),
        "class_count": SchoolClass.objects.filter(school=school).count(),
        "current_year": AcademicYear.objects.filter(school=school, is_current=True).first(),
    })
