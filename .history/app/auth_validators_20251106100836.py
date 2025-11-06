import re

# Retourne (True, None) si OK, sinon (False, "Message d'erreur")
def validate_password_strength(password: str, *, min_length: int = 8):
    if not isinstance(password, str):
        return False, "Mot de passe invalide."
    if len(password) < min_length:
        return False, f"Le mot de passe doit contenir au moins {min_length} caractères."
    if not re.search(r"[A-Z]", password):
        return False, "Le mot de passe doit contenir au moins une lettre majuscule."
    if not re.search(r"[a-z]", password):
        return False, "Le mot de passe doit contenir au moins une lettre minuscule."
    if not re.search(r"\d", password):
        return False, "Le mot de passe doit contenir au moins un chiffre."
    if not re.search(r"[^\w\s]", password):
        return False, "Le mot de passe doit contenir au moins un caractère spécial (ex: !@#$%)."
    return True, None