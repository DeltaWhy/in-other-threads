import sqlite3, logging, sys, os
logger = logging.getLogger(__name__)

db = None

def get_setting(key):
    row = select_one("SELECT value FROM meta WHERE key=?", key)
    if row == None:
        return None
    else:
        return row['value']

def set_setting(key, value):
    if db == None:
        raise RuntimeError('DB not initialized')
    c = db.cursor()
    c.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, value,))
    db.commit()

def select(sql, *params):
    if db == None:
        raise RuntimeError('DB not initialized')
    c = db.cursor()
    c.execute(sql, params)
    columns = [x[0] for x in c.description]
    objs = []
    for row in c:
        obj = {}
        for i in range(len(columns)):
            obj[columns[i]] = row[i]
        objs.append(obj)
    return objs

def select_one(sql, *params):
    if db == None:
        raise RuntimeError('DB not initialized')
    c = db.cursor()
    c.execute(sql, params)
    columns = [x[0] for x in c.description]
    row = c.fetchone()
    if row == None:
        return None
    else:
        obj = {}
        for i in range(len(columns)):
            obj[columns[i]] = row[i]
        return obj

def insert(table_name, obj=None, **kwargs):
    if obj == None and len(kwargs) == 0:
        raise ArgumentError("Nothing given to insert")
    elif obj != None and len(kwargs) != 0:
        raise ArgumentError("Can't give both dict and keyword arguments")
    elif obj == None and len(kwargs) > 0:
        obj = kwargs
    if db == None:
        raise RuntimeError('DB not initialized')
    c = db.cursor()
    sql = "INSERT INTO %s (%s) VALUES (%s)" % (table_name, ', '.join(obj.keys()), ','.join(['?' for x in obj.values()]))
    c.execute(sql, list(obj.values()))
    db.commit()
    return c.lastrowid

def init_db():
    """
    Initialize the database connection. Creates the database if it does
    not exist and updates the schema if it is an older version.
    """
    global db
    db = sqlite3.connect('iot.db')
    c = db.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT UNIQUE, value TEXT)")

    # check DB version to see if we need to update it
    version = get_setting("schema_version")
    if version != None:
        version = int(version)


    while version != 3:
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
            version = int(get_setting('schema_version'))
        elif version == 1:
            logger.info("Updating database to version 2...")
            set_setting("schema_version",2)
            c.executescript("""
                    ALTER TABLE threads ADD COLUMN handled INTEGER NOT NULL DEFAULT 0;
                    """)
            version = int(get_setting('schema_version'))
        elif version == 2:
            logger.info("Updating database to version 3...")
            set_setting("schema_version",3)
            c.executescript("""
                    CREATE TABLE xposts (
                        source_id INTEGER NOT NULL,
                        target_id INTEGER NOT NULL,
                        status TEXT,
                        comment_id INTEGER,
                        FOREIGN KEY(source_id) REFERENCES threads(id),
                        FOREIGN KEY(target_id) REFERENCES threads(id));
                    CREATE INDEX xpost_sources ON xposts(source_id);
                    CREATE INDEX xpost_targets ON xposts(target_id);
                    """)
            version = int(get_setting('schema_version'))
        elif version > 3:
            logger.critical("Unknown database version %d.", version)
            exit(1)

def get_article_ids():
    """
    Returns a list of article ids which have more than one thread.
    """
    if db == None:
        raise RuntimeError('DB not initialized')
    c = db.cursor()
    c.execute("""SELECT article_id FROM
                    (SELECT article_id, COUNT(id) as thread_count FROM threads GROUP BY article_id)
                    WHERE thread_count > 1""")
    ids = []
    for row in c:
        ids.append(row[0])
    return ids

def get_source_thread_ids(article_id):
    """
    Returns a list of thread ids which we can reference.
    """
    if db == None:
        raise RuntimeError('DB not initialized')
    c = db.cursor()

    # don't use very new or very small threads
    # because the best comment probably hasn't been posted yet
    c.execute("""SELECT id FROM threads WHERE article_id=?
                    AND posted_at < DATETIME('NOW', '-4 hours')
                    AND comment_count >= 10
                    AND subreddit!='test'""", (article_id,))
    ids = []
    for row in c:
        ids.append(row[0])
    return ids

def get_target_thread_ids(article_id):
    """
    Returns a list of thread ids which we can post to.
    """
    if db == None:
        raise RuntimeError('DB not initialized')
    c = db.cursor()

    # don't bump old threads
    # we don't want to be too disruptive so for now also avoid new/small threads
    c.execute("""SELECT id FROM threads WHERE article_id=?
                    AND (
                            (posted_at < DATETIME('NOW', '-4 hours')
                            AND posted_at > DATETIME('NOW', '-30 hours')
                            AND comment_count >= 10)
                        OR subreddit='test')""", (article_id,))
    ids = []
    for row in c:
        ids.append(row[0])
    return ids

