#!/bin/python2

import sys, os, time
import wbackup

from pprint import pprint as pp
from glob import glob
import random, time
import os
import math
from multiprocessing import Pool


wbackup.runOnlyOnce( __file__ )


jobs = wbackup.jobCards()
# update free space card for the BKP list of the inserted tape!
jobs.updateLTOfreeSpaceCard()
# now go over all jobs os available storages and update the correspondent cards!
if 0:
    # single thread version
    for job in jobs.jobsOnDisk():
        jobs.update( job )
else:
    # multithreaded version
    j = jobs.jobsOnDisk()
    j.sort()
    def jobs_update( n ):
    	print n
    	try:
        	jobs.update( n )
    	except:
    		print "ERROR : ",n
    	return (jobs.toRemove, jobs.pode_apagar)

    jobs.toRemove=[]
    jobs.pode_apagar=[]
    p = Pool(20)
    for each in p.map( jobs_update, j ):
    	jobs.toRemove += each[0]
    	jobs.pode_apagar += each[1]

jobs.toRemove = list(set(jobs.toRemove))
jobs.pode_apagar = list(set(jobs.pode_apagar))

# variables below only fill up after calling update on cards.
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

# list links that dont't exist anymore
if jobs.toRemove:
    print "\nThe following jobs are links and they don't exist where the link points to:"
    for n in jobs.toRemove:
        print '\tsudo rm -f {:<40} #=> {:<12}'.format( n, os.readlink(n) )


# jobs backed up and verified to LTO that can be deleted
if jobs.pode_apagar:
    print "\nThe following jobs are on the LTO tape and can be deleted:"
    for j in jobs.pode_apagar:
        inLTO = [ x for x in jobs.all_jobs[os.path.basename(j)] if '/LTO' in x[0:12] ]
        if inLTO:
            print '\tsudo rm -rf %s' % j

# jobs backed up and verified to another storage that can be deleted
if jobs.pode_apagar:
    print "\nThe following jobs are on another storage, and can be deleted:"
    for j in jobs.pode_apagar:
        if '/atomo/jobs' in j[0:12]:
            deleted = '/atomo/jobs/.deleted_jobs/'
            for another in [ x for x in jobs.all_jobs[os.path.basename(j)] if '/atomo/jobs' not in x[0:12] ]:
                if '/LTO' not in  another:
                    print '\tsudo mv %s\t %s  && sudo ln -s %s\t/atomo/jobs/' % (j, deleted, os.path.dirname(another)+'/'+os.path.basename(j) )


print
