"""
Management command to clean up orphaned ProposalVote records.

This command finds and removes ProposalVote records where the related
User has been deleted. While on_delete=CASCADE should handle this,
data integrity issues can occur.

Usage: python manage.py cleanup_orphaned_votes
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from home.models import ProposalVote


class Command(BaseCommand):
    help = 'Remove orphaned ProposalVote records with missing voters'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        # Find votes with NULL voter_id (orphaned records)
        orphaned_votes = ProposalVote.objects.filter(voter__isnull=True)
        count = orphaned_votes.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ No orphaned votes found. Database is clean!')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠ DRY RUN: Found {count} orphaned vote(s) that would be deleted'
                )
            )
            for vote in orphaned_votes[:5]:
                self.stdout.write(f'  • Vote ID {vote.id} (Proposal: {vote.proposal.title})')
            if count > 5:
                self.stdout.write(f'  ... and {count - 5} more')
        else:
            deleted_count, _ = orphaned_votes.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Cleanup complete: {deleted_count} orphaned vote(s) removed'
                )
            )
