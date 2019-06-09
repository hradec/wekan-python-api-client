#!/bin/python2

import sys, os
sys.path.insert(0, os.path.dirname(__file__)+"/src/" )

from wekanapi import WekanApi
from pprint import pprint as pp
from glob import glob
import os

api = WekanApi("http://192.168.0.16:8080/wekan", eval(''.join(open("userpasswd.txt").readlines())), )


jobs=[]
d = {}
cards = {}
for b  in api.get_user_boards('BACKUP'):
	print b.get_custom_fields()
	d[b.title] = {}
	d[b.title][".class"] = b
	for list in b.get_cardslists():
		d[b.title][list.title] = {}
		d[b.title][list.title][".class"] = list
		for card in list.get_cards():
			d[b.title][list.title][card.title]=card
			jobs.append(card.title)
			cards[ card.title.split('\n')[0].replace("*","") ] = card


toRemove=[]
paths=[]
j=''.join(jobs)
for p in glob("/atomo/jobs/*"):
	p = os.path.abspath(p)
	if os.path.islink(p):
		p = os.readlink(p)
	p = p.rstrip('/')
	jobNumber = int(os.path.basename(p).split('.')[0])
	if not os.path.exists(p):
		toRemove.append(p)
	if jobNumber < 9000 and jobNumber > 0:
		print p
		size=''.join(os.popen("du -shc %s 2>/dev/null | grep total" % p).readlines()).split()[0].strip()
		disco=os.path.dirname(p)
		mover=""
		posicao=""
		title="**%s**" % os.path.basename(p)
		title+="\n>disco: %s" % disco
		title+="\nmover: %s" % mover
		title+="\nposicao: %s" % posicao
		title+="\ntamanho: %s" % size
		# if a card exists
		hasCard = os.path.basename(p) in j
		if hasCard:
			try:
				cards[ os.path.basename(p) ].modify( title=title )
			except:
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
