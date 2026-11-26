import logging
import sqlite3
import db

def get_all_classes():
    sql = "SELECT title, value FROM classes ORDER BY id"
    result = db.query(sql)

    classes = {}
    for row in result:
        title = row["title"]
        value = row["value"]
        classes.setdefault(title, []).append(value)
    return classes



def add_song(title, artist, tabulatuuri, user_id, classes):
    if not title or not artist or not tabulatuuri:
        return "VIRHE: kaikki kentät ovat pakollisia", 400
    try:
        db.ensure_songs_schema()
        db.ensure_song_classes_schema()
        sql = "INSERT INTO songs (title, artist, tab, user_id) VALUES (?, ?, ?, ?)"
        db.execute(sql, [title, artist, tabulatuuri, user_id])
        song_id = db.last_insert_id()

        sql = "INSERT INTO song_classes (song_id, title, value) VALUES (?, ?, ?)"
        for title, value in classes:
            db.execute(sql, [song_id, title, value])
    except sqlite3.Error:
        logging.getLogger(__name__).exception("Kappaleen luominen epäonnistui")
        return "VIRHE: kappaleen luominen epäonnistui", 500


def add_comment(song_id, user_id, content):
    db.ensure_comments_schema()
    sql = "INSERT INTO comments (song_id, user_id, content) VALUES (?, ?, ?)"
    db.execute(sql, [song_id, user_id, content])

def get_comments(song_id):
    db.ensure_comments_schema()
    sql = """SELECT comments.content, users.id AS user_id, users.username
             FROM comments
             JOIN users ON comments.user_id = users.id
             WHERE comments.song_id = ?
             ORDER BY comments.id DESC"""
    result = db.query(sql, [song_id])
    return result

def get_images(song_id):
    db.ensure_images_schema()
    sql = "SELECT id FROM images WHERE song_id = ?"
    return db.query(sql, [song_id])

def add_image(song_id, image):
    db.ensure_images_schema()
    sql = "INSERT INTO images (song_id, image) VALUES (?, ?)"
    db.execute(sql, [song_id, image])

def get_image(image_id):
    db.ensure_images_schema()
    sql = "SELECT image FROM images WHERE id = ?"
    result = db.query(sql, [image_id])
    return result[0]["image"] if result else None

def remove_image(song_id, image_id):
    sql = "DELETE FROM images WHERE id = ? AND song_id = ?"
    db.execute(sql, [image_id, song_id])


def get_review_data(song_id, user_id):
    db.ensure_reviews_schema()
    summary = db.query(
        "SELECT COUNT(*) AS count, AVG(rating) AS average "
        "FROM reviews WHERE song_id = ?",
        [song_id],
    )[0]
    user_review = db.query(
        "SELECT rating FROM reviews WHERE song_id = ? AND user_id = ?",
        [song_id, user_id],
    )
    return summary["count"], summary["average"], (
        user_review[0]["rating"] if user_review else None
    )

def save_review(song_id, user_id, rating):
    db.ensure_reviews_schema()
    db.execute(
        """INSERT INTO reviews (song_id, user_id, rating)
           VALUES (?, ?, ?)
           ON CONFLICT (song_id, user_id)
           DO UPDATE SET rating = excluded.rating""",
        [song_id, user_id, rating],
    )


def get_songs():
    db.ensure_songs_schema()
    db.ensure_comments_schema()
    db.ensure_reviews_schema()
    sql = """SELECT songs.id,
                    songs.title,
                    users.id AS user_id,
                    users.username,
                    (SELECT COUNT(*) FROM comments
                     WHERE comments.song_id = songs.id) AS comments_count,
                    (SELECT COUNT(*) FROM reviews
                     WHERE reviews.song_id = songs.id) AS review_count,
                    (SELECT AVG(reviews.rating) FROM reviews
                     WHERE reviews.song_id = songs.id) AS review_average
             FROM songs
             LEFT JOIN users ON songs.user_id = users.id
             ORDER BY songs.id DESC"""
    return db.query(sql)

def search_songs(query):
    db.ensure_songs_schema()
    search_term = f"%{query}%"
    sql = """SELECT id, title, artist
             FROM songs
             WHERE title LIKE ? OR artist LIKE ?
             ORDER BY id DESC"""
    result = db.query(sql, [search_term, search_term])
    return result if result else None

def get_song(song_id):
    db.ensure_songs_schema()
    sql = """SELECT songs.id,
                    songs.title,
                    songs.artist,
                    songs.tab,
                    users.id AS user_id,
                    users.username
             FROM songs
             LEFT JOIN users ON songs.user_id = users.id
             WHERE songs.id = ?"""
    result = db.query(sql, [song_id])
    return result[0] if result else None

def get_classes(song_id):
    db.ensure_song_classes_schema()
    result = db.query(
        "SELECT title, value FROM song_classes WHERE song_id = ?",
        [song_id],
    )
    return {row["title"]: row["value"] for row in result}

def update_song(song_id, user_id, title, artist, tabulatuuri, classes):
    if not title or not artist or not tabulatuuri:
        return "VIRHE: kaikki kentät ovat pakollisia", 400
    try:
        db.ensure_song_classes_schema()
        sql = "UPDATE songs SET title = ?, artist = ?, tab = ? WHERE id = ? AND user_id = ?"
        db.execute(sql, [title, artist, tabulatuuri, song_id, user_id])
        db.execute("DELETE FROM song_classes WHERE song_id = ?", [song_id])
        sql = "INSERT INTO song_classes (song_id, title, value) VALUES (?, ?, ?)"
        for title, value in classes:
            db.execute(sql, [song_id, title, value])
    except sqlite3.Error:
        logging.getLogger(__name__).exception("Kappaleen muokkaaminen epäonnistui")
        return "VIRHE: kappaleen muokkaaminen epäonnistui", 500

def delete_song(song_id, user_id):
    try:
        db.ensure_reviews_schema()
        db.execute(
            """DELETE FROM reviews
               WHERE song_id IN (
                   SELECT id FROM songs WHERE id = ? AND user_id = ?
               )""",
            [song_id, user_id],
        )
        db.ensure_song_classes_schema()
        db.execute(
            """DELETE FROM song_classes
               WHERE song_id IN (
                   SELECT id FROM songs WHERE id = ? AND user_id = ?
               )""",
            [song_id, user_id],
        )
        sql = "DELETE FROM songs WHERE id = ? AND user_id = ?"
        db.execute(sql, [song_id, user_id])
    except sqlite3.Error:
        logging.getLogger(__name__).exception("Kappaleen poistaminen epäonnistui")
        return "VIRHE: kappaleen poistaminen epäonnistui", 500