from django.shortcuts import render


def index(request):
    return render(request, "index.html", {
        'page_name': 'index',

    })