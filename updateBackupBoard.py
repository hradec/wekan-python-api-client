#!/bin/python2

import sys, os, time
sys.path.insert(0, os.path.dirname(__file__)+"/src/" )

from wekanapi import WekanApi
from pprint import pprint as pp
from glob import glob
import os

lock = "/tmp/.%s.lock" % os.path.basename(__file__)
if os.path.exists(lock) :
	sys.exit(0)
else:
	open( lock, "w" ).close()

api = WekanApi("http://192.168.0.16:8080/wekan", eval(''.join(open("userpasswd.txt").readlines())), )


jobs=[]
d = {}
cards = {}
# grab all cards form the weekan BACKUP board and store in cards dictionary
for b  in api.get_user_boards('BACKUP'):
	d[b.title] = {}
	d[b.title][".class"] = b
	for list in b.get_cardslists():
		d[b.title][list.title] = {}
		d[b.title][list.title][".class"] = list
		for card in list.get_cards():
			d[b.title][list.title][card.title]=card
			jobs.append(card.title)
			cards[ card.title.split('\n')[0].replace("*","") ] = card

# create a big string with all titles so we can fast and easyly find
# if a job already has a card!
j=''.join(jobs)
toRemove=[]
paths=[]

# check if we're backup to LTO
ltoBackup = ''.join(os.popen("ssh root@nexenta.local 'pgrep -fa rsync.*LTO' | tail -1").readlines()).strip().split()
if len(ltoBackup) > 3:
	ltoBackup = ltoBackup[3].strip().rstrip('/')
print ltoBackup

# loop over jobs and update weekan cards with size and other info
for p in glob("/atomo/jobs/*")+glob("/.LIZARDFS/atomo/jobs/*")+glob("/.MOOSEFS/atomo/jobs/*"):
	p = os.path.abspath(p)
	if os.path.islink(p):
		p = os.readlink(p)
	p = p.rstrip('/')
	jobNumber = int(os.path.basename(p).split('.')[0])
	if not os.path.exists(p):
		toRemove.append(p)

	# only consider directories
	if os.path.isdir(p):
		if jobNumber < 9000 and jobNumber > 0: #and jobNumber==665:
			print p
			# calculate size of jobs just once a day!
			l='/tmp/%s.disk_usage.log' % os.path.basename(p)
			if not os.path.exists(l) or ( ( time.time() - int(os.stat(l)[-1]) ) /60 /60 ) > 24:
				size=''.join(os.popen( '''
					du -shc %s 2>/dev/null | grep total > %s ; \
					cat %s
					''' % ( p, l, l )
				).readlines()).split()[0].strip()
			else:
				size= ''.join(open( l ).readlines()).split()[0].strip()

			disco=os.path.dirname(p)
			mover=""
			posicao=""

			# now update the card which is being backed up
			print os.path.basename(p) in ltoBackup, os.path.basename(p), ltoBackup
			if os.path.basename(p) in ltoBackup:
				posicao="Movendo para o LTO..."

			# create title
			title="**%s**" % os.path.basename(p)
			title+="\n>disco: %s" % disco
			title+="\nmover: %s" % mover
			title+="\nposicao: **%s**" % posicao
			title+="\ntamanho: %s" % size
			print title

			# if a card exists
			hasCard = os.path.basename(p) in j
			if hasCard:
				# if '.LIZARDFS' in disco:

				print cards[ os.path.basename(p) ].data['title']
				print cards[ os.path.basename(p) ].cardslist.data
				# print cards[ os.path.basename(p) ].setList('JOBS')

				if not cards[ os.path.basename(p) ].modify( title=title ):
					print "Error updating card for %s!!" % p

			# or else create a new card
			else:
			 	for b  in api.get_user_boards('BACKUP'):
			 		for l in b.get_cardslists('JOBS'):
			 			l.add_card(title)





print "\nThe following jobs don't exist:"
for n in toRemove:
	print '\t%s' % n

print

if os.path.exists(lock) :
	os.remove( lock )
