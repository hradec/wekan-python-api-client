
import sys, os, time

# force to use local wekanapi
sys.path.insert(0, os.path.dirname(__file__)+"/../src/" )
from wekanapi import WekanApi

# generic function to connect to wekan
def api():
    return WekanApi("http://192.168.0.16:8080/wekan", eval(''.join(open(os.path.dirname(__file__)+"/userpasswd.txt").readlines())), )


# prevent script from run multiple times
# maxProcesses is default to 3, since crontab creates
# a cascade of 2 to 3 processes
def runOnlyOnce( file , maxProcesses=3 ):
    processes = os.popen("ps -AHfc | grep %s | grep -v grep | grep -v tail" % os.path.basename(file)).readlines()
    print len(processes), processes
    if len( processes ) > maxProcesses:
    	print "exiting... too many processess!"
    	exit(0)
