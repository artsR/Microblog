from flask import Blueprint


bp = Blueprint('main', __name__)


from microblog.main import routes
