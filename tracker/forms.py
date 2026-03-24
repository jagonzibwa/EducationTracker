"""
tracker/forms.py - Django Forms for Class and Student Management

Defines ModelForms for creating and editing SchoolClass and Student objects.
Each form uses Tailwind CSS classes on the widgets for consistent styling
throughout the application.

Note: The bulk attendance form (radio buttons for each student) is handled
dynamically in the template and view, not as a Django ModelForm, because
it processes multiple students at once.
"""

from django import forms
from .models import SchoolClass, Student, GradeRecord

# Reusable Tailwind CSS classes for form input styling
TAILWIND_INPUT_CLASS = (
    'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm '
    'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500'
)


class SchoolClassForm(forms.ModelForm):
    """
    Form for creating and editing SchoolClass objects.

    Fields:
        name: The name of the class (e.g., 'Primary 5A')
        teacher: Dropdown to assign a teacher (only shows users with 'teacher' role)
    """

    class Meta:
        model = SchoolClass
        fields = ['name', 'teacher']
        # Apply Tailwind CSS styling to each form widget
        widgets = {
            'name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'e.g., Grade 5A'
            }),
            'teacher': forms.Select(attrs={
                'class': TAILWIND_INPUT_CLASS
            }),
        }

    def __init__(self, *args, **kwargs):
        """
        Customize the form after initialization.

        - Filters the teacher dropdown to only show users with the 'teacher' role
        - Makes the teacher field optional (a class can exist without an assigned teacher)
        """
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        # Only show teachers in the dropdown, not admins
        self.fields['teacher'].queryset = User.objects.filter(profile__role='teacher')
        # Allow creating a class without immediately assigning a teacher
        self.fields['teacher'].required = False


class StudentForm(forms.ModelForm):
    """
    Form for creating and editing Student objects.

    Fields:
        first_name: Student's first name
        last_name: Student's last name
        school_class: Dropdown to select which class the student belongs to
        parent_name: Name of the student's parent/guardian
        parent_phone: Phone number for SMS notifications (Uganda format: +256...)
    """

    class Meta:
        model = Student
        fields = ['first_name', 'last_name', 'school_class', 'parent_name', 'parent_phone']
        # Apply Tailwind CSS styling to each form widget
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
            }),
            'last_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
            }),
            'school_class': forms.Select(attrs={
                'class': TAILWIND_INPUT_CLASS,
            }),
            'parent_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'Parent/Guardian full name'
            }),
            'parent_phone': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': '+256700000000'  # Uganda phone format
            }),
        }


class GradeRecordForm(forms.ModelForm):
    """Form for recording a single grade entry."""

    class Meta:
        model = GradeRecord
        fields = ['student', 'subject', 'score', 'term']
        widgets = {
            'student': forms.Select(attrs={'class': TAILWIND_INPUT_CLASS}),
            'subject': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'e.g., Mathematics'
            }),
            'score': forms.NumberInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'min': '0', 'max': '100', 'step': '0.01'
            }),
            'term': forms.Select(attrs={'class': TAILWIND_INPUT_CLASS}),
        }
