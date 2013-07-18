#!/usr/bin/python3
import praw
import sys, os
import logging
import datetime

if __name__ == "__main__":
    os.chdir(os.path.dirname(sys.argv[0]))

# set up logging
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)
fh = logging.FileHandler('iot.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter(fmt="%(asctime)s %(name)s [%(levelname)s]: %(message)s"))
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
rootLogger.addHandler(fh)
rootLogger.addHandler(ch)
logger = logging.getLogger(__name__)

import iot_db as db

def get_threads(subreddit_name):
    sr = reddit.get_subreddit(subreddit_name)
    threads = sr.get_hot(limit=50)
    c = db.db.cursor()
    for thread in threads:
        if thread.is_self:
            continue
        c.execute("SELECT * FROM threads WHERE permalink=?", (thread.permalink,))
        row = c.fetchone()
        if row == None:
            logger.info("Found new thread %s in %s", thread.id, sr.display_name)
            c.execute("SELECT id FROM articles WHERE url=?", (thread.url,))
            row = c.fetchone()
            if row == None:
                c.execute("INSERT INTO articles (url) VALUES (?)", (thread.url,))
                db.db.commit()
                article_id = c.lastrowid
            else:
                article_id = row[0]
            c.execute("INSERT INTO threads (article_id, poster, subreddit, permalink, karma, comment_count, posted_at) VALUES (?,?,?,?,?,?,?)",
                    [article_id, thread.author.name, sr.display_name, thread.permalink, thread.score, thread.num_comments,
                        datetime.datetime.utcfromtimestamp(thread.created_utc)])
            db.db.commit()


##MAIN PROGRAM
db.init_db()

reddit = None
subreddits = ["anarchism","conservative","inthenews","liberal","libertarian","news","politics","socialism","technology","worldnews","worldpolitics","test"]

if __name__ == "__main__":
    if len(sys.argv) == 1:
        logger.warning("No login given, running in test mode.")
    elif len(sys.argv) != 3:
        logger.critical("Usage: %s username password", os.path.basename(sys.argv[0]))
        exit(1)
    reddit = praw.Reddit(user_agent="InOtherThreads v0.1 github.com/DeltaWhy/in-other-threads")
    if len(sys.argv) == 3:
        logger.debug("Logging in as %s", sys.argv[1])
        reddit.login(sys.argv[1], sys.argv[2])

    for subreddit in subreddits:
        get_threads(subreddit)
