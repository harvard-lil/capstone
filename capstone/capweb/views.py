from django.shortcuts import render


def index(request):
    return render(request, "index.html", {'page_name': 'index'})


def about(request):
    return render(request, "about.html", {"page_name": "about"})


def tools(request):
    return render(request, "tools.html", {"page_name": "tools"})
