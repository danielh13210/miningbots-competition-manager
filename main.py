import os

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

@app.route("/favicon.ico")
def favicon(): return redirect("/static/favicon.ico")
