from django.db import models


class Media(models.Model):
    number = models.IntegerField()  # Represents the serial number
    title = models.CharField(max_length=255)
    year = models.IntegerField()
    duration = models.CharField(max_length=50)
    age_rating = models.CharField(max_length=50)
    rating = models.FloatField()
    votes = models.IntegerField()
    metascore = models.IntegerField(null=True, blank=True)  # Some values could be missing
    description = models.TextField()
    watched = models.BooleanField(default=False)
    skipped = models.BooleanField(default=False)
    series = models.BooleanField(default=False)
