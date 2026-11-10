from flask import Flask
import sqlite3
from flask import redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import config
import db
import songs as song_service

app = Flask(__name__)
app.config.from_object(config)

@app.route("/")
def index():
    all_songs = song_service.get_songs()
    return render_template("index.html", songs=all_songs)

@app.route("/find_song")
def find_song():
    query = request.args.get("query", "").strip()
    results = song_service.search_songs(query) if query else []
    return render_template("find_song.html", query=query, results=results)

@app.route("/songs", strict_slashes=False)
def songs():
    return render_template("songs.html")

@app.route("/songs/<int:song_id>")
def song(song_id):
    song_details = song_service.get_song(song_id)
    if not song_details:
        return "Kappaletta ei löytynyt", 404
    return render_template("show_song.html", song=song_details[0])

@app.route("/songs/<int:song_id>/edit", methods=["GET", "POST"])
def edit_song(song_id):
    song_details = song_service.get_song(song_id)
    if not song_details:
        return "Kappaletta ei löytynyt", 404
    song_to_edit = song_details[0]
    if not session.get("user_id") or session["user_id"] != song_to_edit["user_id"]:
        return "Ei käyttöoikeutta", 403

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        artist = request.form.get("artist", "").strip()
        tabulatuuri = request.form.get("tabulatuuri", "").strip()
        result = song_service.update_song(song_id, session["user_id"], title, artist, tabulatuuri)
        if result is not None:
            return result
        return redirect(url_for("song", song_id=song_id))

    return render_template("edit_song.html", song=song_to_edit)

@app.route("/songs/<int:song_id>/delete", methods=["GET", "POST"])
def delete_song(song_id):
    song_details = song_service.get_song(song_id)
    if not song_details:
        return "Kappaletta ei löytynyt", 404
    if not session.get("user_id") or session["user_id"] != song_details[0]["user_id"]:
        return "Ei käyttöoikeutta", 403

    if request.method == "GET":
        return render_template("remove_song.html", song=song_details[0])

    result = song_service.delete_song(song_id, session["user_id"])
    if result is not None:
        return result
    return redirect(url_for("index"))

@app.route("/songs/create", methods=["POST"])
def create_item():
    db.ensure_songs_schema()
    title = request.form.get("title", "").strip()
    artist = request.form.get("artist", "").strip()
    tabulatuuri = request.form.get("tabulatuuri", "").strip()
    user_id = session.get("user_id")

    result = song_service.add_song(title, artist, tabulatuuri, user_id)
    if result is not None:
        return result

    return redirect(url_for("index"))

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/create", methods=["POST"])
def create():
    username = request.form.get("username", "").strip()
    password1 = request.form.get("password1", "")
    password2 = request.form.get("password2", "")
    if not username or not password1 or not password2:
        return "VIRHE: kaikki kentät ovat pakollisia", 400
    if password1 != password2:
        return "VIRHE: salasanat eivät ole samat"
    password_hash = generate_password_hash(password1)

    try:
        sql = "INSERT INTO users (username, password_hash) VALUES (?, ?)"
        db.execute(sql, [username, password_hash])
    except sqlite3.IntegrityError:
        return "VIRHE: tunnus on jo varattu"

    return "Tunnus luotu"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        sql = "SELECT id, password_hash FROM users WHERE username = ?"
        rows = db.query(sql, [username])
        if not rows:
            return "VIRHE: väärä tunnus tai salasana"

        user_id = rows[0]["id"]
        password_hash = rows[0]["password_hash"]

        if check_password_hash(password_hash, password):
            session["user_id"] = user_id
            session["username"] = username
            return redirect("/")
        else:
            return "VIRHE: väärä tunnus tai salasana"

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")