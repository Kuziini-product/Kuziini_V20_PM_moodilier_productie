# containers/__init__.py
from . import dashboard
from . import overview
from . import sections
from . import new_order
from . import project_settings
from . import users
from . import data_check
from . import user_profile   # ← nou
from . import nav  # dacă există, rămâne disponibil

__all__ = [
    "dashboard",
    "overview",
    "sections",
    "new_order",
    "project_settings",
    "users",
    "data_check",
    "user_profile",
    "nav",
]
