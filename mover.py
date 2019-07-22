#!/bin/python2

import sys, os, time
import wbackup

from pprint import pprint as pp
from decimal import Decimal
from glob import glob
import random, time
import os

wbackup.runOnlyOnce( __file__ )


cmd = ' ; '.join([
    'date | tee -a /tmp/move_%s.log',
    '''echo rsync -avpP --exclude "'*:*'" %s/ %s/ | egrep -v "/$" | tee -a /tmp/move_%s.log''',
    '''sudo rsync -avpP --exclude "'*:*'" %s/ %s/ | egrep -v "/$" | tee -a /tmp/move_%s.log''',
    'echo "return code: $?" | tee -a /tmp/move_%s.log',
])
check_log = 'ls /tmp/move_%s.log'

# new class which holds all cards for all jobs,
# and can update single cards
jobs = wbackup.jobCards()

def rsync( source, target ):
    card = os.path.basename(source)
    _cmd = cmd % (
        card,
        source, target, card,
        source, target, card,
        card
    )
    # check if rsync is already running
    if not wbackup.moving( '/tmp/move_.*.log' ):
        print os.popen(_cmd).readlines()



# storages
for storage in wbackup.storages:
    if not 'JOBS' in storage:
      if 'LIZARD' in storage:
        for list in [ x for x in jobs.lists() if storage in x ]:
            cards = jobs.lists()[list]
            for card in cards:
                log = '/tmp/move_%s.log' % card
                fit = wbackup.checkIfFits(
                    cards[card].attr['disco'],
                    cards[card].attr['tamanho']
                )
                if not fit:
                    print card, "won't fit in", list
                    os.system( 'echo "NO SPACE LEFT" | tee -a '+log )
                    continue

                if os.path.exists(log):
                    startTime = ''.join( os.popen( 'cat %s | grep START_TIME:' % log).readlines() ).strip().split(':')[-1]
                    startTime = Decimal(startTime)
                else:
                    startTime = Decimal(time.time())
                    os.system( 'echo "START_TIME: %s" > %s' % (startTime, log) )
                elapsed = Decimal(time.time()) - startTime

                source = cards[card].attr['path']
                target = '/'.join([ wbackup.storages[storage], source ])
                target = target.replace('//','/')
                if elapsed > wbackup.move_delay:
                    rsync( source, target )








#
