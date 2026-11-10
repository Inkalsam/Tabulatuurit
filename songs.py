import logging
import sqlite3
import db

def add_song(title, artist, tabulatuuri, user_id):
    if not title or not artist or not tabulatuuri:
        return "VIRHE: kaikki kentät ovat pakollisia", 400
    try:
        sql = "INSERT INTO songs (title, artist, tab, user_id) VALUES (?, ?, ?, ?)"
        db.execute(sql, [title, artist, tabulatuuri, user_id])
    except sqlite3.Error:
        logging.getLogger(__name__).exception("Kappaleen luominen epäonnistui")
        return "VIRHE: kappaleen luominen epäonnistui", 500

def get_songs():
    db.ensure_songs_schema()
    sql = "SELECT id, title FROM songs ORDER BY id DESC"
    return db.query(sql)

def get_song(song_id):
    db.ensure_songs_schema()
    sql = '''SELECT songs.title,
                    songs.artist,
                    songs.tab,
                    users.username
                FROM songs
                LEFT JOIN users ON songs.user_id = users.id
                WHERE songs.id = ?'''
    return db.query(sql, [song_id])