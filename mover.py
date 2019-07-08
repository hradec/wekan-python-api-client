#!/bin/python2

import sys, os, time
import wbackup

from pprint import pprint as pp
from glob import glob
import random, time
import os

wbackup.runOnlyOnce( __file__ )
api = wbackup.api()

cmd = ';'.join([
    'date | tee -a /tmp/backup_%s.log',
    "echo rsync -avpP --exclude '*:*' %s/ /LTO/%s/ | tee -a /tmp/backup_%s.log",
    'rsync -avpP --exclude \'*:*\' %s/ /LTO/%s/ | egrep -v "/$" | tee -a /tmp/backup_%s.log',
    'echo "return code: $?" | tee -a /tmp/backup_%s.log',
])
check_log = 'ls /tmp/move_%s.log'

# grab all cards form the weekan BACKUP board and store in hierarquical dict "d"
# and a cards dictionary
result = wbackup.getCards()
d     = result['data']
cards = result['cards']
jobs  = result['jobs']



storages = wbackup.getStoragesInfo()
zpath_list = storages['path']
zpath_free = storages['free']



# go over the "MOVER PARA " lists - the LTO
for _l in [ x for x in d['BACKUP'].keys() if 'MOVER PARA' in x and 'LTO' not in x ]:
    # now pull the cards
    for c in [ x for x in d['BACKUP'][_l] if '.class' != x and ' livre ' not in x ]:
        card = d['BACKUP'][_l][c]
        title = card.title.split('\n')

        # keep data that is in the card title
        _disco      = [ x for x in title if 'disco' in x ]
        _decorrido  = [ x for x in title if 'decorrido' in x ]
        _modificado	= [ x for x in title if 'modificado' in x ]
        _tamanho	= [ x for x in title if 'tamanho' in x ]

        path = ''
        size = 0

        if _disco:
            print title[0], zpath_list[_l], _disco[0]
            if zpath_list[_l] in _disco[0]:
                print '\tAlready in %s' % zpath_list[_l]
            else:
                print '\tNot in %s' % zpath_list[_l]

            path = '%s/%s' % (
                _disco[0].split(':')[-1].strip(),
                title[0].replace('**', '')
            )

        if _tamanho:
            size = wbackup.convertHtoV( _tamanho[0].split(':')[-1].strip() )

            if zpath_free[_l]['free'] - size > 0:
                print "Job fits in the storage..."
            else:
                print "Job won't fit in the storage..."







sys.exit(0)


# if we have a tape in the LTO and if there's nothing
# being copied to it...
if hasTapeLTO and not runningLTO:
    # go over all cards that are waiting to be backed up,
    # in the list with the same name as the loaded TAPE
    for c in [ x for x in d['BACKUP'][labelLTO] if '.class' != x and ('esperando' in x or 'falta apagar' in x)]:
        card = d['BACKUP'][labelLTO][c]
        title = card.title.split('\n')

        # grab job path
        path = [x for x in title if 'disco: ' in x]
        if path:
            path = path[0].replace('disco: ','').replace('**','').strip('>')
            if '>/' in path:
                path = '/'.join([
                    '',
                    path.split('>/')[1].split('</')[0],
                    title[0].replace('**','')
                ])
            bpath = os.path.basename(path)

            # check if it fits in the current loaded tape...
            size = [x for x in title if 'tamanho: ' in x]
            if size:
                if not wbackup.checkIfFitsLTO(path, size[0]):
                    continue

            # if path is not /LTO...
            doBackup = False
            if '/LTO' not in path:
                # check log file in the LTO machine to see if rsync was DONE
                # susscessfully!
                result = wbackup.checkRsyncLogLTO( path )
                # if file not exist or there no susccessfull runs...
                if not result:
                    doBackup = True
                # if there's less than 4 susccessfull runs...
                elif len(result) < 4:
                    doBackup = True
                elif wbackup.checkRsyncLog4ErrorsLTO( path ):
                    wbackup.removeRsyncLogLTO( path )
                    doBackup = True

                if doBackup:
                    backup = cmd % (
                        bpath,
                        path, bpath, bpath,
                        path, bpath, bpath,
                        bpath,
                    )
                    print 'backing up %s...' % bpath,
                    sys.stdout.flush()
                    log = wbackup.sshLTO( backup )
                    print wbackup.checkRsyncLog4ErrorsLTO( path, log ),
                    print 'verificado %d vezes.' % len( wbackup.checkRsyncLogLTO( path ) )


else:
    print "Can't start backup now..."
    if runningLTO:
        print "Because there's a backup running at the moment already ( %s )..." % runningLTO
        print "Free space in the LTO after backing up the current cards: %s" %  wbackup.convertVtoH(ltoSpaceAfter)
    elif not hasTapeLTO:
        print "Because we don't have a tape in the LTO drive..."


if hasTapeLTO:
    sum = 0
    for c in [ x for x in d['BACKUP'][labelLTO] if '.class' != x ]:
        card = d['BACKUP'][labelLTO][c]
        title = card.title.split('\n')
        size = [x for x in title if 'tamanho: ' in x]
        if size:
            size = wbackup.convertHtoV(size[0])
            sum += size
    print "Total the todos os cards na coluna %s: %s" % (labelLTO, wbackup.convertVtoH(sum))

    # update wekan!!
    os.system("%s/updateBackupBoard.py" % os.path.dirname(__file__))






#
