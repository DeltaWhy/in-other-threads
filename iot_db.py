import sqlite3, logging, sys, os
logger = logging.getLogger(__name__)

db = None

def get_setting(key):
    if db == None:
        raise RuntimeError('DB not initialized')
    c = db.cursor()
    c.execute("SELECT value FROM meta WHERE key=?", (key,))
    row = c.fetchone()
    if row == None:
        return None
    else:
        return row[0]

def set_setting(key, value):
    if db == None:
        raise RuntimeError('DB not initialized')
    c = db.cursor()
    c.execute("INSERT INTO meta VALUES (?,?)", (key, value,))
    db.commit()

def init_db():
    global db
    if __name__ == "__main__":
        os.chdir(os.path.dirname(sys.argv[0]))
    db = sqlite3.connect('iot.db')
    c = db.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS meta (key TEXT UNIQUE, value TEXT)""")

    # check DB version to see if we need to update it
    version = get_setting("schema_version")
    if version != None:
        version = int(version)

    if version == None:
        logger.info("Creating database...")
        set_setting("schema_version",1)
        c.executescript("""
                PRAGMA foreign_keys = ON;
                CREATE TABLE articles (
                    id INTEGER PRIMARY KEY,
                    url TEXT UNIQUE);
                CREATE TABLE threads (
                    id INTEGER PRIMARY KEY,
                    article_id INTEGER,
                    poster TEXT,
                    subreddit TEXT,
                    permalink TEXT,
                    karma INTEGER,
                    comment_count INTEGER,
                    posted_at TEXT,
                    FOREIGN KEY(article_id) REFERENCES articles(id));
                CREATE TABLE comments (
                    id INTEGER PRIMARY KEY,
                    thread_id INTEGER,
                    poster TEXT,
                    body TEXT,
                    permalink TEXT,
                    karma INTEGER,
                    comment_count INTEGER,
                    posted_at TEXT,
                    FOREIGN KEY(thread_id) REFERENCES threads(id));
                CREATE INDEX article_urls ON articles(url);
                CREATE INDEX thread_permalinks ON threads(permalink);
                CREATE INDEX comment_permalinks ON comments(permalink);
                """)
    elif version > 1:
        logger.critical("Unknown database version %d.", version)
        exit(1)
