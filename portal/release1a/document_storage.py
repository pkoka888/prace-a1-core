"""Private Django Storage; no public URL, no names or identifiers in keys."""
import re
from pathlib import Path
from django.conf import settings
from django.core.files.storage import FileSystemStorage


class ProtectedDocumentStorage(FileSystemStorage):
    def __init__(self):
        root = Path(getattr(settings, "DOCUMENT_STORAGE_ROOT", settings.BASE_DIR / "runtime" / "portal"))
        super().__init__(location=root, file_permissions_mode=0o600, directory_permissions_mode=0o700)

    def path(self, name):
        if not re.fullmatch(r"(?:documents|generated)/[a-f0-9]{32}(?:/[a-f0-9]{64})?\.(?:source|json|png)", name):
            raise ValueError("INVALID_STORAGE_KEY")
        return super().path(name)

    def url(self, name):
        raise ValueError("PROTECTED_STORAGE_HAS_NO_URL")


def document_storage():
    return ProtectedDocumentStorage()
