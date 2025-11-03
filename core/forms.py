from django import forms

class UploadYAMLForm(forms.Form):
    file = forms.FileField(
        label="Tệp YAML",
        help_text="Chọn file .yaml hoặc .yml để nhập dữ liệu truyện",
    )
