#!/bin/python2

import sys, os, time
import re
from glob import glob
from decimal import Decimal
import random, time
import os
import math

import wbackup

verificarNvezes = 4

class jobCards:
    gifs={
        'esperando' : [
            # 'https://media.tenor.com/images/3887c2e4935e851062bfb30ab503a0b3/tenor.gif',
            'https://data.whicdn.com/images/98966151/original.gif',
            # 'https://media1.tenor.com/images/e63c6e5bad162196621b12890c0d574f/tenor.gif?itemid=5530289',
        ],
    }
    # a counter to switch the gif
    gif_counter={
        'esperando' : 0,
    }
    def __init__( self, board = 'BACKUP', justCards=False ):
        self.api = wbackup.api()
        # grab all cards form the weekan BACKUP board and store in hierarquical dict "d"
        # and a cards dictionary
        self.cardsData = wbackup.getCards( str(board) )
        self.d     = self.cardsData['data']
        self.cards = self.cardsData['cards']
        self.jobs  = self.cardsData['jobs']

        # create a big string with all titles so we can fast and easyly find
        # if a job already has a card!
        self.j=''.join(self.jobs)

        if not justCards:
            # gather information from the storages
            self.storages = wbackup.getStoragesInfo()

            # gather information from the LTO machine
            self.ltoBackup = wbackup.runningLTO()
            # print self.ltoBackup
            self.ltoFreeSpace = wbackup.freeSpace( '/LTO' )
            self.ltoLS = wbackup.lsLTO()
            self.labelLTO = wbackup.labelLTO()

            # find all jobs is all paths, and return a dictionary with job names as keys
            # and all paths for the job as a list.
            self.all_jobs = wbackup.findAllJobs(self.ltoLS)
            self.toRemove = wbackup.toRemove()
            self.paths=[]

            # sort the jobs just because...
            self.pode_apagar = []
            self.repetidos_sorted = self.all_jobs.keys()
            self.repetidos_sorted.sort()
            self.lto_total = 0

            # sort all paths of a job once
            for job in self.repetidos_sorted:
                self.all_jobs[job].sort()

            # initialize lists dict
            self._lists = {}
            self._lists_clean = {}
            for job in self.keys():
                _card = self._cards(job)
                if _card:
                    if _card.cardslist.title not in self._lists:
                        self._lists[_card.cardslist.title] = {}
                    self._lists[_card.cardslist.title][job] = _card
                    if 'livre' not in job:
                        if _card.cardslist.title not in self._lists_clean:
                            self._lists_clean[_card.cardslist.title] = {}
                        self._lists_clean[_card.cardslist.title][job] = _card
                        # keep data that is in the card title
                        # inside attrs disctionary in the card object
                        self._all_attrs( _card )

    # remove wrongly duplicated cards on the same list.
    def _cards_remove_duplicated(self, job):
        _card = self.cards[ job ]

        if type(_card) == type([]):
            if len(_card)>1:
                print job, len(_card)
                for n in _card[10:]:
                    print n.id, n.modify( archived=True )

    # only return cards of BKP lists which the tape is inserted
    def _cards( self, job ):
        _card = self.cards[ job ]

        if type(_card) == type([]):
            cards = [ x for x in _card if 'BKP' in  x.cardslist.title and self.labelLTO in x.cardslist.title ]
            if not cards:
                _card = None
            else:
                # we return just the first card, since we shouldn't have more than one
                # card for the same job on the same tape!
                _card = cards[0]
                print job, _card

        # if its a card in a BKP list that is not the tape in the LTO drive,
        # ignore it! This should speed up the run since we won't process
        # cards in all BKP lists, but the one with the tape in the drive!
        if _card and 'BKP' in  _card.cardslist.title and self.labelLTO not in  _card.cardslist.title and '/LTO' in _card.title:
            _card = None

        return _card

    # cleanup formating and html junk from a string
    def _cleanup_string( self, txt ):
        ret = re.sub( '<[^<]+?>', '', txt.strip().replace('**','') )
        ret = ret.replace('>','').strip()
        return ret

    # cleanup a title line
    def _cleanup_title_line( self, line ):
        ret = ''
        if line:
            if type(line) == type([]):
                line = line[0]
            ret = self._cleanup_string( line )
        return ret

    # detect and store all attributes in a card title
    def _all_attrs( self, card ):
        value = ''
        if type(card) == type(""):
            card = self._cards(card)
        if card:
            title = card.title
            for line in [ x for x in title.split('\n') if ':' in x ]:
                line = self._cleanup_string( line )
                self._attr( card, line.split(':')[0] )

    # store attribute from a card title in the
    # .attrs dict in the card object
    def _attr( self, card, attr ):
        value = ''
        if type(card) == type(""):
            card = self._cards(job)
        if card:
            title = self._cleanup_title_line( card.title ).split('\n')
            value = [ self._cleanup_string(x).split(':')[-1].strip() for x in title if attr in x ]
            if not value:
                return ''
            value = value[0]
            if not hasattr( card, 'attr' ):
                card.attr = {}
            card.attr[ attr ] = value

            if 'tamanho' == attr:
                card.attr[ 'raw_'+attr ] = wbackup.convertHtoV(value)
            if 'disco' == attr:
                card.attr[ 'path' ] = '/'.join([ value, title[0] ]).replace('//','/')
        return value


    # returns a list with the card names, so one can access the card class
    # by using the names in the list, calling this class[name], like a dict
    def keys(self, filter=''):
        return [ x for x in self.cards.keys() if filter in x ]

    def jobsOnDisk(self, filter=''):
        return [ x for x in self.all_jobs.keys() if filter in x ]

    # return the cards in a given list name
    def lists( self ):
        return self._lists_clean

    # one can use this class like a dictionary
    def __getitem__( self, job_name ):
        return self._cards( os.path.basename(job_name) )


    def strtime( self, secs ):
        last_modified = ''
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
        last_modified = meses + dias
        return last_modified


    # update the cards in the BACKUP board
    def update( self, job ):
        # self.labelLTO = wbackup.labelLTO()

        p = [ x for x in self.all_jobs[job] if '/atomo' in x[0:7] ]
        if p:
            p = p[0]
        else:
            p = self.all_jobs[job][0]


        # only consider real job numbers
        try: jobNumber = int(os.path.basename(p).split('.')[0])
        except: jobNumber = 99999999
        if jobNumber < 9000 and jobNumber > 0:
          # if jobNumber==621:
            print p

            # get the title of the card, if its already exist
            card_title = ""
            hasCard = os.path.basename(p) in self.j and os.path.basename(p) in self.cards.keys()
            if hasCard:
                _card = self._cards( os.path.basename(p) )
                # if the card is in a BKP list, but the list doesn't have the name of the
                # inserted tape, _card will be None!
                if not _card:
                    print "card in bkp, but tape not inserted, so create a new card for:",p
                    hasCard = False
                else:
                    card_title = _card.data['title'].strip()

            # keep data that is in the card title
            _disco      = [ x for x in card_title.split('\n') if 'disco' in x ]
            _tamanho    = [ x for x in card_title.split('\n') if 'tamanho' in x ]
            _posicao    = [ x for x in card_title.split('\n') if 'posicao' in x ]
            _decorrido  = [ x for x in card_title.split('\n') if 'decorrido' in x ]
            _modificado = [ x for x in card_title.split('\n') if 'modificado' in x ]

            # calculate size of jobs just once a day!
            l='/tmp/%s.disk_usage.log' % p.strip('/').replace('/','_')
            if not os.path.exists(l) or ( ( time.time() - int(os.stat(l)[-1]) ) /60 /60 ) > 24  or  os.stat( l )[6] == 0:
                # if the only path for the job is the LTO...
                if '/LTO' in p:
                    tamanho = 0
                    # if we have the size in the card, we don't need to
                    # calculate it from the LTO folder
                    if _tamanho:
                        tamanho = wbackup.convertHtoV(_tamanho[0].split(':')[-1])

                    # query the data in the LTO to get the job size, since we don't
                    # have it! This will only happen for already in tape jobs,
                    # since the size should come from the original folder on disk
                    # for new cards being backed up!
                    if not tamanho:
                        os.popen( wbackup.lto_ssh+''' "du -shc %s 2>/dev/null" | grep total > %s ''' % ( p, l ) )
                    # but if we have it already, just re-create the log with it.
                    else:
                        os.popen( '''echo "%s\ttotal" > %s ''' % ( wbackup.convertVtoH(tamanho), l ) )

                # if the job is in a storage other than LTO tape, we have to calculate it!
                else:
                    os.popen( 'du -shc %s 2>/dev/null | grep total > %s ' % ( p, l ) )

            # get the last modification date
            lm='/tmp/%s.last_modified.log' % p.strip('/').replace('/','_')
            if not os.path.exists(lm) or ( ( time.time() - int(os.stat(lm)[-1]) ) /60 /60 ) > 24  or  os.stat( lm )[6] == 0:
                # if the only path for the job is the LTO...
                if '/LTO' in p:
                    # and we don't already have the last modification time in the card
                    if not _modificado:
                        # calculate from the TAPE folder
                        os.popen( wbackup.lto_ssh+''' "find %s -type f -printf '%%T@ %%p\n'" | sort -n | tail -1 2>/dev/null  >  %s ''' % ( p, lm ) )
                else:
                    # find the last modification time from the job folder
                    os.popen( "sudo find %s -type f -printf '%%T@ %%p\n' | sort -n | tail -1 2>/dev/null  >  %s " % ( p, lm ) )

            # variables used to construtct the card title!
            size= ''.join(open( l ).readlines()).split()[0].strip()
            disco=os.path.dirname(p)
            mover=""
            posicao=""
            last_modified=""
            extra=""

            # months is later to write the position string...
            months=0
            # If we have a last modified log file
            if os.path.exists( lm ):
                # pull the last_modified time from it!
                epoch=''.join(open( lm ).readlines()).strip().split()
                # construct the string now!
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
            elif _modificado:
                # use the last_modified from the card title...
                last_modified = '\n%s' % _modificado[0]

            # if the card exists, we construct the posicao variable
            # for it, depending on the list the card is in...
            if hasCard:
                if [ x for x in ["JOBS","LIZARD","BTRFS"] if x in _card.cardslist.title ]:
                    if months < 2:
                        posicao = "**em producao**"
                    elif months < 3:
                        posicao = '**parado...**'
                    else:
                        posicao = '**<font color="red">Fazer Backup?</font>**'

                if "LTO" in _card.cardslist.title:
                    extra=''
                    _decorrido = []
                    posicao = "**esperando...**"
                    # now update the card which is being backed up
                    # print os.path.basename(p) in ltoBackup, os.path.basename(p), ltoBackup
                    if os.path.basename(p) in self.ltoBackup:
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

                        self.lto_total += m

                elif "MOVER PARA" in _card.cardslist.title:
                    label = _card.cardslist.title.split()[-1]

                    storage = [x for x in wbackup.storages if x in _card.list.title]
                    target = '/'.join([ wbackup.storages[storage[0]], p ])
                    percentage = wbackup.copiedPercentage( p, target )
                    print p, target,  percentage

                    paths_in_label = [ x for x in self.all_jobs[job] if (label in x or label.lower() in x) and '/LTO' not in x ]
                    paths_not_in_label = [ x for x in self.all_jobs[job] if label not in x and label.lower() not in x and '/LTO' not in x ]
                    print paths_in_label
                    extra = ''
                    if paths_in_label:
                        result = wbackup.checkRsyncLog( p )
                        vezes = len(result)
                        print p,vezes
                        if len( self.all_jobs[job] )>1:
                            posicao = "**movendo...**"
                            if percentage > 99.0:
                                if vezes>=0 and vezes<=verificarNvezes:
                                    posicao = "**falta verificar %d vezes**" % (verificarNvezes-len(result))
                                    extra = " "
                                else:
                                    if vezes < 0:
                                        vezes = 0
                                    posicao =  "**terminado\n(Verificado %d %s)\npode apagar:**" % (
                                        vezes,
                                        'vez' if vezes < 2 else 'vezes',
                                    )
                                    extra = "%s\n" % ', '.join(paths_not_in_label)
                                    self.pode_apagar += paths_not_in_label
                        else:
                            extra = "copia: **terminada**"
                    if extra=="":
                    	posicao = "**esperando...**"



                    if _tamanho:
                        __size = wbackup.convertHtoV( _tamanho[0].split(':')[-1].strip() )
                        if label in self.storages['free'] and self.storages['free'][ label ]['free'] - __size < 0:
                            posicao = '<font color="red">**NAO CABE NO STORAGE**</font>'

                    mvlog = '/tmp/move_%s.log' % os.path.basename(p)
                    if os.path.exists(mvlog) and 'terminad' not in extra:
                        START_TIME = ''.join(os.popen('grep START_TIME %s | tail -1' % mvlog).readlines())
                        if 'NO SPACE LEFT' in START_TIME:
                            posicao = '<font color="red">**NAO CABE NO STORAGE**</font>'
                        if ':' in START_TIME:
                            START_TIME = Decimal(START_TIME.split(':')[-1])
                            elapsed = Decimal(time.time()) - START_TIME
                            if wbackup.move_delay-elapsed > 0:
                                extra += '**%s para comecar...**\n' % self.strtime( wbackup.move_delay - elapsed )
                            else:
                                if wbackup.moving( '/tmp/move_.*.log' ):
                                    print wbackup.moving( _card.attr['path'] + '.*/tmp/move_.*.log' )
                                    if wbackup.moving( _card.attr['path'] + '.*/tmp/move_.*.log' ):
                                        storage = [x for x in wbackup.storages if x in _card.list.title]
                                        if storage:
                                            posicao  = "**movendo... %3.2f%%**" % (percentage)
                                        ttf = wbackup.copyTimeToFinish( p, returnAsString = True )
                                        print ttf
                                        if ttf[0]:
                                            posicao += "\ndecorrido: **%s**" % ttf[1]
                                            posicao += "\nprevisao: **%s**" % ttf[0]
                                            _decorrido = []
                                    else:
                                        if 'terminad' not in posicao:
                                            extra += '**esperando outra copia terminar...**\n'
                                            if 'esperando' in posicao:
                                                extra += '**outra copia terminar...**\n'
                                        extra += "**(%3.2f%% feito)**\n" % percentage
                                else:
                                    if 'terminado' in posicao or 'falta' in posicao:
                                        extra += '**comecar...**\n'
                        # checkRsyncLogLTO = wbackup.checkRsyncLogLTO( p )

                elif "BKP" in _card.cardslist.title:
                    job_in_the_tape = [ x for x in self.all_jobs[job] if '/LTO' in x[0:6] ]
                    posicao = "**esperando...**"
                    if 'esperando...' in card_title:
                        # TODO: write the code to start rsync when cards have "esperando..." in it, and are in a BKP* list
                        if self.labelLTO in _card.cardslist.title:
                            tailLog = wbackup.checkRsyncLog4ErrorsLTO( p )
                            print tailLog
                            if 'JOB NAO CABE NA FITA' in tailLog:
                                posicao += '\n<font color="red"> %s </font>' % tailLog

                    # if the path is being copied over right now... (self.ltoBackup tells us that!)
                    print os.path.basename(p) in self.ltoBackup, os.path.basename(p), self.ltoBackup
                    if os.path.basename(p) in self.ltoBackup:
                        posicao="**movendo para o LTO...**"
                        # if the job exists in the /LTO folder, we can check the percentage
                        # of files copied over to it.
                        if job_in_the_tape:
                            percentage = wbackup.copiedPercentageLTO( p )
                            posicao  = "**movendo... %3.2f%%**" % (percentage)
                            ttf = wbackup.copyTimeToFinishLTO( p, returnAsString = True )
                            print "wbackup.copyTimeToFinishLTO", ttf
                            if len(ttf)>1:
                                posicao += "\ndecorrido: **%s**" % ttf[1]
                                posicao += "\nprevisao: **%s**" % ttf[0]
                                # since we're adding decorrido here, reset the one
                                # kept from the title!
                                _decorrido = []

                    # if the job name is in the current loaded LTO...
                    elif job in [ os.path.basename(x) for x in self.ltoLS ]:
                        rep = self.all_jobs[job]
                        # if the job exists in the /LTO folder, we can check the percentage
                        # of files copied over to it.
                        if len( rep )>1 and job_in_the_tape:
                            # count the amount of "result: 0" in the log
                            # which should naively indicate that rsync finished
                            # without error.
                            checkRsyncLogLTO = wbackup.checkRsyncLogLTO( p )
                            vezes = verificarNvezes-len(checkRsyncLogLTO)
                            vezesStr = 'vez'
                            if vezes > 1:
                                vezesStr = 'vezes'

                            if job_in_the_tape:
                                percentage = wbackup.copiedPercentageLTO( p )

                            # if the backup is not done, lets try to give some information
                            # in the cards about the reason...
                            if len(checkRsyncLogLTO) < 4 or percentage < 100.0:
                                # not all files have being copied over to the tape
                                if percentage < 100.0:
                                    tailLog = wbackup.checkRsyncLog4ErrorsLTO( p )
                                    if tailLog:
                                        posicao = '**esperando... <font color="red">(Erro!)</font>** \n(%3.2f%% feito. Falta %3.2f%%)\n<font color="red"> %s </font>\n' % (
                                            percentage,
                                            100.0-percentage,
                                            tailLog,
                                        )
                                    else:
                                        posicao = "**esperando...\n(%3.2f%% feito. Falta %3.2f%%)**" % (percentage, 100.0-percentage)
                                # ok, all files are in the tape, so
                                # we didn't verified 4 times yet!
                                else:
                                    posicao = "**esperando... \n(%.2f%% - falta verificar %s %s)**" % (percentage, vezes, vezesStr)
                                    # remove decimals if it's .00 to save char space
                                    posicao = posicao.replace('.00','')

                            # so, all verification is done, and 100% of the files
                            # have being copied over.
                            else:
                                # we now only set as "falta apagar" after it has being verified
                                posicao = "**terminado(%3.2f%% feito. Verificado %d %s)\npode apagar %s**" % (
                                    percentage,
                                    verificarNvezes-vezes,
                                    'vez' if verificarNvezes-vezes < 2 else 'vezes',
                                    ', '.join([ x for x in self.all_jobs[job] if 'LTO' not in x])
                                )
                                self.pode_apagar += [ x for x in self.all_jobs[job] if 'LTO' not in x]

                        # the job has being deleted from the original folder
                        else:
                            # theres no other path for the JOB in the LTO
                            posicao = "**terminado**"
                            extra = "bakup: **terminado - %s**" % self.labelLTO


            # after setting the posicao variable, we use it to define extra
            # information to the card, like icons and stuff...
            if 'terminad' in extra:
                extra += ' <img src="https://thumbs.gfycat.com/ShyCautiousAfricanpiedkingfisher-size_restricted.gif" width=12 height=12>\n'

            if 'esperando' in posicao:
                # extra='<img src="%s" width=200 height=70>' % gifs['esperando'][random.randint(0, len(gifs['esperando'])-1)]
                self.gif_counter['esperando'] += 1
                if self.gif_counter['esperando'] >= len(self.gifs['esperando']):
                    self.gif_counter['esperando'] = 0

                extra+='<img src="%s" width=200 height=50>' % self.gifs['esperando'][self.gif_counter['esperando']]

            elif 'movendo' in posicao:
                extra+='<img src="https://media.giphy.com/media/sRFEa8lbeC7zbcIZZR/giphy.gif" width=200 height=50>'

            elif 'apagar' in posicao:
                posicao += '<img src="http://www.alpes-maritimes.gouv.fr/var/ezwebin_site/storage/images/media/images/icones/triangle-attention/148314-1-fre-FR/Triangle-Attention_small.gif" width=20 height=20>'

            elif 'parado' in posicao:
                posicao += ' <img src="https://static.wixstatic.com/media/5c6573_1072137d8e4d4d60ab1a91a0e861da09~mv2.gif" width=80 height=16>'

            elif 'backup' in posicao.lower():
                posicao += '   '
                posicao += '<img src="http://www.alpes-maritimes.gouv.fr/var/ezwebin_site/storage/images/media/images/icones/triangle-attention/148314-1-fre-FR/Triangle-Attention_small.gif" width=20 height=20>'
                extra += '<img src="https://media0.giphy.com/media/W6AqdGRBUXxSw/giphy.gif" width=200 height=50>'

            elif 'nao cabe' in posicao.lower():
                extra += '<img src="http://www.netanimations.net/animated-roped-off-construction-barracades.gif" width=200 height=50>'
            # elif 'producao' in posicao:
            #     posicao += ' <img src="https://www.shopitcommerce.com/wp-content/uploads/2019/03/production-line-boxes.gif" width=200 height=30>'



            # set the font color of the path in the card, to make it easier to
            # identify what storage the job is in.
            if 'LIZARD' in disco:
                disco = '<font color="#959">'+disco+'</font>'
            elif 'MOOSE' in disco:
                disco = '<font color="#57A">'+disco+'</font>'
            elif 'smb' in disco:
                disco = '<font color="#994">'+disco+'</font>'
            else:
                disco = '<font color="#599">'+disco+'</font>'

            # now, we can add extra information that has being kept from the
            # card title, which was added at some point.
            if _decorrido:
                extra = '\n'.join([extra.strip(), _decorrido[0]])

            # construct card title string here
            title="**%s**" % os.path.basename(p)
            title+='\n>disco: **%s**' % disco
            title+="\ntamanho: **%s**" % size
            title+= last_modified
            title+="\nposicao: %s" % posicao
            title+="\n%s" % extra
            title+=""

            # if a card exists, edit it!
            if hasCard:
                if title.strip() != _card.data['title'].strip() or 1:

                    updateCard = True
                    # don't update card if the card already belongs to another LTO tape
                    # different from the one currently in the Tape!
                    if '/LTO' in disco:
                        if 'BKP' in _posicao and self.labelLTO not in _posicao:
                            updateCard = False

                    # update the card if true!
                    if updateCard:
                        if not _card.modify( title=title ):
                            print "Error updating card for %s!!" % p

            # or else create a new card
            else:
                for b  in self.api.get_user_boards('BACKUP'):
                    if '/LTO' in disco:
                        for l in b.get_cardslists(self.labelLTO):
                            l.add_card(title)
                    else:
                        for l in b.get_cardslists('JOBS'):
                            l.add_card(title)

    def updateLTOfreeSpaceCard(self):
        # update the free space available in free space card
        # of the list with the same name as the current inserted TAPE
        if self.labelLTO and self.ltoFreeSpace['free'] > 0:
            ltoList = [x for x in self.d['BACKUP'].keys() if self.labelLTO in x]
            # if the current TAPE name exists in the board as a list
            if ltoList:
                print self.labelLTO, self.ltoFreeSpace['free']
                list = self.d['BACKUP'][self.labelLTO][".class"]
                if 'BKP' in  list.title or 'EXT' in  list.title:
                    wbackup.updateListWithFreeSpace( self.labelLTO, self.ltoFreeSpace )



#
