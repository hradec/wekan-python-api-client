#!/bin/python2

import sys, os, time
sys.path.insert(0, os.path.dirname(__file__)+"/src/" )

from wekanapi import WekanApi
from pprint import pprint as pp
from glob import glob
import random, time
import os

lto_ssh='ssh root@nexenta.local'

processes = os.popen("ps -AHfc | grep update | grep -v grep | grep -v tail").readlines()
print len(processes), processes
if len( processes ) > 3:
	print "exiting... too many processess!"
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

# gather information from the LTO machine
ltoFreeSpace = ""
ltoBackup = ''.join(os.popen(lto_ssh+" 'pgrep -fa rsync.*LTO' | tail -1 ").readlines()).strip().split()
if len(ltoBackup) > 3:
	ltoBackup = ltoBackup[3].strip().rstrip('/')
	print "1 ===>",ltoBackup
else:
	ltoBackup = ''
ltoFreeSpace = ''.join(os.popen(lto_ssh+" 'df -h | grep LTO' ").readlines()).strip().split()
if len(ltoFreeSpace) > 3:
	ltoFreeSpace = ltoFreeSpace[-3]
	print "2 ===>",ltoFreeSpace
else:
	ltoFreeSpace = ""
ltoLS = [ '/LTO/%s' % x.strip() for x in os.popen(lto_ssh+" 'ls -1 /LTO/' ").readlines() ]
print "3 ===>",ltoLS

