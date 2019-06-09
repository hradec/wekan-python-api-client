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
			cards[ card.title.split('\n')[0] ] = card


paths=[]
j=''.join(jobs)
for p in glob("/atomo/jobs/*"):
	p = os.path.abspath(p)
	if os.path.islink(p):
		p = os.readlink(p)
	p = p.rstrip('/')
	jobNumber = int(os.path.basename(p).split('.')[0])
	if jobNumber < 9000 and jobNumber > 0:
		hasCard = os.path.basename(p) in j
		# if a card exists
		if hasCard:
			print p
			size=''.join(os.popen("du -shc %s | grep total" % p).readlines()).split()[0].strip()
			disco=os.path.dirname(p)
			mover=""
			posicao=""
			title=os.path.basename(p)
			title+="\ndisco: %s" % disco
			title+="\nmover: %s" % mover
			title+="\nposicao: %s" % posicao
			title+="\ntamanho: %s" % size
			cards[ os.path.basename(p) ].modify( title=title )

		# or else create a new card
		# else:
		# 	for b  in api.get_user_boards('BACKUP'):
		# 		for l in b.get_cardslists('JOBS'):
		# 			l.add_card(os.path.basename(p))
