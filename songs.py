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

def get_songs():
    db.ensure_songs_schema()
    sql = "SELECT id, title FROM songs ORDER BY id DESC"
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
    sql = '''SELECT songs.id,
                    songs.title,
                    songs.artist,
                    songs.tab,
                    users.id user_id,
                    users.username
                FROM songs
                LEFT JOIN users ON songs.user_id = users.id
                WHERE songs.id = ?'''
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