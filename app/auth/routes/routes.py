from app.auth import blp as auth_blp
from flask import jsonify
from flask.views import MethodView
from flask_smorest import abort
from flask_jwt_extended import jwt_required, get_jwt, create_access_token
from app.schemas import UserSchema
from app.models import User
from app import db, jwt
from datetime import datetime


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return (
        jsonify({"message": "The token has expired.", "error": "token_expired"}),
        401,
    )

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return (
        jsonify(
            {"message": "Signature verification failed.", "error": "invalid_token"}
        ),
        401,
    )

@jwt.unauthorized_loader
def missing_token_callback(error):
    return (
        jsonify(
            {
                "description": "Request does not contain an access token.",
                "error": "authorization_required",
            }
        ),
        401,
    )


@auth_blp.route('/users')
class AccountAdminView(MethodView):

    @jwt_required()
    @auth_blp.response(200, UserSchema(many=True))
    def get(self):
        jwt = get_jwt()
        if jwt.get("role") != 'administrator':
            abort(403, message="Administrator  privileges required.")
        else:
            User.ping()
            users = User.query.all()
        return users
    
    @jwt_required()
    @auth_blp.arguments(UserSchema)
    @auth_blp.response(201, UserSchema)
    def post(self, user_data):
        jwt = get_jwt()
        if jwt.get("role") != 'administrator':
            abort(403, message="Administrator privileges required.")
        else:
            user = User(username=user_data["username"], password=user_data["password"], email=user_data["email"])
            db.session.add(user)
            db.session.commit()
            return user
    
@auth_blp.route('/login')
class AuthenticationView(MethodView):
    
    @auth_blp.arguments(UserSchema)
    def post(self, user_data):
        user = User.query.filter_by(email=user_data["email"]).first()

        if user.verify_password(user_data["password"]) and not user.account_locked:
            add_claims = {
                "role": user.role,
                "iat": datetime.utcnow(),
                "id": user.id
            }
            access_token = create_access_token(identity=user.id, additional_claims=add_claims)
            return {"access_token": access_token}, 200
        user.failed_pwd += 1
        if user.failed_pwd >= 3:
            user.account_locked = True
        db.session.commit()
        if user.account_locked:
            abort(401, message="Account is locked out.")
        abort (401, message="Invalid credentials.")