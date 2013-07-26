in-other-threads
================

A Reddit bot to encourage better political discussions

~~~
usage: iot.py [-h] (--test | --live) [--debug | -q] [--no-fetch] [--no-post]
              [username] [password]

A Reddit bot to encourage better political discussions.

positional arguments:
  username     Username for the bot. If not provided, will not attempt to
               post.
  password     Password for the bot. If not provided, will prompt.

optional arguments:
  -h, --help   show this help message and exit
  --test       Only post to /r/test.
  --live       Post to any subreddit in the list.
  --debug      Show debug messages.
  -q, --quiet  Suppress info messages in console.
  --no-fetch   Don't check for new threads, only use existing data.
  --no-post    Don't make any posts.

This script exits after finishing its work, so it should be run in a cron job
or similar.
~~~

No setup required - the script will create its database automatically if it's not found. For development you can run it 
in several "safe modes" - if you don't give it a username and password, or if you specify --no-post it will not post any
comments. If you specify --test it will run normally but will only post in /r/test. You should only use --live on the
production server unless you have some way of mirroring the database - otherwise things will get double-posted.

In production, you'll need to set up a cron job to run the script at regular intervals. Mine looks like this:
~~~
0 * * * * /home/redditbot/in-other-threads/iot.py --debug --live USERNAME PASSWORD
15,20,45 * * * * /home/redditbot/in-other-threads/iot.py --debug --live --no-fetch USERNAME PASSWORD
~~~
