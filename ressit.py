#!/usr/bin/env python

import reddit as reddit
import feedparser
import time, sys
import shelve
import ConfigParser

if len(sys.argv) != 2:
	raise Exception("Usage: %s config_file.ini" % sys.argv[0])

defaults = {
	'submit_delay'     : 60,
	'looping'          : True,   # daemon mode
	'refresh_time'     : 3600,   # delay beeten loops
	'retries'          : 2,      # number of feed download, and submission retries
	'retry_delay'      : 60,     # delay beetwen retries
	'error_delay'      : 600,    # how long wait after retries failed
	'robust'           : True,   # if False, then errors will terminate script
	'db_filename'      : "uploads.shelve.db",
	'dry_run'          : False,
	'verbose'          : False,
	'quiet'            : False
}

config_filename = sys.argv[1]

config = ConfigParser.SafeConfigParser()
config.add_section('general')
for k, v in defaults.iteritems():
	config.set('general', k, str(v))
config.read([config_filename])

reddit_subreddits = []
for section_name in config.sections():
	if section_name != "general" and section_name.startswith("r/"):
		reddit_subreddits.append(section_name)

if len(reddit_subreddits) == 0:
	raise Exception("No subreddits defined in configuration file")

reddit_username  = config.get('general', 'password')
reddit_password  = config.get('general', 'username')

submit_delay     = config.getint('general', 'submit_delay')
looping          = config.getboolean('general', 'looping')
refresh_time     = config.getint('general', 'refresh_time')
db_filename      = config.get('general', 'db_filename')
dry_run          = config.getboolean('general', 'dry_run')
verbose          = config.getboolean('general', 'verbose')
quiet            = config.getboolean('general', 'quiet')

nq = not quiet

if nq: print "Found", len(reddit_subreddits), "subreddit sections."

while True:
	s = shelve.open(db_filename)

	r = None
	k = None

	def login(r, k):
		if r == None:
			if nq: print "Logging in as %s ..." % (reddit_username),
			r = reddit.Reddit(user_agent="ressit robot 0.1")
			r.login(user=reddit_username, password=reddit_password)
			if nq: print "logged,",
		if k == None:
			k = r.get_subreddit(reddit_subreddit)
			if nq: print "got reddit."
		return r, k

	for reddit_subreddit in reddit_subreddits:
		section_name = reddit_subreddit
		if reddit_subreddit.startswith("r/"):
			reddit_subreddit = reddit_subreddit[2:]

		k = None

		if nq: print "Starting update for subreddit r/%s" % (reddit_subreddit)

		feeds = config.items(section_name)
		if len(feeds) == 0:
			if nq: print "WARNING: No feeds for subreddit", reddit_subreddit
			continue
		# TODO: multifeed uploader
		for key, feed_url in feeds:
			if nq: print time.asctime()
			if nq: print "Retriving, parsing, and analyzing feed", feed_url
			ignored, submited = 0, 0
			for f in reversed(feedparser.parse(feed_url).entries):
				key = str(f.link)
				if key in s:
					if verbose:
						print "ignoring %d:" % (ignored+1), f.title, f.link
					ignored += 1
					continue
				r, k = login(r, k) # lazy login
				if nq: print "submiting %d:" % (submited+1), f.title, f.linke
				s[key] = 1
				if not dry_run:
					k.submit(url=f.link, title=f.title)
				else:
					if nq: print "dry run",
				# TODO: automatically 'approve' this submissions
				if nq: print "submited."
				s[key] = int(time.time())
				submited += 1
				time.sleep(submit_delay)

			if nq: print "Feed summary:", ignored, "ignored,", submited, "submited."

	s.close()
	k = None
	r = None
	if looping:
		if nq: print "Sleeping", refresh_time, "second for feed updates."
		time.sleep(refresh_time)
	else:
		break
