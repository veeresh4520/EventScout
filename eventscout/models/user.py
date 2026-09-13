"""
User domain model for EventScout.
Stores authentication credentials and personalization preferences.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class User:
    """
    Canonical User model.
    Passwords are NEVER stored in plain text; only password_hash is stored.
    saved_event_ids holds MongoDB _id strings of events saved by this user.
    """

    email: str
    password_hash: str

    # Personalization preferences
    interests: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    preferred_event_types: List[str] = field(default_factory=list)
    preferred_modes: List[str] = field(default_factory=list)

    # User-specific saved event relationships (stored as event _id strings)
    saved_event_ids: List[str] = field(default_factory=list)

    # Roles and Permissions
    is_admin: bool = False

    # Metadata
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a MongoDB-insertable dictionary."""
        return {
            "email": self.email,
            "password_hash": self.password_hash,
            "interests": self.interests,
            "skills": self.skills,
            "preferred_event_types": self.preferred_event_types,
            "preferred_modes": self.preferred_modes,
            "saved_event_ids": self.saved_event_ids,
            "is_admin": self.is_admin,
            "created_at": self.created_at,
        }

    def to_public_dict(self) -> Dict[str, Any]:
        """
        Safe public representation — NEVER includes password_hash.
        Used in API responses.
        """
        return {
            "email": self.email,
            "interests": self.interests,
            "skills": self.skills,
            "preferred_event_types": self.preferred_event_types,
            "preferred_modes": self.preferred_modes,
            "saved_event_ids": self.saved_event_ids,
            "is_admin": self.is_admin,
            "created_at": self.created_at,
        }
