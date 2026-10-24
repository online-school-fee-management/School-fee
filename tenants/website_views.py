from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required

from .models import GalleryImage, Notice, SchoolWebsite, TeacherProfile
from .website_forms import (
    GalleryImageForm,
    NoticeForm,
    SchoolDetailsForm,
    TeacherProfileForm,
    WebsiteSettingsForm,
)


def _website_for(school):
    website, _ = SchoolWebsite.objects.get_or_create(school=school)
    return website


def public_school_site(request):
    """The tenant's public home page (shown before the portal login)."""
    school = request.school
    website = _website_for(school)
    notices = Notice.objects.filter(
        school=school,
        is_active=True,
        published_on__lte=timezone.localdate(),
    )[:6]
    gallery = GalleryImage.objects.filter(school=school, is_active=True)[:9]
    teachers = TeacherProfile.objects.filter(school=school, is_active=True)[:8]

    return render(request, "website/public_home.html", {
        "school": school,
        "site": website,
        "notices": notices,
        "gallery": gallery,
        "teachers": teachers,
    })


@role_required("admin", "webmaster")
def website_dashboard(request):
    school = request.school
    website = _website_for(school)
    return render(request, "website/dashboard.html", {
        "site": website,
        "notice_count": Notice.objects.filter(school=school).count(),
        "gallery_count": GalleryImage.objects.filter(school=school).count(),
        "teacher_count": TeacherProfile.objects.filter(school=school).count(),
        "recent_notices": Notice.objects.filter(school=school)[:3],
    })


@role_required("admin", "webmaster")
def website_settings(request):
    school = request.school
    website = _website_for(school)
    school_form = SchoolDetailsForm(instance=school)
    site_form = WebsiteSettingsForm(instance=website)

    if request.method == "POST":
        form_kind = request.POST.get("form_kind")
        if form_kind == "school":
            school_form = SchoolDetailsForm(
                request.POST, request.FILES, instance=school
            )
            if school_form.is_valid():
                school_form.save()
                messages.success(request, "School contact details updated.")
                return redirect("website:settings")
        elif form_kind == "website":
            site_form = WebsiteSettingsForm(
                request.POST, request.FILES, instance=website
            )
            if site_form.is_valid():
                site_form.save()
                messages.success(request, "Website content updated.")
                return redirect("website:settings")

    return render(request, "website/settings.html", {
        "site": website,
        "school_form": school_form,
        "site_form": site_form,
    })


@role_required("admin", "webmaster")
def notice_list(request):
    return render(request, "website/notices.html", {
        "notices": Notice.objects.filter(school=request.school),
    })


@role_required("admin", "webmaster")
def notice_add(request):
    form = NoticeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        notice = form.save(commit=False)
        notice.school = request.school
        notice.save()
        messages.success(request, "Notice published.")
        return redirect("website:notices")
    return render(request, "website/notice_form.html", {
        "form": form,
        "target": None,
    })


@role_required("admin", "webmaster")
def notice_edit(request, pk):
    notice = get_object_or_404(
        Notice.objects.filter(school=request.school), pk=pk
    )
    form = NoticeForm(request.POST or None, instance=notice)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Notice updated.")
        return redirect("website:notices")
    return render(request, "website/notice_form.html", {
        "form": form,
        "target": notice,
    })


@role_required("admin", "webmaster")
@require_POST
def notice_delete(request, pk):
    notice = get_object_or_404(
        Notice.objects.filter(school=request.school), pk=pk
    )
    notice.delete()
    messages.success(request, "Notice deleted.")
    return redirect("website:notices")


@role_required("admin", "webmaster")
def gallery_list(request):
    return render(request, "website/gallery.html", {
        "images": GalleryImage.objects.filter(school=request.school),
    })


@role_required("admin", "webmaster")
def gallery_add(request):
    form = GalleryImageForm(
        request.POST or None,
        request.FILES or None,
    )
    if request.method == "POST" and form.is_valid():
        image = form.save(commit=False)
        image.school = request.school
        image.save()
        messages.success(request, "Gallery image added.")
        return redirect("website:gallery")
    return render(request, "website/gallery_form.html", {
        "form": form,
        "target": None,
    })


@role_required("admin", "webmaster")
def gallery_edit(request, pk):
    image = get_object_or_404(
        GalleryImage.objects.filter(school=request.school), pk=pk
    )
    form = GalleryImageForm(
        request.POST or None,
        request.FILES or None,
        instance=image,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Gallery image updated.")
        return redirect("website:gallery")
    return render(request, "website/gallery_form.html", {
        "form": form,
        "target": image,
    })


@role_required("admin", "webmaster")
@require_POST
def gallery_delete(request, pk):
    image = get_object_or_404(
        GalleryImage.objects.filter(school=request.school), pk=pk
    )
    image.delete()
    messages.success(request, "Gallery image deleted.")
    return redirect("website:gallery")


@role_required("admin", "webmaster")
def teacher_list(request):
    return render(request, "website/teachers.html", {
        "teachers": TeacherProfile.objects.filter(school=request.school),
    })


@role_required("admin", "webmaster")
def teacher_add(request):
    form = TeacherProfileForm(
        request.POST or None,
        request.FILES or None,
    )
    if request.method == "POST" and form.is_valid():
        teacher = form.save(commit=False)
        teacher.school = request.school
        teacher.save()
        messages.success(request, "Teacher profile added.")
        return redirect("website:teachers")
    return render(request, "website/teacher_form.html", {
        "form": form,
        "target": None,
    })


@role_required("admin", "webmaster")
def teacher_edit(request, pk):
    teacher = get_object_or_404(
        TeacherProfile.objects.filter(school=request.school), pk=pk
    )
    form = TeacherProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=teacher,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Teacher profile updated.")
        return redirect("website:teachers")
    return render(request, "website/teacher_form.html", {
        "form": form,
        "target": teacher,
    })


@role_required("admin", "webmaster")
@require_POST
def teacher_delete(request, pk):
    teacher = get_object_or_404(
        TeacherProfile.objects.filter(school=request.school), pk=pk
    )
    teacher.delete()
    messages.success(request, "Teacher profile deleted.")
    return redirect("website:teachers")
