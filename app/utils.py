def luhn_valid(number: str) -> bool:
    """Retourne True si number (avec ou sans espaces) passe l'algorithme de Luhn."""
    s = ''.join(ch for ch in str(number) if ch.isdigit())
    if not 13 <= len(s) <= 19:
        return False

    # rejeter les numéros triviaux composés d'un seul chiffre (ex: "0000...") 
    # -> considérés invalides même s'ils passent Luhn
    if len(set(s)) == 1:
        return False

    total, alt = 0, False
    for d in reversed(s):
        n = int(d)
        if alt:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        alt = not alt
    return total % 10 == 0