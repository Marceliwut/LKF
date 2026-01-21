from django.db import models
from django.contrib.auth.models import User

from django.utils import timezone

class LogEntry(models.Model):
    ACTION_CHOICES = [
    ('vote_add', 'Dodano głos'),
    ('vote_remove', 'Usunięto głos'),
    ('proposal_create', 'Nowa propozycja'),
    ('proposal_delete', 'Usunięto propozycję'),
    ('movie_mark_watched', 'Oznaczono jako obejrzane'),
    ('login', 'Logowanie'),
    ('register', 'Rejestracja'),      # ← NOWE
    ('logout', 'Wylogowanie'),        # ← NOWE
    ('clear_logs', 'Wyczyszczono logi'),
    ('password_changed', 'Zmieniono hasło'),
]

    
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='movie_logs')  # ← DODAJ related_name
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    proposal_id = models.IntegerField(null=True, blank=True)
    proposal_title = models.CharField(max_length=255, blank=True)
    details = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.timestamp} - {self.user or 'Anonim'}"


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


class MovieProposal(models.Model):
    title = models.CharField(max_length=255)
    imdb_id = models.CharField(max_length=20, blank=True, null=True)
    proposer = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Cached IMDb data to avoid repeated API calls
    cached_imdb_data = models.JSONField(null=True, blank=True)
    cached_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} (proposed by {self.proposer.username})"


class ProposalVote(models.Model):
    proposal = models.ForeignKey(MovieProposal, on_delete=models.CASCADE, related_name='proposal_votes')
    voter = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('proposal', 'voter')  # One vote per user per proposal
    
    def __str__(self):
        return f"{self.voter.username} voted for {self.proposal.title}"


class MovieRating(models.Model):
    movie_title = models.CharField(max_length=255)  # Movie title from CSV
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='movie_ratings')
    rating = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('movie_title', 'user')  # One rating per user per movie
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} rated '{self.movie_title}' {self.rating}/5"


class UserProposalLimit(models.Model):
    """Store custom proposal limits for users. Default is 10 if not present."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='proposal_limit')
    limit = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Limit: {self.limit}"
