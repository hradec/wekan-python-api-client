#!/bin/python2

import sys, os, time
sys.path.insert(0, os.path.dirname(__file__)+"/src/" )

from wekanapi import WekanApi
from pprint import pprint as pp
from glob import glob
import random, time
import os


processes = os.popen("ps -AHfc | grep update | grep -v grep | grep -v tail").readlines()
print len(processes), processes
if len( processes ) > 2:
	exit(0)

api = WekanApi("http://192.168.0.16:8080/wekan", eval(''.join(open(os.path.dirname(__file__)+"/userpasswd.txt").readlines())), )
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
print ltoBackup
ltoFreeSpace = ''.join(os.popen("ssh root@nexenta.local 'df -h | grep LTO'").readlines()).strip().split()[-3]
print ltoFreeSpace
ltoLS = [ x.strip() for x in os.popen("ssh root@nexenta.local 'ls -1 /LTO/'").readlines() ]
print ltoLS

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


wh = (200,70)
gifs={
	'esperando' : [
		# 'https://media.tenor.com/images/3887c2e4935e851062bfb30ab503a0b3/tenor.gif',
		'https://data.whicdn.com/images/98966151/original.gif',
		# 'https://media1.tenor.com/images/e63c6e5bad162196621b12890c0d574f/tenor.gif?itemid=5530289',
	],
}
gif_counter={
	'esperando' : 0,
}
for job in repetidos.keys():
	# print job
	repetidos[job].sort()
	p = [ x for x in repetidos[job] if '/atomo' in x[0:7] ]
	if p:
		p = p[0]
	else:
		p = repetidos[job][0]

	jobNumber = int(os.path.basename(p).split('.')[0])

	# only consider directories
	if jobNumber < 9000 and jobNumber > 0: # and jobNumber==587:

		# calculate size of jobs just once a day!
		print p
		l='/tmp/%s.disk_usage.log' % p.strip('/').replace('/','_')
		lm='/tmp/%s.last_modified.log' % p.strip('/').replace('/','_')
		if not os.path.exists(l) or ( ( time.time() - int(os.stat(l)[-1]) ) /60 /60 ) > 24  or  os.stat( l )[6] == 0:
			os.popen( 'du -shc %s 2>/dev/null | grep total > %s ' % ( p, l ) )

		if not os.path.exists(lm) or ( ( time.time() - int(os.stat(lm)[-1]) ) /60 /60 ) > 24  or  os.stat( lm )[6] == 0:
			# os.popen( "sudo find %s -type f -printf '%%T@ %%p\n' | sort -n | tail -1 | date -d@$(awk '{print $1}') 2>/dev/null  >  %s" % ( p, lm ) )
			os.popen( "sudo find %s -type f -printf '%%T@ %%p\n' | sort -n | tail -1 2>/dev/null  >  %s" % ( p, lm ) )

		size= ''.join(open( l ).readlines()).split()[0].strip()
		disco=os.path.dirname(p)
		mover=""
		posicao=""
		last_modified=""
		extra=""
		months=0

		if os.path.exists( lm ):
			epoch=''.join(open( lm ).readlines()).strip().split()
			if len(epoch) > 1:
				secs = time.time()-float(epoch[0])
				(months, remainder) = divmod(secs, 86400*30)
				(days, remainder) = divmod(remainder, 86400)
				(hours, remainder) = divmod(remainder, 60*60)
				(mins, remainder) = divmod(remainder, 60)
				color="green"

				dias = "%s dias" % int(days)
				if days == 1:
					dias = "%s dia" % int(days)
				elif days == 0:
					if hours>0:
						dias = "%s horas" % int(hours)
					else:
						dias = "%s minutos" % int(mins)

				meses = "%s meses " % int(months)
				if int(months) > 5:
					color="red"
				elif int(months) > 1:
					color="orange"
				elif int(months) == 1:
					meses = "%s mes " % int(months)
				elif int(months) == 0:
					meses=""
				last_modified = '\nmodificado a:**<font color="%s"> %s%s</font>**' % ( color, meses, dias )

		hasCard = os.path.basename(p) in j and os.path.basename(p) in cards.keys()
		if hasCard:
			if cards[ os.path.basename(p) ].cardslist.title == "JOBS":
				if months < 2:
					posicao = "**em producao**"
				elif months < 3:
					posicao = '**parado...**'
				else:
					posicao = '**<font color="red">Fazer Backup?</font>**'

			elif "LIZARD" in cards[ os.path.basename(p) ].cardslist.title:
				posicao = "**esperando...**"
				if [ x for x in repetidos[job] if 'LIZARD' in x ]:
					if len( repetidos[job] )>1:
						posicao = "**movendo pro LizardFS**"
					else:
						posicao = "**terminado**"

			elif "LTO" in cards[ os.path.basename(p) ].cardslist.title:
				posicao = "**esperando...**"
				# now update the card which is being backed up
				# print os.path.basename(p) in ltoBackup, os.path.basename(p), ltoBackup
				if os.path.basename(p) in ltoBackup:
					posicao="**movendo para o LTO...**"
					if len( repetidos[job] )>1:
						posicao = "**movendo pro LizardFS**"
					else:
						posicao = "**terminado**"


			elif "BKP" in cards[ os.path.basename(p) ].cardslist.title:
				posicao = "**esperando...**"
				if job in ltoLS:
					posicao = "**terminado - %s**" % cards[ os.path.basename(p) ].cardslist.title

		# set extra information
		if 'esperando' in posicao:
			# extra='<img src="%s" width=200 height=70>' % gifs['esperando'][random.randint(0, len(gifs['esperando'])-1)]
			gif_counter['esperando'] += 1
			if gif_counter['esperando'] >= len(gifs['esperando']):
				gif_counter['esperando'] = 0

			extra='<img src="%s" width=200 height=50>' % gifs['esperando'][gif_counter['esperando']]

		elif 'movendo' in posicao:
			extra='<img src="https://media.giphy.com/media/sRFEa8lbeC7zbcIZZR/giphy.gif" width=200 height=50>'

		elif 'terminado' in posicao:
			posicao += ' <img src="https://thumbs.gfycat.com/ShyCautiousAfricanpiedkingfisher-size_restricted.gif" width=12 height=12>'

		elif 'parado' in posicao:
			posicao += ' <img src="https://static.wixstatic.com/media/5c6573_1072137d8e4d4d60ab1a91a0e861da09~mv2.gif" width=80 height=16>'

		elif 'backup' in posicao.lower():
			posicao += '   '
			posicao += '<img src="http://www.alpes-maritimes.gouv.fr/var/ezwebin_site/storage/images/media/images/icones/triangle-attention/148314-1-fre-FR/Triangle-Attention_small.gif" width=20 height=20>'

		# elif 'producao' in posicao:
		# 	posicao += ' <img src="https://www.shopitcommerce.com/wp-content/uploads/2019/03/production-line-boxes.gif" width=200 height=30>'

		if 'LIZARD' in disco:
			disco = '<font color="#959">'+disco+'</font>'
		elif 'MOOSE' in disco:
			disco = '<font color="#57A">'+disco+'</font>'
		elif 'smb' in disco:
			disco = '<font color="#994">'+disco+'</font>'
		else:
			disco = '<font color="#599">'+disco+'</font>'

		# create title
		title="**%s**" % os.path.basename(p)
		title+='\n>disco: **%s**' % disco
		# title+="\nmover: %s" % mover
		title+="\ntamanho: **%s**" % size
		title+= last_modified
		title+="\nposicao: %s" % posicao
		title+="\n%s" % extra
		title+=""

		# if a card exists

		if hasCard:
			if title.strip() != cards[ os.path.basename(p) ].data['title'].strip() or 1:
				# print title.strip() != cards[ os.path.basename(p) ].data['title'].strip()
				# print title, cards[ os.path.basename(p) ].data['title']
				# print cards[ os.path.basename(p) ].cardslist.data
				# print cards[ os.path.basename(p) ].setList('JOBS')

				if not cards[ os.path.basename(p) ].modify( title=title ):
					print "Error updating card for %s!!" % p

				# if not cards[ os.path.basename(p) ].modify( description="TESTE" ):
				# 	print "Error updating card for %s!!" % p

			# else:
			# 	print "No update needed!"

		# or else create a new card
		else:
		 	for b  in api.get_user_boards('BACKUP'):
		 		for l in b.get_cardslists('JOBS'):
		 			l.add_card(title)


		if ltoFreeSpace and os.path.basename(p) in ltoBackup:
			list = cards[ os.path.basename(p) ].cardslist
			b = list.board
			title = "**%s - %s livre**" % ( list.title, ltoFreeSpace )
			spaceCard = [ x for x in d[b.title][list.title].keys() if 'livre**' in x.lower() ]
			print d[b.title][list.title].keys()
			print spaceCard
			if spaceCard:
				if title != cards[spaceCard[0].replace('*','')].data['title']:
					cards[spaceCard[0].replace('*','')].modify( title=title )
			else:
				list.add_card( title )



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
