import os

from instances import *

from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
import argon2
engine=create_engine(os.environ['POSTGRES_CONNECT_URI'])

Base = declarative_base()

class UserEntry(Base):
    from sqlalchemy import Column, String
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    password = Column(String, nullable=False) # not the password, the hex hash
    uploaddir = Column(String, nullable=False)

class PlayerEntry(Base):
    from sqlalchemy import Column, String, ForeignKey, PrimaryKeyConstraint
    __tablename__ = "players"

    name = Column(String, nullable=False)
    instance = Column(String, nullable=False)
    uploaddir = Column(String, nullable=False)
    ownerID = Column(String, ForeignKey("users.id"), nullable=False)
    testserver = Column(String, nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint("instance","name"),
    )

Base.metadata.create_all(engine)

def check_user(id,password):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT password FROM users WHERE id = :id"),
            {"id": id}
        )
        password_hash=result.scalar()
        try:
            return argon2.PasswordHasher().verify(password_hash,password)
        except argon2.exceptions.VerifyMismatchError:
            return False


def get_player_data(user):
    ownerID=user.id
    with engine.connect() as conn:
        player=conn.execute(text("SELECT name, instance FROM players WHERE \"ownerID\"=:ownerID"),{"ownerID":ownerID}).fetchone()
    return player
app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']  # Load secret key from env

login_manager = LoginManager()
login_manager.init_app(app)

# wrapper for login required routes
def login_view(route,*args,**kwargs):
    def wrapper(view):
        login_manager.login_view = route
        return app.route(route,*args,**kwargs)(view)
    return wrapper

# Example user model
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# User loader callback
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route("/login",methods=['GET'])
@login_view('/login')
def login():
    if current_user.is_authenticated:
        return redirect(request.args.get('next') or '/')
    return render_template("login.html")

@app.route("/login", methods=['POST'])
def login_post():
    username = request.form.get('userID')
    password = request.form.get('password')
    if check_user(username,password):
        login_user(User(id=username))
        return redirect(request.args.get('next') or '/')
    else:
        return render_template("login.html",error="Login incorrect")


@app.route("/")
@login_required
def protected():
    return render_template("index.html", username=current_user.id)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

from flask import make_response, jsonify

@app.route('/testserver/start',methods=['POST'])
@login_required
def start():
    player,instance = get_player_data(current_user)
    if not (error:=start_player(player, instance))['success']:
        return jsonify({"error":"failed to start container",'rawError': error['rawError']}), 500
    return "", 204

@app.route('/testserver/stop',methods=['POST'])
@login_required
def stop():
    player,instance = get_player_data(current_user)
    if not (error:=stop_player(player, instance))['success']:
        return jsonify({"error":"failed to stop container",'rawError': error['rawError']}), 500
    return "", 204

@app.route("/favicon.ico")
def favicon(): return redirect("/static/favicon.ico")
@app.route("/healthcheck")
def healthcheck(): return "",204
