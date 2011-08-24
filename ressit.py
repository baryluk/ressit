#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
	'veryverbose'      : False,
	'nonverbose'       : False,
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

reddit_username  = config.get('general', 'username')
reddit_password  = config.get('general', 'password')

submit_delay     = config.getint('general', 'submit_delay')
looping          = config.getboolean('general', 'looping')
refresh_time     = config.getint('general', 'refresh_time')
db_filename      = config.get('general', 'db_filename')
dry_run          = config.getboolean('general', 'dry_run')
verbose          = config.getboolean('general', 'verbose')
veryverbose      = config.getboolean('general', 'veryverbose')
nonverbose       = config.getboolean('general', 'nonverbose')
quiet            = config.getboolean('general', 'quiet')

if (verbose or veryverbose) and nonverbose:
	raise Exception("Cannot use (very)verbose and nonverbose same time")

normalverbose = True
if veryverbose:
	verbose = True

if quiet:
	verbose = False
	veryverbose = False
	normalverbose = False

if submit_delay >= refresh_time or submit_delay < 5 or refresh_time < 60:
	raise Exception("Provide sane submit_delay (>=5), refresh_time (>=60), and submit_delay < refresh_time.")

if verbose: print "Found", len(reddit_subreddits), "subreddit sections."

while True:
	s = shelve.open(db_filename)

	r = None
	k = None

	def login(r, k, sr):
		if r is None:
			if verbose: print "Logging in as %s ..." % (reddit_username),
			r = reddit.Reddit(user_agent="ressit robot 0.1")
			r.login(user=reddit_username, password=reddit_password)
			if verbose: print "logged,",
		if k is None:
			k = r.get_subreddit(sr)
			if verbose: print "got reddit."
		return r, k

	for reddit_subreddit in reddit_subreddits:
		section_name = reddit_subreddit
		if reddit_subreddit.startswith("r/"):
			reddit_subreddit = reddit_subreddit[2:]

		k = None

		if verbose: print "Starting update for subreddit r/%s" % (reddit_subreddit)

		feeds = config.items(section_name)
		if len(feeds) == 0:
			if not quiet: print "WARNING: No feeds for subreddit", reddit_subreddit
			continue
		# TODO: multifeed uploader
		for key, feed_url in feeds:
			if verbose: print time.asctime()
			if verbose: print "Retriving, parsing, and analyzing feed", feed_url
			ignored, submited = 0, 0
			for f in reversed(feedparser.parse(feed_url).entries):
				key = str(f.link)
				if key in s and s[key] != 1:
					if veryverbose:
						print "ignoring %d:" % (ignored+1), f.title, f.link, "(", s[key], ")"
					ignored += 1
					continue
				r, k = login(r, k, reddit_subreddit) # lazy login
				if normalverbose: print "submiting %d:" % (submited+1), f.title, f.link,
				s[key] = 1
				if not dry_run:
					k.submit(url=f.link, title=f.title)
				else:
					if normalverbose: print "dry run",
				# TODO: automatically 'approve' this submissions
				if normalverbose: print "submited."
				if not dry_run:
					s[key] = int(time.time())
				submited += 1
				time.sleep(submit_delay)

			if verbose: print "Feed summary:", ignored, "ignored,", submited, "submited."

	s.close()
	k = None
	r = None
	if looping:
		if verbose: print "Sleeping", refresh_time, "second for feed updates."
		time.sleep(refresh_time)
	else:
		break
