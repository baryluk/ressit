#!/usr/bin/env python

import reddit as reddit
import feedparser
import time
import shelve

# Configuration section.
feed_url         = "http://example.com/rss.xml"
reddit_user      = "login"
reddit_password  = "secret"
reddit_subreddit = "name-of-subreddit"

raise Exception("Please configure ressit first") # REMOVE, after configuring above ones.

# Please do not change, until You know what are you doing.
refresh_time     = 3600
submit_delay     = 60

while True:
	s = shelve.open("uploads.shelve.db")

	logged = False
	r = None
	k = None
	def login():
		if logged:
			return
		logged = True
		print "Logging in...",
		r = reddit.Reddit(user_agent="ressit robot 0.1")
		r.login(user=reddit_user, password=reddit_password)
		print "logged,",
		k = r.get_subreddit(reddit_subreddit)
		print "got reddit."

	# TODO: multifeed uploader

	print time.asctime()
	print "Retriving, parsing, and analyzing feed", feed_url
	ignored, submited = 0, 0
	for f in reversed(feedparser.parse(feed_url).entries):
		key = str(f.link)
		if key in s:
			ignored += 1
			continue
		login() # lazy login
		print "submiting %d:" % (submited+1),
		print f.title, f.link,
		s[key] = 1
		k.submit(url=f.link, title=f.title)
		# TODO: automatically 'approve' this submissions
		print "submited."
		s[key] = 2 # TODO: date of upload
		submited += 1
		time.sleep(submit_delay)

	print "Feed summary:", ignored, "ignored,", submited, "submited."
	s.close()
	k = None
	r = None
	print "Sleeping", refresh_time, "second for feed updates."
	time.sleep(refresh_time)
