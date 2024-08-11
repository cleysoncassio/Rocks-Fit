from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # Campos adicionais para o seu modelo de User personalizado
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to="user_avatars/", null=True, blank=True)
    website = models.URLField(max_length=100, blank=True)

    # Se você quiser adicionar campos aos grupos e permissões para evitar conflitos
    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name="groups",
        blank=True,
        related_name="blog_users",
        related_query_name="blog_user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name="user permissions",
        blank=True,
        related_name="blog_users",
        related_query_name="blog_user",
    )

    def __str__(self):
        return self.username


class Program(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to="program_images/", blank=True, null=True)
    join_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name


class Trainer(models.Model):
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, blank=True, null=True)  # Para o título como "Professor"
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="trainer_images/", blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name


class Schedule(models.Model):
    DAY_CHOICES = [
        ("sunday", "Sunday"),
        ("monday", "Monday"),
        ("tuesday", "Tuesday"),
        ("wednesday", "Wednesday"),
        ("thursday", "Thursday"),
        ("friday", "Friday"),
        ("saturday", "Saturday"),
    ]

    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    Trainers = models.ForeignKey(Trainer, on_delete=models.CASCADE, default=1)  # Use um ID válido

    def __str__(self):
        return f"{self.program.name} on {self.day} from {self.start_time} to {self.end_time}"


class ContactInfo(models.Model):
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.address


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} at {self.created_at}"


class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    content = models.TextField()
    posted_on = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='images/', null=True, blank=True)
    comments_count = models.IntegerField(default=0)

    def __str__(self):
        return self.title

class Event(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    description = models.TextField()
    event_date = models.DateField()
    comments_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.title} on {self.event_date}"
