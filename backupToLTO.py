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
    '''echo rsync -avpP --exclude "'*:*'" %s/ /LTO/%s/ | egrep -v "/$" | tee -a /tmp/backup_%s.log''',
    '''rsync -avpP --exclude "'*:*'" %s/ /LTO/%s/ | egrep -v "/$" | tee -a /tmp/backup_%s.log''',
    'echo "return code: $?" | tee -a /tmp/backup_%s.log',
])
check_log = 'ls /tmp/backup_%s.log'

# new class which holds all cards for all jobs,
# and can update single cards
jobs = wbackup.jobCards()

# grab all cards form the weekan BACKUP board and store in hierarquical dict "d"
# and a cards dictionary
result = wbackup.getCards()
d     = result['data']
cards = result['cards']
jobs  = result['jobs']

# get the TAPE Label
labelLTO = wbackup.labelLTO()
hasTapeLTO = wbackup.hasTapeLTO()
runningLTO = wbackup.runningLTO()
ltoFreeSpace = wbackup.convertHtoV(wbackup.freespaceLTO())
ltoLS = wbackup.sshLTO( 'ls -l /LTO/', timeout=30 )

ltoSpaceAfter = ltoFreeSpace
if labelLTO:
    for c in [ x for x in d['BACKUP'][labelLTO] if '.class' != x and ('esperando' in x or 'falta apagar' in x)]:
        card = d['BACKUP'][labelLTO][c]
        title = card.title.split('\n')
        size = [x for x in title if 'tamanho: ' in x]
        if size:
            size = wbackup.convertHtoV(size[0])
            ltoSpaceAfter -= size


# if we have a tape in the LTO and if there's nothing
# being copied to it... (if it can't connect to the lto server,
# runningLTO will have ERROR in it, so it won't run as well.)
print '========>',runningLTO
if hasTapeLTO and not runningLTO:
    # go over all cards that are waiting to be backed up,
    # in the list with the same name as the loaded TAPE
    for c in [ x for x in d['BACKUP'][labelLTO] if '.class' != x and ('esperando' in x or 'pode apagar' in x)]:
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


            # if path is not /LTO...
            doBackup = False
            if '/LTO' not in path:
                # check log file in the LTO machine to see if rsync was DONE
                # susscessfully!
                result = wbackup.checkRsyncLogLTO( path )
                # if file not exist or there no susccessfull runs...
                if not result:
                    doBackup = True

                    if os.path.basename(path) not in str(ltoLS):
                        # check if it fits in the current loaded tape...
                        size = [x for x in title if 'tamanho: ' in x]
                        if size:
                           if not wbackup.checkIfFitsLTO(path, size[0]):
                             doBackup = False
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
                    log = wbackup.sshLTO( backup, timeout=0, error='2>&1' )
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
