from django.db import models

# Create your models here.
class Student(models.Model):
    name = models.CharField(max_length=10)
    email = models.CharField(max_length=20)
    birthday = models.DateField()
    age = models.IntegerField()

    def __str__(self):
        return self.name