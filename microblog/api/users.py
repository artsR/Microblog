# microblog/api/users.py


from flask import request, g, abort
from flask import jsonify, url_for
from microblog import db
from microblog.api import bp
from microblog.api.auth import token_auth
from microblog.api.errors import bad_request
from microblog.models import User



@bp.route('/users/<int:id>', methods=['GET'])
@token_auth.login_required
def get_user(id):

    return jsonify(User.query.get_or_404(id).to_dict())


@bp.route('/users', methods=['GET'])
@token_auth.login_required
def get_users():

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    data = User.to_collection_dict(User.query, page, per_page, 'api.get_users')

    return jsonify(data)


@bp.route('/users/<int:id>/followers', methods=['GET'])
@token_auth.login_required
def get_followers(id):

    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    data = User.to_collection_dict(user.followers, page, per_page,
                                'api.get_followers', id=id)
    return jsonify(data)


@bp.route('/users/<int:id>/followed', methods=['GET'])
@token_auth.login_required
def get_followed(id):

    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    data = User.to_collection_dict(user.followed, page, per_page,
                                'api.get_followed', id=id)
    return jsonify(data)


@bp.route('/users', methods=['POST'])
def create_user():

    data = request.get_json() or {}

    if 'username' not in data or 'email' not in data or 'password' not in data:
        return bad_request('Must include username, email and password fields')
    if User.query.filter_by(username=data['username']).first():
        return bad_request('Please use a different username')
    if User.query.filter_by(email=data['email']).first():
        return bad_request('Provided email address already used')

    user = User()
    user.from_dict(data, new_user=True)
    db.session.add(user)
    db.session.commit()
    response = jsonify(user.to_dict())
    response.status_code = 201
    response.headers['Location'] = url_for('api.get_user', id=user.id)

    return response


@bp.route('/users/<int:id>', methods=['PUT'])
@token_auth.login_required
def update_user(id):

    if g.current_user.id != id:
        abort(403)

    user = User.query.get_or_404(id)
    data = request.get_json() or {}

    if ('username' in data and data['username'] != user.username
            and User.query.filter_by(username=data['username']).first()):
        return bad_request('Please use a different username')
    if ('email' in data and data['email'] != user.email
            and User.query.filter_by(email=data['email']).first()):
        return bad_request('Please use a different email address')

    user.from_dict(data, new_user=False)
    db.session.commit()

    return jsonify(user.to_dict())