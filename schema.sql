CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT
);

CREATE TABLE songs (
    id INTEGER PRIMARY KEY,
    title TEXT,
    artist TEXT,
    tab TEXT,
    user_id INTEGER REFERENCES users
);

CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    song_id INTEGER REFERENCES songs,
    user_id INTEGER REFERENCES users,
    content TEXT
);

CREATE TABLE classes (
    id INTEGER PRIMARY KEY,
    title TEXT,
    value TEXT
);

CREATE TABLE song_classes (
    id INTEGER PRIMARY KEY,
    song_id INTEGER REFERENCES songs,
    title TEXT,
    value TEXT
);