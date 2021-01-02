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
    '''echo rsync -avpP --exclude "'*:*'" --inplace %s/ %s/ | egrep -v "/$" | tee -a /tmp/move_%s.log ''',
    '''sudo rsync -avpP --exclude "'*:*'" --inplace %s/ %s/ | egrep -v "/$" | tee -a /tmp/move_%s.log && echo "return code: $?" | tee -a /tmp/move_%s.log''',
])
check_log = 'ls /tmp/move_%s.log'

# new class which holds all cards for all jobs,
# and can update single cards
jobs = wbackup.jobCards()
alljobs = wbackup.findAllJobs()

def rsync( source, target ):
    card = os.path.basename(source)
    print source, target, card, cmd
    _cmd = cmd % (
        card,
        source, target, card,
        source, target, card, card
    )
    # check if rsync is already running
    print "backup %s to %s" % (source, target)
    if not wbackup.moving( '/tmp/move_.*.log' ):
        os.system(_cmd)



# storages
for storage in wbackup.storages:
    if not 'JOBS' in storage:
      if 'LIZARD' in storage or 'BTRFS10TB' in storage:
        for list in [ x for x in jobs.lists() if storage in x ]:
            cards = jobs.lists()[list]
            for card in cards:
                print card, len(alljobs[card])
                log = '/tmp/move_%s.log' % card

                source = cards[card].attr['path']
                target = '/'.join([ wbackup.storages[storage], 'atomo', source.split('atomo')[-1] ])
                target = target.replace('//','/')


                # if the job exists only in one storage, check if it fits
                if len(alljobs[card])<2:
                  print source, target, source == target
                  if source == target:
                      if os.path.exists( log ):
                          os.system('mkdir -p /tmp/move_log_archive/')
                          os.system('mv %s /tmp/move_log_archive/' % log)
                          #os.remove( log )
                      continue
                  else:
                    fit = wbackup.checkIfFits(
                        # cards[card].attr['disco'],
                        wbackup.storages[storage],
                        cards[card].attr['tamanho']
                    )
                    if not fit:
                        print card, "won't fit in", list
                        os.system( 'echo "NO SPACE LEFT" | tee -a '+log )
                        continue

                startTime = ''
                if os.path.exists(log):
                    startTime = ''.join( os.popen( 'cat %s | grep START_TIME:' % log).readlines() ).strip().split(':')[-1]

                if startTime:
                    startTime = Decimal(startTime)

                if not startTime:
                    startTime = Decimal(time.time())
                    os.system( 'echo "START_TIME: %s" > %s' % (startTime, log) )
                elapsed = Decimal(time.time()) - startTime

                if elapsed > wbackup.move_delay:
                    # check log file in the LTO machine to see if rsync was DONE
                    # susscessfully!
                    result = wbackup.checkRsyncLog( source )
                    # if file not exist or there no susccessfull runs...
                    doBackup = False
                    if not result:
                        doBackup = True
                    # if there's less than 4 susccessfull runs...
                    elif len(result) <= 4:
                        doBackup = True
                    elif wbackup.checkRsyncLog4Errors( source ):
                        #wbackup.removeRsyncLogLTO( path )
                        doBackup = True

                    if doBackup:
                        rsync( source, target )
                    else:
                        print 'verificado %d vezes.' % len( result )
			if len(result)>=5:
				source_path = os.path.dirname(source.rstrip('/'))
				target_path = os.path.dirname(target.rstrip('/'))
				if source_path != target_path:
					_cmd = [
						"mv %s %s/.deleted/" % (source, source_path),
						"ln -s %s %s" % (target, source)
					]
					_cmd=' && '.join(_cmd)
					print _cmd








#
