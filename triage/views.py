# triage/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def triage_result(request, case_id):
    """عرض نتيجة التصنيف"""
    return render(request, 'triage/result.html')