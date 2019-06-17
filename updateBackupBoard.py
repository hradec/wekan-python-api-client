#!/bin/python2

import sys, os, time
sys.path.insert(0, os.path.dirname(__file__)+"/src/" )

from wekanapi import WekanApi
from pprint import pprint as pp
from glob import glob
import os

processes = os.popen("ps -AHfc | grep update | grep -v grep").readlines()
print processes
if len( processes ) > 3:
	exit(0)

api = WekanApi("http://192.168.0.16:8080/wekan", eval(''.join(open("userpasswd.txt").readlines())), )

class _cards(dict):
	pass

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
ltoFreeSpace = ""
ltoBackup = ''.join(os.popen("ssh root@nexenta.local 'pgrep -fa rsync.*LTO' | tail -1").readlines()).strip().split()
if len(ltoBackup) > 3:
	ltoBackup = ltoBackup[3].strip().rstrip('/')
	ltoFreeSpace = ''.join(os.popen("ssh root@nexenta.local 'df -h | grep LTO'").readlines()).strip().split()[-3]
	print ltoFreeSpace
print ltoBackup

# loop over jobs and update weekan cards with size and other info
folders  = glob("/atomo/jobs/*")
folders += glob("/.LIZARDFS/atomo/jobs/*")
folders += glob("/.MOOSEFS/atomo/jobs/*")
folders += glob("/smb/Backups-3ds/atomo/jobs/*")
folders.sort()
repetidos={}
for p in folders:
	p = os.path.abspath(p).replace('//','/').rstrip('/')
	if os.path.islink(p):
		p = os.readlink(p)
	p = p.replace('//','/').rstrip('/')

	if not os.path.exists(p):
		toRemove.append(p)
	elif os.path.isdir(p) and not os.path.islink(p):
		if os.path.basename(p) not in repetidos:
			repetidos[ os.path.basename(p) ] = [p]
		else:
			if p not in repetidos[ os.path.basename(p) ]:
				repetidos[ os.path.basename(p) ] += [p]
			else:
				continue

for job in repetidos.keys():
	print job
	repetidos[job].sort()
	p = [ x for x in repetidos[job] if 'atomo' in x ]
	if p:
		p = p[0]
	else:
		p = repetidos[job][0]

	jobNumber = int(os.path.basename(p).split('.')[0])

	# only consider directories
	if jobNumber < 9000 and jobNumber > 0: # and jobNumber==581:

		# calculate size of jobs just once a day!
		print p
		l='/tmp/%s.disk_usage.log' % p.strip('/').replace('/','_')
		if not os.path.exists(l) or ( ( time.time() - int(os.stat(l)[-1]) ) /60 /60 ) > 24  or  os.stat( l )[6] == 0:
			os.popen( 'du -shc %s 2>/dev/null | grep total > %s ' % ( p, l ) )

		size= ''.join(open( l ).readlines()).split()[0].strip()
		disco=os.path.dirname(p)
		mover=""
		posicao=""
		extra=""

		hasCard = os.path.basename(p) in j
		if hasCard:
			if cards[ os.path.basename(p) ].cardslist.title == "JOBS":
				posicao = "**em producao**"
			elif "LIZARD" in cards[ os.path.basename(p) ].cardslist.title:
				posicao = "**esperando...**"
				extra='<img src="https://media1.tenor.com/images/b5c77a0f1690bcfdce0df8c6525ea95e/tenor.gif?itemid=7903387" width=200>'
				if [ x for x in repetidos[job] if 'LIZARD' in x ]:
					if len( repetidos[job] )>1:
						posicao = "**movendo pro LizardFS**"
						extra='<img src="https://media.giphy.com/media/sRFEa8lbeC7zbcIZZR/giphy.gif" width=200>'
					else:
						posicao = "**terminado de mover**"
						extra=""

			elif "LTO" in cards[ os.path.basename(p) ].cardslist.title:
				posicao = "**esperando...**"
				# extra='<img src="https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/e8b59154-c192-4417-888b-f9731b36ae89/daxnkcx-3db57900-9d17-4f68-8323-4bfd7031fc3b.gif?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7InBhdGgiOiJcL2ZcL2U4YjU5MTU0LWMxOTItNDQxNy04ODhiLWY5NzMxYjM2YWU4OVwvZGF4bmtjeC0zZGI1NzkwMC05ZDE3LTRmNjgtODMyMy00YmZkNzAzMWZjM2IuZ2lmIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmZpbGUuZG93bmxvYWQiXX0.W3zjrny0ezsx5e-uGiQcLQKfQbgHFp-MQqGdzqWM-4g" width=100>'
				extra='<img src="https://media1.tenor.com/images/b5c77a0f1690bcfdce0df8c6525ea95e/tenor.gif?itemid=7903387" width=200>'

			elif "BKP" in cards[ os.path.basename(p) ].cardslist.title:
				posicao = "**terminado**"

		# now update the card which is being backed up
		# print os.path.basename(p) in ltoBackup, os.path.basename(p), ltoBackup
		if os.path.basename(p) in ltoBackup:
			posicao="**Movendo para o LTO...**"
			extra='<img src="https://media.giphy.com/media/sRFEa8lbeC7zbcIZZR/giphy.gif" width=200>'

		# create title
		title="**%s**" % os.path.basename(p)
		title+="\n>disco: %s" % disco
		# title+="\nmover: %s" % mover
		title+="\nposicao: %s" % posicao
		title+="\ntamanho: %s" % size
		title+="\n%s" % extra

		# if a card exists

		if hasCard:
			if title.strip() != cards[ os.path.basename(p) ].data['title'].strip():
				# print title.strip() != cards[ os.path.basename(p) ].data['title'].strip()
				# print title, cards[ os.path.basename(p) ].data['title']
				# print cards[ os.path.basename(p) ].cardslist.data
				# print cards[ os.path.basename(p) ].setList('JOBS')

				if not cards[ os.path.basename(p) ].modify( title=title ):
					print "Error updating card for %s!!" % p
			# else:
			# 	print "No update needed!"

		# or else create a new card
		else:
		 	for b  in api.get_user_boards('BACKUP'):
		 		for l in b.get_cardslists('JOBS'):
		 			l.add_card(title)


		if ltoFreeSpace and os.path.basename(p) in ltoBackup:
			title = "**Ainda tem %s de espaco livre**" % ltoFreeSpace
			list = cards[ os.path.basename(p) ].cardslist
			b = list.board
			spaceCard = [ x for x in d[b.title][list.title].keys() if 'ainda tem' in x.lower() ]
			print d[b.title][list.title].keys()
			print spaceCard
			if spaceCard:
				if title != cards[spaceCard[0].replace('*','')].data['title']:
					cards[spaceCard[0].replace('*','')].modify( title=title )
			else:
				list.add_card( "**Ainda tem %s de espaco livre**" % ltoFreeSpace )



print "\nThe following jobs don't exist:"
for n in toRemove:
	print '\t%s' % n

print "\nThe following jobs exist on more than one path:"
keys = repetidos.keys()
keys.sort()
for n in keys:
	if len(repetidos[n])>1:
		print n
		print repetidos[n]



print
