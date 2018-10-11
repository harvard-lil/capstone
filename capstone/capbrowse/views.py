from django.shortcuts import render

# Create your views here.

def browse_case(request, case_id):
    return render(request, "browse_case.html", {'case_id':case_id})

def browse_cases(request, case_id):
    return render(request, "browse_case.html")
