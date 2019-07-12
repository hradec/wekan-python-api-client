#!/bin/python2

import sys, os, time
import wbackup

from pprint import pprint as pp
from glob import glob
import random, time
import os
import math

wbackup.runOnlyOnce( __file__ )


jobs = wbackup.jobCards()
for job in jobs.jobsOnDisk():
    # print job
    jobs.update( job )

# variables below only fill up after calling update on cards.
# list links that dont't exist anymore
if jobs.toRemove:
    print "\nThe following jobs don't exist:"
    for n in jobs.toRemove:
        print '\tsudo rm -f {:<40} #=> {:<12}'.format( n, os.readlink(n) )

# jobs that exist in multiple storages!!
if jobs.all_jobs.keys():
    print "\nThe following jobs exist on more than one path:"
    keys = jobs.all_jobs.keys()
    keys.sort()
    for n in keys:
        if len(jobs.all_jobs[n])>1:
            print '\t',n
            for r in jobs.all_jobs[n]:
                print '\t\t',r
            print

# jobs backed up and verified that can be deleted
if jobs.pode_apagar:
    print "\nThe following jobs are on the LTO tape and can be deleted:"
    for j in jobs.pode_apagar:
        print '\tsudo rm -rf %s' % j


print
