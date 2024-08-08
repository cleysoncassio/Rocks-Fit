from django.shortcuts import render
from blog.models import ContactInfo, ContactMessage, Program, Schedule
from .models import BlogPost, Event

def home(request):
    return render(request, "home.html")


def programs(request):
    programs = Program.objects.all()
    return render(request, "programs.html", {"programs": programs})


def schedule(request):
    schedules = Schedule.objects.all()
    return render(request, "schedule.html", {"schedules": schedules})


def contact(request):
    contact_info = ContactInfo.objects.first()
    if request.method == "POST":
        name = request.POST["name"]
        email = request.POST["email"]
        message = request.POST["message"]
        ContactMessage.objects.create(name=name, email=email, message=message)
        return render(
            request, "contact.html", {"contact_info": contact_info, "success": True}
        )
    return render(request, "contact.html", {"contact_info": contact_info})


def trainers(request):
    return render(request, "trainers.html")


def about(request):
    return render(request, "about.html")

def index(request):
    blog_posts = BlogPost.objects.all()
    events = Event.objects.all()
    context = {
        'blog_posts': blog_posts,
        'events': events,
    }
    return render(request, 'index.html', context)