from flask import Flask, abort
import sqlite3
from flask import redirect, make_response, render_template, request, session, url_for
import config
import db
import songs as song_service
import users

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
    login_redirect = require_user_logged_in()
    if login_redirect:
        return login_redirect
    classes = song_service.get_all_classes()
    return render_template("songs.html", classes=classes)

@app.route("/create_comment", methods=["POST"])
def create_comment():
    login_redirect = require_user_logged_in()
    if login_redirect:
        return login_redirect

    content = request.form.get("content", "").strip()
    if not content:
        return "VIRHE: kommentti puuttuu", 400
    if len(content) > 500:
        return "VIRHE: kommentin pituus on liian pitkä", 400

    song_id = request.form.get("song_id", "").strip()
    if not song_id:
        return "VIRHE: kappaleen ID puuttuu", 400
    if not song_id.isdigit():
        return "VIRHE: virheellinen kappaleen ID", 400
    song_id = int(song_id)
    if not song_service.get_song(song_id):
        return "Kappaletta ei löytynyt", 404

    user_id = session.get("user_id")
    song_service.add_comment(song_id, user_id, content)
    return redirect(url_for("song", song_id=song_id))



@app.route("/user/<int:user_id>")
def show_user(user_id):
    user = users.get_user(user_id)
    if not user:
        return "Käyttäjää ei löytynyt", 404
    songs = users.get_songs(user_id)
    return render_template("show_user.html", user=user, songs=songs)

@app.route("/songs/<int:song_id>")
def song(song_id):
    song_details = song_service.get_song(song_id)
    if not song_details:
        return "Kappaletta ei löytynyt", 404
    classes = song_service.get_classes(song_id)
    song_comments = song_service.get_comments(song_id)
    images = song_service.get_images(song_id)
    review_count, review_average, user_rating = song_service.get_review_data(
        song_id, session.get("user_id")
    )
    return render_template(
        "show_song.html",
        song=song_details,
        classes=classes,
        comments=song_comments,
        review_count=review_count,
        review_average=review_average,
        user_rating=user_rating,
        images=images,
    )

@app.route("/image/<int:image_id>")
def show_image(image_id):
    image = song_service.get_image(image_id)
    if not image:
        abort(404)

    response = make_response(bytes(image))
    response.headers.set("Content-Type", "image/png")
    return response

@app.route("/images/<int:song_id>")
def edit_images(song_id):
    login_redirect = require_user_logged_in()
    if login_redirect:
        return login_redirect
    song_details = song_service.get_song(song_id)
    if not song_details:
        abort(404)
    if song_details["user_id"] != session["user_id"]:
        abort(403)

    images = song_service.get_images(song_id)
    return render_template("images.html", song=song_details, images=images)

@app.route("/add_image", methods=["POST"])
def add_image():
    login_redirect = require_user_logged_in()
    if login_redirect:
        return login_redirect

    song_id = request.form.get("song_id", "").strip()
    if not song_id.isdigit():
        return "VIRHE: virheellinen kappaleen ID", 400
    song_id = int(song_id)
    song_details = song_service.get_song(song_id)
    if not song_details:
        abort(404)
    if song_details["user_id"] != session["user_id"]:
        abort(403)

    image_file = request.files.get("image")
    if not image_file or not image_file.filename:
        return "VIRHE: kuva puuttuu", 400
    if not image_file.filename.lower().endswith(".png"):
        return "VIRHE: väärä tiedostomuoto", 400

    image = image_file.stream.read(100 * 1024 + 1)
    if len(image) > 100 * 1024:
        return "VIRHE: liian suuri kuva", 400
    if not image.startswith(b"\x89PNG\r\n\x1a\n"):
        return "VIRHE: tiedosto ei ole PNG-kuva", 400

    song_service.add_image(song_id, image)
    return redirect(url_for("edit_images", song_id=song_id))

@app.route("/remove_image", methods=["POST"])
def remove_images():
    login_redirect = require_user_logged_in()
    if login_redirect:
        return login_redirect

    song_id = request.form.get("song_id", "").strip()
    if not song_id.isdigit():
        return "VIRHE: virheellinen kappaleen ID", 400
    song_id = int(song_id)
    song_details = song_service.get_song(song_id)
    if not song_details:
        abort(404)
    if song_details["user_id"] != session["user_id"]:
        abort(403)

    for image_id in request.form.getlist("image_id"):
        song_service.remove_image(song_id, image_id)

    return redirect("/images/" + str(song_id))