# loop over jobs and update weekan cards with size and other info
folders  = glob("/atomo/jobs/*")
folders += glob("/.LIZARDFS/atomo/jobs/*")
folders += glob("/.MOOSEFS/atomo/jobs/*")
folders += glob("/smb/Backups-3ds/atomo/jobs/*")
folders.sort()
repetidos={}
for p in folders+ltoLS:
	p = os.path.abspath(p).replace('//','/').rstrip('/')
	if os.path.islink(p):
		p = os.readlink(p)
	p = p.replace('//','/').rstrip('/')

	if not os.path.exists(p) and not '/LTO' in p:
		toRemove.append(p)
	elif ( os.path.isdir(p) and not os.path.islink(p) ) or '/LTO' in p:
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
repetidos_sorted = repetidos.keys()
repetidos_sorted.sort()
lto_total = 0
for job in repetidos_sorted:
	# print job
	repetidos[job].sort()
	p = [ x for x in repetidos[job] if '/atomo' in x[0:7] ]
	if p:
		p = p[0]
	else:
		p = repetidos[job][0]

	jobNumber = int(os.path.basename(p).split('.')[0])

	# only consider directories
	if jobNumber < 9000 and jobNumber > 0:
	  # if jobNumber==621:

		print p
		# get the title of the card, if its already exist
		card_title = ""
		hasCard = os.path.basename(p) in j and os.path.basename(p) in cards.keys()
		if hasCard:
			card_title = cards[ os.path.basename(p) ].data['title'].strip()

		# calculate size of jobs just once a day!
		l='/tmp/%s.disk_usage.log' % p.strip('/').replace('/','_')
		if not os.path.exists(l) or ( ( time.time() - int(os.stat(l)[-1]) ) /60 /60 ) > 24  or  os.stat( l )[6] == 0:
			if '/LTO' in p:
				tamanho = 0
				# if we have tamanho in the title
				# if 'tamanho' in card_title:
				# 	# extract the value from it and save to the log file.
				# 	m = [ x for x in card_title.split('\n') if 'tamanho' in x ]
				# 	if m:
				# 		if '**' in m[0]:
				# 			m = m[0].split('**')[1]
				# 		else:
				# 			m = m[0].split(' ')[1]
				#
				# 		mv = float(''.join([x for x in m if x.isdigit() or x=='.']))
				# 		if mv > 0:
				# 			if 'G' in m.upper():
				# 				mv = mv/1000
				# 			elif 'T' in m.upper():
				# 				mv = mv
				# 			else:
				# 				mv = mv/1000/1000
				# 		tamanho = mv
				if not tamanho:
					os.popen( lto_ssh+''' "du -shc %s 2>/dev/null" | grep total > %s ''' % ( p, l ) )
				else:
					os.popen( '''echo "%.2fT" > %s ''' % ( tamanho, l ) )
			else:
				os.popen( 'du -shc %s 2>/dev/null | grep total > %s ' % ( p, l ) )

		# get the last modification date
		lm='/tmp/%s.last_modified.log' % p.strip('/').replace('/','_')
		if not os.path.exists(lm) or ( ( time.time() - int(os.stat(lm)[-1]) ) /60 /60 ) > 24  or  os.stat( lm )[6] == 0:
			if '/LTO' in p:
				if 'modificado' not in card_title:
					# calculate from the TAPE folder
					os.popen( lto_ssh+''' "find %s -type f -printf '%%T@ %%p\n'" | sort -n | tail -1 2>/dev/null  >  %s ''' % ( p, lm ) )
			else:
				os.popen( "sudo find %s -type f -printf '%%T@ %%p\n' | sort -n | tail -1 2>/dev/null  >  %s " % ( p, lm ) )

		size= ''.join(open( l ).readlines()).split()[0].strip()
		disco=os.path.dirname(p)
		mover=""
		posicao=""
		last_modified=""
		extra=""

		# months is later to write the position string...
		months=0
		# write the last modified string
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
		elif 'modificado' in card_title:
			# keep last modification from card title
			m = [ x for x in card_title.split('\n') if 'modificado' in x ]
			print cards[ os.path.basename(p) ].data['title'].strip()
			if m:
				last_modified = '\n%s' % m[0]



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
				print os.path.basename(p) in ltoBackup, os.path.basename(p), ltoBackup
				if os.path.basename(p) in ltoBackup:
					posicao="**movendo para o LTO...**"

				m = [ x for x in card_title.split('\n') if 'tamanho' in x ]
				if m:
					if '**' in m[0]:
						m = m[0].split('**')[1]
					else:
						m = m[0].split(' ')[1]
					if 'G' in m.upper():
						m = 1000/float(''.join([x for x in m if x.isdigit() or x=='.']))
					elif 'T' in m.upper():
						m = float(''.join([x for x in m if x.isdigit() or x=='.']))
					else:
						m = 1000/1000/float(''.join([x for x in m if x.isdigit() or x=='.']))

					lto_total += m


			elif "BKP" in cards[ os.path.basename(p) ].cardslist.title:
				if 'esperando...' not in card_title:
					# TODO: write the code to start rsync when cards have "esperando..." in it, and are in a BKP* list
					print "\n\nNeed to write the code to start rsync when a %s is 'esperando...' in the LTO list\n\n" % job

				posicao = "**esperando...**"
				# if the path is being copied over right now... (ltoBackup tells us that!)
				if os.path.basename(p) in ltoBackup:
					posicao="**movendo para o LTO...**"

				# if the job name is in the current loaded LTO...
				elif job in [ os.path.basename(x) for x in ltoLS ]:
					rep = repetidos[job]
					# if we have more than one path for the job that is in
					# the LTO tape, we need to delete the other ones
					if len( rep )>1:
						# TODO: we need to write the code to double check if the LTO copy is 100% the other paths.
						# TODO: if we known the LTO copy is OK, then move it to a deleted folder to be deleted after 48hours
						posicao = "**terminado - falta apagar %s**" % ', '.join(repetidos[job])
					else:
						# theres no other path for the JOB in the LTO
						posicao = "**terminado - %s**" % cards[ os.path.basename(p) ].cardslist.title

					# keep the size from the card title
					# m = [ x for x in card_title.split('\n') if 'tamanho' in x ]
					# if m:
					# 	if '**' in m[0]:
					# 		tsize = m[0].split('**')[1]
					# 	else:
					# 		tsize = m[0].split(' ')[1]
					# 	if float(tsize) > 0:
					# 		size = tsize


		# set extra information (icons)
		if 'esperando' in posicao:
			# extra='<img src="%s" width=200 height=70>' % gifs['esperando'][random.randint(0, len(gifs['esperando'])-1)]
			gif_counter['esperando'] += 1
			if gif_counter['esperando'] >= len(gifs['esperando']):
				gif_counter['esperando'] = 0

			extra='<img src="%s" width=200 height=50>' % gifs['esperando'][gif_counter['esperando']]

		elif 'movendo' in posicao:
			extra='<img src="https://media.giphy.com/media/sRFEa8lbeC7zbcIZZR/giphy.gif" width=200 height=50>'

		elif 'apagar' in posicao:
			posicao += '<img src="http://www.alpes-maritimes.gouv.fr/var/ezwebin_site/storage/images/media/images/icones/triangle-attention/148314-1-fre-FR/Triangle-Attention_small.gif" width=20 height=20>'

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
			if 'BKP' in  list.title or 'EXT' in  list.title:
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



# lto_total
# def createListTotal( p ):
# 	list = cards[ os.path.basename(p) ].cardslist
# 	b = list.board
# 	title = "**%s - %%s total**" % ( list.title )
# 	spaceCard = [ x for x in d[b.title][list.title].keys() if 'total**' in x.lower() ]
# 	if spaceCard:
# 		title = cards[ spaceCard[0].replace('*','') ].data['title']
#
# 		total = float(title.split(' ')[0])+
# 		if title != cards[spaceCard[0].replace('*','')].data['title']:
# 			cards[spaceCard[0].replace('*','')].modify( title=title )
# 	else:
# 		list.add_card( title )


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
