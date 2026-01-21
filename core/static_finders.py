from django.contrib.staticfiles.finders import FileSystemFinder

class IgnoreScssFinder(FileSystemFinder):
    ignore_patterns = ["*.scss"]

    def list(self, ignore_patterns):
        ignore_patterns = tuple(ignore_patterns) + tuple(self.ignore_patterns)
        return super().list(ignore_patterns)