@app.route("/songs/<int:song_id>/review", methods=["POST"])
def create_review(song_id):
    login_redirect = require_user_logged_in()
    if login_redirect:
        return login_redirect

    song_details = song_service.get_song(song_id)
    if not song_details:
        return "Kappaletta ei löytynyt", 404
    if session["user_id"] == song_details["user_id"]:
        return "Et voi arvioida omaa kappalettasi", 403

    rating_value = request.form.get("rating", "")
    if not rating_value.isdigit():
        return "VIRHE: arvosanan tulee olla kokonaisluku väliltä 1–5", 400
    rating = int(rating_value)
    if rating < 1 or rating > 5:
        return "VIRHE: arvosanan tulee olla kokonaisluku väliltä 1–5", 400

    song_service.save_review(song_id, session["user_id"], rating)
    return redirect(url_for("song", song_id=song_id))

@app.route("/songs/<int:song_id>/edit", methods=["GET", "POST"])
def edit_song(song_id):
    song_details = song_service.get_song(song_id)
    if not song_details:
        return "Kappaletta ei löytynyt", 404
    song_to_edit = song_details
    if not session.get("user_id") or session["user_id"] != song_to_edit["user_id"]:
        return "Ei käyttöoikeutta", 403

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        artist = request.form.get("artist", "").strip()
        tabulatuuri = request.form.get("tabulatuuri", "").strip()
        if not title or len(title) > 50:
            return "VIRHE: kappaleen nimi on liian pitkä", 400
        if not artist or len(artist) > 50:
            return "VIRHE: artistin nimi on liian pitkä", 400
        if not tabulatuuri or len(tabulatuuri) > 1000:
            return "VIRHE: tabulatuurin pituus on liian pitkä", 400

        classes = []
        all_classes = song_service.get_all_classes()
        for entry in request.form.getlist("classes"):
            if entry:
                parts = entry.split(":", 1)
                if len(parts) != 2:
                    abort(403)
                title_name, value = parts
                if title_name not in all_classes or value not in all_classes[title_name]:
                    abort(403)
                classes.append((title_name, value))
        result = song_service.update_song(
            song_id, session["user_id"], title, artist, tabulatuuri, classes
        )
        if result is not None:
            return result
        return redirect(url_for("song", song_id=song_id))

    return render_template(
        "edit_song.html",
        song=song_to_edit,
        song_classes=song_service.get_classes(song_id),
        classes=song_service.get_all_classes(),
    )

@app.route("/songs/<int:song_id>/delete", methods=["GET", "POST"])
def delete_song(song_id):
    song_details = song_service.get_song(song_id)
    if not song_details:
        return "Kappaletta ei löytynyt", 404
    if not session.get("user_id") or session["user_id"] != song_details["user_id"]:
        return "Ei käyttöoikeutta", 403

    if request.method == "GET":
        return render_template("remove_song.html", song=song_details)

    result = song_service.delete_song(song_id, session["user_id"])
    if result is not None:
        return result
    return redirect(url_for("index"))

@app.route("/songs/create", methods=["POST"])
def create_item():
    login_redirect = require_user_logged_in()
    if login_redirect:
        return login_redirect

    title = request.form.get("title", "").strip()
    artist = request.form.get("artist", "").strip()
    tabulatuuri = request.form.get("tabulatuuri", "").strip()
    if not title or len(title) > 50:
        return "VIRHE: kappaleen nimi on liian pitkä", 400
    if not artist or len(artist) > 50:
        return "VIRHE: artistin nimi on liian pitkä", 400
    if not tabulatuuri or len(tabulatuuri) > 1000:
        return "VIRHE: tabulatuurin pituus on liian pitkä", 400
    user_id = session.get("user_id")

    all_classes = song_service.get_all_classes()

    classes = []
    for entry in request.form.getlist("classes"):
        if entry:
            parts = entry.split(":", 1)
            if len(parts) != 2:
                abort(403)
            title_name, value = parts
            if title_name not in all_classes or value not in all_classes[title_name]:
                abort(403)
            classes.append((title_name, value))
    result = song_service.add_song(title, artist, tabulatuuri, user_id, classes)
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
        return "VIRHE: salasanat eivät ole samat", 400

    try:
        users.create_user(username, password1)
    except sqlite3.IntegrityError:
        return "VIRHE: tunnus on jo varattu", 409

    return "Tunnus luotu"

def require_user_logged_in():
    if not session.get("user_id"):
        return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            return "VIRHE: tunnus ja salasana ovat pakollisia", 400

        user_id = users.check_login(username, password)
        if user_id:
            session["user_id"] = user_id
            session["username"] = username
            return redirect("/")
        else:
            return "VIRHE: väärä tunnus tai salasana", 401

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)