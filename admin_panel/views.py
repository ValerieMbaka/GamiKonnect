from django.shortcuts import render


def admin_login(request):
    return render(request, "admin_panel/base/admin_login.html")

