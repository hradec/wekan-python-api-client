#!/bin/python2

import sys, os, time
import wbackup

from pprint import pprint as pp
from glob import glob
import random, time
import os

wbackup.runOnlyOnce( __file__ )
api = wbackup.api()

cmd = 'date | tee -a /tmp/backup_%s.log ; rsync -avpP %s/ /LTO/%s/ | tee -a /tmp/backup_%s.log ; echo "return code: $?"'
check_log = 'ls /tmp/backup_%s.log'
check_cmd = 'tail -n 10 /tmp/backup_%s.log | grep "return code"'

# grab all cards form the weekan BACKUP board and store in hierarquical dict "d"
# and a cards dictionary
result = wbackup.getCards()
d     = result['data']
cards = result['cards']
jobs  = result['jobs']

# get the TAPE Label
labelLTO = wbackup.labelLTO()
hasTapeLTO = wbackup.hasTapeLTO()

# go over all cards that are waiting to be backed up!
if hasTapeLTO:
    for c in [ x for x in d['BACKUP'][labelLTO] if '.class' != x and ('esperando' in x or 'falta apagar' in x)]:
        card = d['BACKUP'][labelLTO][c]
        title = card.title.split('\n')
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
            backup = cmd % (bpath, path, bpath, bpath)
            doBackup = False

            exist = 'backup_%s.log' % bpath in  wbackup.sshLTO( check_log % bpath )
            if not exist:
                doBackup = True
            else:
                result = wbackup.sshLTO( check_cmd % bpath ).split(':')
                if not result[-1].strip() or int(result[-1]) != 0:
                    doBackup = True

            if doBackup:
                print 'backing up %s...' % bpath
                sys.stdout.flush()
                log = wbackup.sshLTO( backup )










#
