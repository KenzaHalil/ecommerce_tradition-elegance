from pathlib import Path
import sys

# ajouter la racine du projet au PYTHONPATH pour que "import run" fonctionne
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# adapte le nom si ton factory/entrypoint est différent
from run import create_app

app = create_app()
with app.app_context():
    rules = sorted(app.url_map.iter_rules(), key=lambda r: (r.rule, sorted(r.methods)))
    for r in rules:
        methods = ",".join(sorted(r.methods - {"HEAD", "OPTIONS"}))
        print(f"{r.rule:40}  [{methods:15}] -> {r.endpoint}")