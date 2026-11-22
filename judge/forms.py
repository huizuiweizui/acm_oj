"""ACM OJ 表单"""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Submission, Discussion, DiscussionReply


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label='邮箱')

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input'

    def _post_clean(self):
        # 跳过 Django 默认密码复杂度校验，只保留最小长度
        forms.ModelForm._post_clean(self)

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1', '')
        password2 = self.cleaned_data.get('password2', '')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('两次输入的密码不一致')
        if len(password2) <= 8:
            raise forms.ValidationError('密码长度必须大于8位')
        return password2


class LoginForm(forms.Form):
    username = forms.CharField(label='用户名', widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '用户名或邮箱'}))
    password = forms.CharField(label='密码', widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': '密码'}))


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['language', 'code']
        widgets = {
            'language': forms.Select(attrs={'class': 'form-select', 'id': 'language-select'}),
            'code': forms.Textarea(attrs={
                'class': 'code-textarea', 'id': 'code-editor',
                'rows': 20, 'placeholder': '在此输入你的代码...', 'spellcheck': 'false',
            }),
        }


class ProblemFilterForm(forms.Form):
    DIFFICULTY_CHOICES = [
        ('', '全部难度'),
        ('暂无评定', '暂无评定'),
        ('入门', '入门'),
        ('普及-', '普及-'),
        ('普及/提高-', '普及/提高-'),
        ('普及+/提高', '普及+/提高'),
        ('提高+/省选-', '提高+/省选-'),
        ('省选/NOI-', '省选/NOI-'),
        ('NOI/NOI+/CTSC', 'NOI/NOI+/CTSC'),
    ]
    keyword = forms.CharField(required=False, label='搜索', widget=forms.TextInput(attrs={
        'class': 'form-input', 'placeholder': '搜索题目标题或编号...'
    }))
    difficulty = forms.ChoiceField(required=False, choices=DIFFICULTY_CHOICES, widget=forms.Select(attrs={
        'class': 'form-select'
    }))


class DiscussionForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '帖子标题'}),
            'content': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 8, 'placeholder': '支持 Markdown...'}),
        }


class ReplyForm(forms.ModelForm):
    class Meta:
        model = DiscussionReply
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': '写下你的回复...'}),
        }
