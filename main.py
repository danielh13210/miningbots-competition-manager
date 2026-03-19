import os

from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = 'secret'  # Load secret key from env

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
    # For demonstration, we accept any username/password
    user = User(username)
    login_user(user)
    return redirect(request.args.get('next') or '/')


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
