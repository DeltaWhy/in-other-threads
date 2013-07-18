#!/usr/bin/python3
import praw
import sys, os
import logging
import datetime
import argparse

args = None
if __name__ == "__main__":
    os.chdir(os.path.dirname(sys.argv[0]))
    parser = argparse.ArgumentParser(description='A Reddit bot to encourage better political discussions.',
                epilog='This script exits after finishing its work, so it should be run in a cron job or similar.')
    parser.add_argument('username', nargs='?', help='Username for the bot. If not provided, will not attempt to post.')
    parser.add_argument('password', nargs='?', help='Password for the bot. If not provided, will prompt.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--debug', help="Show debug messages.", action='store_true')
    group.add_argument('-q','--quiet', dest='quiet', help="Suppress info messages in console.", action='store_true')

    parser.add_argument('--no-fetch', help="Don't check for new threads, only use existing data.", action='store_true')
    args = parser.parse_args()

# set up logging
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)
fh = logging.FileHandler('iot.log')
if args and args.debug:
    fh.setLevel(logging.DEBUG)
else:
    fh.setLevel(logging.INFO)
fh.setFormatter(logging.Formatter(fmt="%(asctime)s %(name)s [%(levelname)s]: %(message)s"))
ch = logging.StreamHandler()
if args and args.debug:
    ch.setLevel(logging.DEBUG)
elif args and args.quiet:
    ch.setLevel(logging.WARNING)
else:
    ch.setLevel(logging.INFO)
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
    reddit = praw.Reddit(user_agent="InOtherThreads v0.1 github.com/DeltaWhy/in-other-threads")
    if args.username == None:
        logger.warning("No login given, running in test mode.")
    elif args.password == None:
        logger.debug("Logging in as %s", args.username)
        reddit.login(args.username)
    else:
        logger.debug("Logging in as %s", args.username)
        reddit.login(args.username, args.password)

    if not(args.no_fetch):
        for subreddit in subreddits:
            get_threads(subreddit)

def test_thread_picking():
    articles = db.get_article_ids()
    sources = {}
    for article in articles:
        threads = db.get_source_thread_ids(article)
        if len(threads) > 0:
            sources[article] = threads
    targets = {}
    for article in articles:
        if article in sources:
            threads = db.get_target_thread_ids(article)
            if len(threads) > 0:
                targets[article] = threads
    print("Sources:\n%s\n\nTargets:\n%s\n" % (sources, targets))
