from django import forms

from .models import GalleryImage, Notice, School, SchoolWebsite, TeacherProfile


class BootstrapModelForm(forms.ModelForm):
    """Apply the dashboard's Bootstrap styling to every generated field."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs["class"] = "form-control"
            else:
                widget.attrs["class"] = "form-control"


class SchoolDetailsForm(BootstrapModelForm):
    class Meta:
        model = School
        fields = ["name", "address", "phone", "email"]
        labels = {
            "name": "School name",
            "address": "Address",
            "phone": "Phone",
            "email": "Email",
        }


class WebsiteSettingsForm(BootstrapModelForm):
    class Meta:
        model = SchoolWebsite
        fields = [
            "logo",
            "hero_image",
            "primary_color",
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "about_title",
            "about_text",
            "principal_name",
            "principal_title",
            "principal_message",
            "principal_photo",
            "admissions_open",
            "admissions_title",
            "admissions_text",
            "footer_note",
        ]
        widgets = {
            "primary_color": forms.TextInput(attrs={"type": "color"}),
            "hero_subtitle": forms.Textarea(attrs={"rows": 3}),
            "about_text": forms.Textarea(attrs={"rows": 5}),
            "principal_message": forms.Textarea(attrs={"rows": 4}),
            "admissions_text": forms.Textarea(attrs={"rows": 3}),
        }


class NoticeForm(BootstrapModelForm):
    class Meta:
        model = Notice
        fields = ["title", "content", "published_on", "is_important", "is_active"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 6}),
            "published_on": forms.DateInput(attrs={"type": "date"}),
        }


class GalleryImageForm(BootstrapModelForm):
    class Meta:
        model = GalleryImage
        fields = ["title", "caption", "image", "display_order", "is_active"]


class TeacherProfileForm(BootstrapModelForm):
    class Meta:
        model = TeacherProfile
        fields = [
            "name",
            "designation",
            "qualification",
            "bio",
            "photo",
            "display_order",
            "is_active",
        ]
        widgets = {"bio": forms.Textarea(attrs={"rows": 4})}
