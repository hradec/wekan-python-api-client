
import sys, os, time

# force to use local wekanapi
sys.path.insert(0, os.path.dirname(__file__)+"/../src/" )
from wekanapi import WekanApi
from glob import glob

lto_ssh='ssh root@nexenta.local'

# generic function to connect to wekan
global _api
_api = None
def api():
    global _api
    if not _api:
        _api = WekanApi("http://192.168.0.16:8080/wekan", eval(''.join(open(os.path.dirname(__file__)+"/userpasswd.txt").readlines())), )
    return _api


# prevent script from run multiple times
# maxProcesses is default to 3, since crontab creates
# a cascade of 2 to 3 processes
def runOnlyOnce( file , maxProcesses=3 ):
    processes = os.popen("ps -AHfc | grep %s | grep -v grep | grep -v tail" % os.path.basename(file)).readlines()
    # print len(processes), processes
    if len( processes ) > maxProcesses:
    	print "Exiting... This script is already running..."
    	exit(0)

def convertHtoV( s ):
    s = s.replace('**','').split(':')[-1].strip()
    if not s:
        return 0.0
    mv = float(''.join([x for x in s if x.isdigit() or x=='.']))
    if 'M' in s.upper():
        mv = mv*1024
    elif 'G' in s.upper():
        mv = mv*1024*1024
    elif 'T' in s.upper():
        mv = mv*1024*1024*1024
    return mv

def convertVtoH( mv ):
    mv = float(mv)
    suffix = ''
    if mv > 1024*1024*1024:
        suffix = 'T'
        mv = mv / 1024.0 / 1024.0 / 1024.0
    elif mv > 1024*1024:
        suffix = 'G'
        mv = mv / 1024.0 / 1024.0
    elif mv > 1024:
        suffix = 'M'
        mv = mv / 1024.0

    return "%.1f%s" % (mv, suffix)


# run the command in the LTO machine!
def sshLTO( cmd ):
    return ''.join( os.popen( lto_ssh+''' '%s' 2>/dev/null''' % cmd ).readlines() ).strip()


# return the path of the job being backed up right now!
# returns '' if nothing is being backed up!
def runningLTO( lto_mount_path = '/LTO' ):
    ltoBackup = sshLTO( "pgrep -fa rsync.*%s" % lto_mount_path.strip('/') ).split('\n')
    if len(ltoBackup) > 1:
    	ltoBackup = ltoBackup[-1].split()[3].strip().rstrip('/')
    	# print "1 ===>", ltoBackup
    else:
    	ltoBackup = ''
    return ltoBackup

# returns the free space of the LTO tape current in the drive!
# return '' if no LTO tape inserted!
# (we use this detect if a tape is inserted!)
def freespaceLTO( lto_mount_path = '/LTO' ):
    ltoFreeSpace = sshLTO('df -h | grep %s' % lto_mount_path.strip('/')).split()
    if len(ltoFreeSpace) > 3:
    	ltoFreeSpace = ltoFreeSpace[-3]
        # print "2 ===>",ltoFreeSpace
    else:
    	ltoFreeSpace = ""
    return ltoFreeSpace

# return True if a tape is inserted and mounted in the LTO drive
def hasTapeLTO( lto_mount_path = '/LTO' ):
    return freespaceLTO( lto_mount_path ) != ''

# returns the tape root directory
def lsLTO( lto_mount_path = '/LTO' ):
    return [ '%s/%s' % (lto_mount_path, x.strip()) for x in sshLTO('ls -1 %s/' % lto_mount_path).split('\n') ]


# returns the tape label
def labelLTO( lto_mount_path = '/LTO' ):
    return sshLTO('attr -g ltfs.volumeName %s | grep -v Attribute' % lto_mount_path).split('\n')[-1]

# check rsync return code
def checkRsyncLogLTO( path ):
    check_cmd = 'grep "return code. 0" /tmp/backup_%s.log 2>/dev/null' % os.path.basename(path)
    return [ x for x in sshLTO(check_cmd).split('\n') if x.strip() ]


# grab all cards form the weekan BACKUP board and store in hierarquical dict "d"
# and a cards dictionary. Also return jobs!
# all data is returned in a dictionary with 'data', 'cards' and 'jobs' keys!
def getCards( board = 'BACKUP'):
    jobs = []
    d = {}
    cards = {}
    for b  in api().get_user_boards(board):
        d[b.title] = {}
        d[b.title][".class"] = b
        for list in b.get_cardslists():
            d[b.title][list.title] = {}
            d[b.title][list.title][".class"] = list
            for card in list.get_cards():
                d[b.title][list.title][card.title]=card
                jobs.append(card.title)
                cards[ card.title.split('\n')[0].replace("*","") ] = card
    return { 'data' : d, 'cards' : cards, 'jobs' : jobs }


# find all jobs is all paths, and return a dictionary with job names as keys
# and all paths for the job as a list.
def findAllJobs( ltoLS=[] ):
    if not ltoLS:
        ltoLS = lsLTO()

    # loop over jobs and update weekan cards with size and other info
    folders  = glob("/atomo/jobs/*")
    folders += glob("/.LIZARDFS/atomo/jobs/*")
    folders += glob("/.MOOSEFS/atomo/jobs/*")
    folders += glob("/smb/Backups-3ds/atomo/jobs/*")
    folders.sort()
    repetidos={}
    for p in folders+ltoLS:
    	p = os.path.abspath(p).replace('//','/').rstrip('/')
    	if os.path.islink(p):
    		p = os.readlink(p)
    	p = p.replace('//','/').rstrip('/')

    	if not os.path.exists(p) and not '/LTO' in p:
            continue
    	elif ( os.path.isdir(p) and not os.path.islink(p) ) or '/LTO' in p:
    		if os.path.basename(p) not in repetidos:
    			repetidos[ os.path.basename(p) ] = [p]
    		else:
    			if p not in repetidos[ os.path.basename(p) ]:
    				repetidos[ os.path.basename(p) ] += [p]
    			else:
    				continue
    return repetidos

# return the folders that are links and the links point to a non-existent
# folder!
def toRemove():
    # loop over jobs and update weekan cards with size and other info
    folders  = glob("/atomo/jobs/*")
    folders += glob("/.LIZARDFS/atomo/jobs/*")
    folders += glob("/.MOOSEFS/atomo/jobs/*")
    folders += glob("/smb/Backups-3ds/atomo/jobs/*")
    folders.sort()
    repetidos={}
    toRemove=[]
    for p in folders:
        if os.path.islink(p):
            if not os.path.exists(os.readlink(p)) and not '/LTO' in p:
                toRemove.append(p)
    return toRemove






#
