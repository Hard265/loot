import json
from django.conf import settings
from pathlib import Path

def get_vite_asset(filename):
    manifest_path = Path(settings.BASE_DIR) / 'static' / 'dist' / 'manifest.json'
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    return 'dist/' + manifest[filename]['file']
