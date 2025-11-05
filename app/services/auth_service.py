from app.models.user import User
from app.utils.password_hasher import PasswordHasher
import uuid
from typing import Optional
from app.services.address_validator import validate_address_nominatim

class AuthService:
    def __init__(self, users: UserRepository, sessions: SessionManager):
        self.users = users
        self.sessions = sessions

    def register(self, email: str, password: str, first_name: str, last_name: str, address: str, is_admin: bool=False, countrycodes: Optional[str]=None) -> User:
        if self.users.get_by_email(email):
            raise ValueError("Email déjà utilisé.")

        # Validation d'adresse via Nominatim (dev). strict=True -> exige ville+code postal.
        addr_info = validate_address_nominatim(address, countrycodes=countrycodes, strict=True)
        if addr_info is None:
            # On refuse l'inscription si l'adresse est introuvable
            raise ValueError("Adresse invalide ou introuvable. Veuillez vérifier et réessayer.")

        # Normaliser l'adresse stockée (display_name) pour la livraison
        normalized_address = addr_info.get("display_name") or address

        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=PasswordHasher.hash(password),
            first_name=first_name,
            last_name=last_name,
            address=normalized_address,
            is_admin=is_admin
        )
        self.users.add(user)
        return user