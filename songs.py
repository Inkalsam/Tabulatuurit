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