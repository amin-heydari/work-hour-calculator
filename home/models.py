from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class WorkSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    work_mode = models.CharField(max_length=10, choices=[('in_person', 'In-Person'), ('remote', 'Remote')])
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.date}"
