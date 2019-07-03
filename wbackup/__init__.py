
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
def sshLTO( cmd , error='2>/dev/null'):
    return ''.join( os.popen( lto_ssh+''' '%s' %s''' % (cmd,error) ).readlines() ).strip()


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

# check rsync log and try to detect error in backup.
def checkRsyncLog4ErrorsLTO( path, log=None, lto_mount_path = '/LTO' ):
    label = labelLTO(lto_mount_path)
    lines = []
    msg = ''
    if not log:
        check_cmd = 'tail -n 20  /tmp/backup_%s.log 2>/dev/null' % os.path.basename(path)
        log = sshLTO(check_cmd)
    log = [ x.strip() for x in log.split('\n') if x.strip() ]

    if len(checkRsyncLogLTO( path ))<=1:
        return msg

    if log:
        error = 0
        if 'NO SPACE LEFT ON TAPE %s' % label in log[-1]:
            error = 100
        elif 'return code: 0' not in log[-1]:
            error = 1
        elif 'total size is' not in log[-2]:
            error = 2
        elif 'sent' not in log[-3]:
            error = 3
        elif 'sending incremental file list' not in log[-4]:
            error = 4
            count = -4
            while True:
                if abs(count)>len(log):
                    break
                l = log[count]
                if 'sending incremental file list' in l:
                    break
                lines += [l]
                count -= 1

        if error >= 100:
            msg = '**JOB NAO CABE NA FITA\nREMOVA O CARTAO DA LISTA %s**' % label
        elif error > 0:
            msg = '**ERRO NO LOG DE BACKUP(%s)...**\n/tmp/backup_%s.log\nO sistema vai tentar novamente...\n' % (error,os.path.basename(path)) #+'\n'.join(log)
            msg += '\n'.join(lines)
    return msg

# remove a log file
def removeRsyncLogLTO( path ):
    cmd = 'rm -rf  /tmp/backup_%s.log 2>/dev/null' % os.path.basename(path)
    return sshLTO(cmd)

# check if a job fits in the tape or not
# pass the tamanho: string from the title and the func will do the rest
# if it doesn't fit, add a message to the backup log so we can
# update the wekan card with this info!
def checkIfFitsLTO( path, size_string, lto_mount_path = '/LTO' ):
    ltoFreeSpace = convertHtoV(freespaceLTO(lto_mount_path))
    size = convertHtoV(size_string)
    bpath = os.path.basename(path)
    if ltoFreeSpace-(size+1024*10) < 0:
        print "%s won't fit in the lto tape currently loaded..." % bpath
        sshLTO( 'echo "NO SPACE LEFT ON TAPE %s: %s - %s = %s" | tee -a /tmp/backup_%s.log' % (
            labelLTO(lto_mount_path),
            ltoFreeSpace,
            (size+1024*10),
            ltoFreeSpace-(size+1024*10),
            bpath
        ) )
        return False
    return True




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

        if os.path.basename(p) == 'LTO':
            continue
    	elif not os.path.exists(p) and not '/LTO' in p:
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
