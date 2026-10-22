from django.shortcuts import render

from accounts.decorators import role_required


@role_required("student")
def home(request):
    return render(request, "portal/home.html")
