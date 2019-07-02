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
    'echo rsync -avpP %s/ /LTO/%s/ | tee -a /tmp/backup_%s.log',
    'rsync -avpP %s/ /LTO/%s/ | tee -a /tmp/backup_%s.log',
    'echo "return code: $?" | tee -a /tmp/backup_%s.log',
])
check_log = 'ls /tmp/backup_%s.log'

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


ltoSpaceAfter = ltoFreeSpace
for c in [ x for x in d['BACKUP'][labelLTO] if '.class' != x and ('esperando' in x or 'falta apagar' in x)]:
    card = d['BACKUP'][labelLTO][c]
    title = card.title.split('\n')
    size = [x for x in title if 'tamanho: ' in x]
    if size:
        size = wbackup.convertHtoV(size[0])
        ltoSpaceAfter -= size


# if we have a tape in the LTO and if there's nothing
# being copied to it...
if hasTapeLTO and not runningLTO:
    # go over all cards that are waiting to be backed up,
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
                size = wbackup.convertHtoV(size[0])
                if ltoFreeSpace-(size+1024*10) < 0:
                    print "%s won't fit in the lto tape currently loaded..." % bpath
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
                    print  bpath, len(result),  result
                    if not result[-1].strip() or int(result[-1].split(':')[-1]) != 0:
                        doBackup = True

                if doBackup:
                    backup = cmd % (
                        bpath,
                        path, bpath, bpath,
                        path, bpath, bpath,
                        bpath,
                    )
                    print 'backing up %s...' % bpath
                    sys.stdout.flush()
                    log = wbackup.sshLTO( backup )


else:
    print "Can't start backup now..."
    if runningLTO:
        print "Because there's a backup running at the moment already ( %s )..." % runningLTO
        print "Free space in the LTO after backing up the current cards: %s" %  wbackup.convertVtoH(ltoSpaceAfter)
    elif not hasTapeLTO:
        print "Because we don't have a tape in the LTO drive..."


sum = 0
for c in [ x for x in d['BACKUP'][labelLTO] if '.class' != x ]:
    card = d['BACKUP'][labelLTO][c]
    title = card.title.split('\n')
    size = [x for x in title if 'tamanho: ' in x]
    if size:
        size = wbackup.convertHtoV(size[0])
        sum += size
print "Total the todos os cards na coluna %s: %s" % (labelLTO, wbackup.convertVtoH(sum))








#
