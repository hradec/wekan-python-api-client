#!/bin/python2

import sys, os, time
import wbackup

from pprint import pprint as pp
from glob import glob
import random, time
import os

wbackup.runOnlyOnce( __file__ )

api = wbackup.api()

# gifs!!
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

# grab all cards form the weekan BACKUP board and store in hierarquical dict "d"
# and a cards dictionary
result = wbackup.getCards()
d     = result['data']
cards = result['cards']
jobs  = result['jobs']

# create a big string with all titles so we can fast and easyly find
# if a job already has a card!
j=''.join(jobs)

# gather information from the LTO machine
ltoBackup = wbackup.runningLTO()
ltoFreeSpace = wbackup.freespaceLTO()
ltoLS = wbackup.lsLTO()
labelLTO = wbackup.labelLTO()
print ltoLS,ltoFreeSpace,ltoBackup, wbackup.hasTapeLTO()

# find all jobs is all paths, and return a dictionary with job names as keys
# and all paths for the job as a list.
repetidos = wbackup.findAllJobs(ltoLS)
toRemove=wbackup.toRemove()
paths=[]

# sort the jobs just because...
pode_apagar = []
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
	  	# print p

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
				# size = [x for x in title if 'tamanho: ' in x]
				# if size:
				# 	tamanho = wbackup.convertHtoV(size[0])
				if not tamanho:
					os.popen( wbackup.lto_ssh+''' "du -shc %s 2>/dev/null" | grep total > %s ''' % ( p, l ) )
				else:
					os.popen( '''echo "%s\ttotal" > %s ''' % ( wbackup.convertVtoH(tamanho), l ) )
			else:
				os.popen( 'du -shc %s 2>/dev/null | grep total > %s ' % ( p, l ) )

		# get the last modification date
		lm='/tmp/%s.last_modified.log' % p.strip('/').replace('/','_')
		if not os.path.exists(lm) or ( ( time.time() - int(os.stat(lm)[-1]) ) /60 /60 ) > 24  or  os.stat( lm )[6] == 0:
			if '/LTO' in p:
				if 'modificado' not in card_title:
					# calculate from the TAPE folder
					os.popen( wbackup.lto_ssh+''' "find %s -type f -printf '%%T@ %%p\n'" | sort -n | tail -1 2>/dev/null  >  %s ''' % ( p, lm ) )
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
			# print cards[ os.path.basename(p) ].data['title'].strip()
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
				# print os.path.basename(p) in ltoBackup, os.path.basename(p), ltoBackup
				if os.path.basename(p) in ltoBackup:
					posicao="**movendo para o LTO...**"
				else:
					wbackup.removeRsyncLogLTO( p )

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
				posicao = "**esperando...**"
				if 'esperando...' in card_title:
					# TODO: write the code to start rsync when cards have "esperando..." in it, and are in a BKP* list
					if labelLTO in cards[ os.path.basename(p) ].cardslist.title:
						print "Need to write the code to start rsync when a %s (%s) is 'esperando...' in the LTO list" % (job, p)
						tailLog = wbackup.checkRsyncLog4ErrorsLTO( p )
						print tailLog
						if 'JOB NAO CABE NA FITA' in tailLog:
							posicao += '\n<font color="red"> %s </font>' % tailLog

				# if the path is being copied over right now... (ltoBackup tells us that!)
				if os.path.basename(p) in ltoBackup:
					print ltoBackup
					posicao="**movendo para o LTO...**"

				# if the job name is in the current loaded LTO...
				elif job in [ os.path.basename(x) for x in ltoLS ]:
					rep = repetidos[job]
					# if we have more than one path for the job that is in
					# the LTO tape, we need to delete the other ones
					if len( rep )>1:
						checkRsyncLogLTO = wbackup.checkRsyncLogLTO( p )
						if len(checkRsyncLogLTO) < 4:
							tailLog = wbackup.checkRsyncLog4ErrorsLTO( p )
							if tailLog:
								posicao = '**esperando...** \n<font color="red"> %s </font>\n' % tailLog
							else:
								posicao = "**esperando... \n(falta verificar %s vezes)**" % (4-len(checkRsyncLogLTO))
						else:
							# we now only set as "falta apagar" after it has being verified
							posicao = "**terminado\npode apagar %s**" % ', '.join([ x for x in repetidos[job] if 'LTO' not in x])
							pode_apagar += [ x for x in repetidos[job] if 'LTO' not in x]
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
				# print d[b.title][list.title].keys()
				# print spaceCard
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


# list links that dont't exist anymore
if toRemove:
	print "\nThe following jobs don't exist:"
	for n in toRemove:
		print '\tsudo rm -f {:<40} #=> {:<12}'.format( n, os.readlink(n) )

# jobs that exist in multiple storages!!
if repetidos.keys():
	print "\nThe following jobs exist on more than one path:"
	keys = repetidos.keys()
	keys.sort()
	for n in keys:
		if len(repetidos[n])>1:
			print '\t',n
			for r in repetidos[n]:
				print '\t\t',r
			print

# jobs backed up and verified that can be deleted
if pode_apagar:
	print "\nThe following jobs are on the LTO tape and can be deleted:"
	for j in pode_apagar:
		print '\tsudo rm -rf %s' % j


print
