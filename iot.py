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
    parser.add_argument('--no-post', help="Don't make any posts.", action='store_true')
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
        row = db.select_one("SELECT id FROM threads WHERE permalink=?", thread.permalink)
        if row == None:
            logger.info("Found new thread %s in %s", thread.id, sr.display_name)
            row = db.select_one("SELECT id FROM articles WHERE url=?", thread.url)
            if row == None:
                article_id = db.insert('articles', url=thread.url)
            else:
                article_id = row['id']
            db.insert('threads', {'article_id': article_id, 'poster': thread.author.name, 'subreddit': sr.display_name,
                'permalink': thread.permalink, 'karma': thread.score, 'comment_count': thread.num_comments,
                'posted_at': datetime.datetime.utcfromtimestamp(thread.created_utc)})

def get_best_comment(thread_id):
    c = db.db.cursor()
    thread_row = db.select_one("SELECT * FROM threads WHERE id=?", thread_id)
    if thread_row == None:
        raise KeyError("Thread %d not found in database." % thread_id)
    thread = reddit.get_submission(url=thread_row['permalink'])

    # comments are sorted by best by default
    # loop until we find a real comment
    for comment in thread.comments:
        if not(comment.author): #[deleted]
            continue
        if type(comment) == praw.objects.MoreComments:
            return
        if db.select_one("SELECT id FROM comments WHERE permalink=?", comment.permalink):
            return #don't double-create
        logger.info("Found new comment %s on thread %s in %s", comment.id, thread.id, thread.subreddit.display_name)
        db.insert('comments', {'thread_id': thread_row['id'], 'poster': comment.author.name, 'body': comment.body,
            'permalink': comment.permalink, 'karma': comment.score, 'posted_at': datetime.datetime.utcfromtimestamp(comment.created_utc)})
        return

def quote_comment(comment):
    return "\n".join(["> " + line for line in comment.split("\n")])

def do_post(source=None, target=None):
    if not(source) or not(target):
        raise ArgumentError("Must provide both source and target thread ids")
    logger.info("Cross-post from %d to %d", source, target)
    c = db.db.cursor()

    thread_row = db.select_one("SELECT * FROM threads WHERE id=?", source)
    if thread_row == None:
        raise KeyError("Thread %d not found in database." % source)

    target_row = db.select_one("SELECT * FROM threads WHERE id=?", target)
    if target_row == None:
        raise KeyError("Thread %d not found in database." % source)

    comment_row = db.select_one("SELECT * FROM comments WHERE thread_id=? ORDER BY id DESC", source)
    if comment_row == None:
        logger.info("No comment found for %d", source)
        return

    post = """This article is also being discussed in [a thread in /r/%(subreddit)s](%(permalink)s).

Selected comment from that thread:
%(quoted_comment)s

^(by /u/%(poster)s ()[^link](%(comment_permalink)s)^)

***
[^(about this bot)](http://google.com)
""" % {'subreddit': thread_row['subreddit'], 'permalink': thread_row['permalink'], 'quoted_comment': quote_comment(comment_row['body']),
        'poster': comment_row['poster'], 'comment_permalink': comment_row['permalink']}

    if not(args) or args.username == None:
        logger.info("Not posting because not logged in.")
        return
    if args and args.no_post:
        logger.info("Not posting because --no-post was given.")
        return
    if target_row['subreddit'] != 'test':
        logger.info("Not posting because not in /r/test.")
        return

    logger.debug(post)
    target = reddit.get_submission(url=target_row['permalink'])
    comment = target.add_comment(post)
    db.insert('comments', {'thread_id': target, 'poster': comment.author.name, 'body': comment.body,
        'permalink': comment.permalink, 'karma': comment.score, 'posted_at': datetime.datetime.utcfromtimestamp(comment.created_utc)})
    c.execute("UPDATE threads SET handled=1 WHERE id=?", (target,))
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

    articles = db.get_article_ids()
    sources = {}
    for article in articles:
        threads = db.get_source_thread_ids(article)
        if len(threads) > 0:
            sources[article] = threads

    if not(args.no_fetch):
        # flatten the sources
        for thread in set([id for sublist in sources.values() for id in sublist]):
            get_best_comment(thread)

    targets = {}
    for article in articles:
        if article in sources:
            threads = db.get_target_thread_ids(article)
            if len(threads) > 0:
                targets[article] = threads

    for article,target_threads in targets.items():
        for target_thread in target_threads:
            source_threads = [x for x in sources[article]] #no list.copy in Python 3.1!!!
            if target_thread in source_threads:
                source_threads.remove(target_thread)
            for source_thread in source_threads:
                do_post(source=source_thread, target=target_thread)
