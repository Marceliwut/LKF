"""
Management command to refresh stale IMDb cache for movie proposals.
Can be run periodically via cron or Celery task.

Usage: python manage.py refresh_imdb_cache
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from datetime import timedelta
import requests

from home.models import MovieProposal


class Command(BaseCommand):
    help = 'Refresh cached IMDb data for movie proposals older than 24 hours'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Cache expiration time in hours (default: 24)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of proposals to refresh per run (default: 50)',
        )

    def handle(self, *args, **options):
        cache_hours = options['hours']
        limit = options['limit']
        
        # Find proposals with stale or missing cache
        cutoff_time = timezone.now() - timedelta(hours=cache_hours)
        stale_proposals = MovieProposal.objects.filter(
            imdb_id__isnull=False
        ).filter(
            models.Q(cached_at__isnull=True) | models.Q(cached_at__lt=cutoff_time)
        )[:limit]
        
        updated_count = 0
        error_count = 0
        
        for proposal in stale_proposals:
            try:
                url = f"https://api.imdbapi.dev/titles/{proposal.imdb_id}"
                resp = requests.get(url, timeout=5)
                
                if resp.status_code == 200:
                    payload = resp.json()
                    d = payload.get('title', {}) or payload
                    img = d.get('primaryImage') or {}
                    rating = d.get('rating') or {}
                    
                    imdb_data = {
                        "title": d.get('primaryTitle') or d.get('originalTitle') or "",
                        "year": d.get('startYear') or "",
                        "plot": (d.get('plotOutline', {}).get('text') if isinstance(d.get('plotOutline'), dict) else ""),
                        "runtime": d.get('runtimeSeconds'),
                        "genres": d.get('genres') or [],
                        "poster": img.get('url') if isinstance(img, dict) else "",
                        "imdb_rating": rating.get('aggregateRating'),
                        "imdb_votes": rating.get('voteCount'),
                    }
                    
                    proposal.cached_imdb_data = imdb_data
                    proposal.cached_at = timezone.now()
                    proposal.save()
                    updated_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Updated cache for: {proposal.title} ({proposal.imdb_id})'
                        )
                    )
                else:
                    error_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠ Failed to fetch data for {proposal.title} (HTTP {resp.status_code})'
                        )
                    )
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Error for {proposal.title} ({proposal.imdb_id}): {str(e)}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Cache refresh complete: {updated_count} updated, {error_count} errors'
            )
        )
