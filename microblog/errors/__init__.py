"""Creation of the 'Error Blueprint' - quite similar to the application creation."""

from flask import Blueprint


bp = Blueprint('errors', __name__)


# import is at the bottom to avoid circular dependencies
# (whatever they are..)
from microblog.errors import handlers
