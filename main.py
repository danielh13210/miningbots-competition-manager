import os

from instances import *

import datetime

from flask import Flask, render_template, redirect, url_for, request, abort, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
import argon2

import re
submission_matcher = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\.zip$")

import zipfile

engine=create_engine(os.environ['POSTGRES_CONNECT_URI'])

Base = declarative_base()

class UserEntry(Base):
    from sqlalchemy import Column, String
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    password = Column(String, nullable=False) # not the password, the hex hash
    uploaddir = Column(String, nullable=False)

class PlayerEntry(Base):
    from sqlalchemy import Column, String, BigInteger, ForeignKey, PrimaryKeyConstraint
    __tablename__ = "players"

    name = Column(String, nullable=False)
    instance = Column(String, nullable=False)
    uploaddir = Column(String, nullable=False)
    ownerID = Column(String, ForeignKey("users.id"), nullable=False)
    instance_observer_key = Column(BigInteger, nullable=False)
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
        if not password_hash: return False
        try:
            return argon2.PasswordHasher().verify(password_hash,password)
        except argon2.exceptions.VerifyMismatchError:
            return False


def get_player_data(user,include_global_data=False):
    ownerID=user.id
    with engine.connect() as conn:
        if include_global_data:
            player=conn.execute(text("SELECT username, name, instance, instance_observer_key, instance_config_dir FROM players WHERE \"ownerID\"=:ownerID"),{"ownerID":ownerID}).fetchone()
        else:
            player=conn.execute(text("SELECT username, name, instance FROM players WHERE \"ownerID\"=:ownerID"),{"ownerID":ownerID}).fetchone()
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

def is_testserver_running(user):
    ownerID,player,instance = get_player_data(user)
    return is_running(ownerID,player,instance)

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

@app.route("/competitionserver")
@login_required
def competitionserver():
    return render_template("competitionserver.html", username=current_user.id)

@app.route("/config/<string:filename>")
@app.route("/submission/<string:filename>")
def config(filename):
    instanceOwner, player, instance = get_player_data(current_user)
    uploaddir = os.path.join('/tmp', f'{instanceOwner}-{instance}-{player}')
    if not os.path.exists(os.path.join(uploaddir, filename)):
        abort(404)
    return send_from_directory(uploaddir, filename)

@app.route("/testserver")
@login_required
def testserver():
    ownerID, player, instance = get_player_data(current_user)
    if container:=get_testserver_info(ownerID, player, instance):
        return render_template("testserver.html", player=player, frontend_url=os.environ['fe_host'], server_url=f'https://{get_url(container)}', isrunning=is_running(container), observer_key=get_observer_key(container), username=current_user.id)
    else:
        return render_template("testserver.html", player=player, frontend_url=os.environ['fe_host'], server_url=None, isrunning=False, observer_key=None, username=current_user.id)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

from flask import jsonify

@app.route('/testserver/start',methods=['POST'])
@login_required
def start():
    ownerID, player, instance, instance_observer_key, instance_config_dir = get_player_data(current_user,True)
    if not (error:=spawn_player(ownerID, player, instance,instance_observer_key,instance_config_dir))['success']:
        return jsonify({"error":"failed to start container",'rawError': error['rawError']}), 500
    return "", 204

@app.route('/testserver/stop',methods=['POST'])
@login_required
def stop():
    ownerID, player, instance = get_player_data(current_user)
    if not (error:=stop_player(ownerID, player, instance))['success']:
        return jsonify({"error":"failed to stop container",'rawError': error['rawError']}), 500
    return "", 204

@app.route('/submit',methods=['POST'])
@login_required
def submit():
    # Check if submission file exists
    if 'submission' not in request.files or request.files['submission'].filename == '':
        return jsonify({"error": "No submission file provided"}), 400

    # Get upload directory from database
    with engine.connect() as conn:
        result = conn.execute(text("SELECT uploaddir FROM players WHERE \"ownerID\"=:ownerID"),{"ownerID":current_user.id}).fetchone()
        if not result:
            return jsonify({"error": "Player data not found"}), 400
        uploaddir = result[0]

    if not uploaddir or not os.path.exists(uploaddir):
        return jsonify({"error": "Upload directory not accessible"}), 500

    try:
        targetfile = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")+".zip"
        request.files['submission'].save(os.path.join(uploaddir, targetfile))

        import shutil
        unzipped_dir = os.path.join(uploaddir, 'current-player')
        shutil.rmtree(unzipped_dir, ignore_errors=True)
        os.makedirs(unzipped_dir)

        safe_extract(zipfile.ZipFile(os.path.join(uploaddir, targetfile)), unzipped_dir)
        return render_template("submitsuccess.html", username=current_user.id)
    except Exception as e:
        return jsonify({"error": "Failed to process submission", "details": str(e)}), 500

@app.route("/history")
@login_required
def history():
    # Get upload directory from database
    with engine.connect() as conn:
        result = conn.execute(text("SELECT uploaddir FROM players WHERE \"ownerID\"=:ownerID"),{"ownerID":current_user.id}).fetchone()
        if not result:
            return jsonify({"error": "Player data not found"}), 400
        uploaddir = result[0]

    if not uploaddir or not os.path.exists(uploaddir):
        return jsonify({"error": "Upload directory not accessible"}), 500

    submissions = list(filter(submission_matcher.match, os.listdir(uploaddir)))
    submissions.sort(key=lambda x: datetime.datetime.strptime(x[:-4], "%Y-%m-%d-%H-%M-%S"),reverse=True)
    return render_template("history.html", username=current_user.id, submissions=submissions)

@app.route("/favicon.ico")
def favicon(): return redirect("/static/favicon.ico")
@app.route("/healthcheck")
def healthcheck(): return "",204
