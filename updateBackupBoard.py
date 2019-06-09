#!/bin/python2

import sys, os
sys.path.insert(0, os.path.dirname(__file__)+"/src/" )

from wekanapi import WekanApi
from pprint import pprint as pp
from glob import glob
import os

api = WekanApi("http://atomovfx.hradec.com/wekan", eval(''.join(open("userpasswd.txt").readlines())), )


jobs=[]
d={}
for b  in [ x for x in api.get_user_boards() if 'backup' in x.title.lower() ]:
	d[b.title] = {}
	d[b.title][".class"] = b
	for list in b.get_cardslists():
		d[b.title][list.title] = {}
		d[b.title][list.title][".class"] = list
		for card in list.get_cards():
			d[b.title][list.title][card.title]=card
			jobs.append(card.title)




pp(d)

paths=[]
j=''.join(jobs)
for p in glob("/atomo/jobs/*"):
	jobNumber = int(os.path.basename(p).split('.')[0])
	if jobNumber < 9000 and jobNumber > 0:
		W = os.path.basename(p) in j
		if not W:
			paths += [p]
			print W,p

paths.sort()
pp(paths)

import wekanapi
print wekanapi.__file__
