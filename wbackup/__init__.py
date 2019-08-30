
import sys, os, time, math

# force to use local wekanapi
sys.path.insert(0, os.path.dirname(__file__)+"/../src/" )
from wekanapi import WekanApi
from glob import glob
from decimal import Decimal
from jobCards import jobCards

lto_ssh='ssh root@nexenta.local'

# time to start move command
move_delay = Decimal(60*60*1.45)

# time to start backup to lto command
backup_delay = 60*60*4


# generic function to connect to wekan
global _api
_api = None
def api():
    global _api
    if not _api:
        _api = WekanApi("http://192.168.0.37:8080/wekan", eval(''.join(open(os.path.dirname(__file__)+"/userpasswd.txt").readlines())), )
    return _api

# check if we have a moving happening already
def moving( source ):
    nprocs = pgrep( 'rsync.*%s' % source )
    # print source, nprocs
    if len(nprocs) > 0:
        return True
    return False



# return the number of proccess running
def pgrep( file ):
    cmd = "pgrep -fa '%s' | grep -v pgrep | grep -v tail" % file
    # print cmd
    return os.popen(cmd).readlines()

# prevent script from run multiple times
# maxProcesses is default to 3, since crontab creates
# a cascade of 2 to 3 processes
def runOnlyOnce( file , maxProcesses=3, echo=True ):
    processes = os.popen("ps -AHfc | grep %s | grep -v grep | grep -v tail" % os.path.basename(file)).readlines()
    # print len(processes), processes
    if echo:
        print ""
        print time.ctime()
        print "="*80
    if len( processes ) > maxProcesses:
        if echo:
    	       print "Exiting... %s is already running..." % file
    	exit(0)

# convert data size in Humam readable values to actual number of bytes.
# also converts % to values betwen 0.0 and 1.0(100%)
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
    elif '%' in s.upper():
        mv = mv/100.0
    return mv

# convert number of bytes to Humam readable values.
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

    ret = "%.1f%s" % (mv, suffix)
    ret = ret.replace('.0','')
    return ret

# run a command in another machine using ssh
# by default, it runs the command in a timeout of 600 (10 minutes)
# and ignores stderr.
def ssh( cmd , error='2>/dev/null', timeout=600):
    _cmd = ""
    if timeout:
        _cmd = "timeout %d " % timeout
    _cmd += lto_ssh+''' '%s' %s''' % (cmd,error)
    # print _cmd
    p = os.popen( _cmd )
    return ''.join( p.readlines() ).replace('\r','').strip()


# run the command in the LTO machine!
def sshLTO( cmd , error='2>/dev/null', timeout=120):
    return ssh( cmd, error, timeout )


# return the path of the job being backed up right now!
# returns '' if nothing is being backed up!
def runningLTO( lto_mount_path = '/LTO' ):
    # ltoBackup = sshLTO( "pgrep -fa rsync.*%s" % lto_mount_path.strip('/'), '2>/dev/null ; ERROR=$? ; [ $ERROR -gt 0 ] && echo ERROR $ERROR' ).split('\n')
    ltoBackup = sshLTO( "pgrep -fa rsync.*%s" % lto_mount_path.strip('/') ).split('\n')
    if 'ERROR' in ''.join(ltoBackup):
        ltoBackup = ''.join(ltoBackup)
    elif len(ltoBackup) > 1:
    	ltoBackup = ltoBackup[-1].split()[-2].strip().rstrip('/')
    else:
    	ltoBackup = ''
    print "1 ===>", ltoBackup
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

# get the number of files in the log for %
def countFilesRsyncLogLTO( path, lto_mount_path = '/LTO' ):
    bpath = os.path.basename(path)
    check_cmd = 'grep 100%% /tmp/backup_%s.log 2>/dev/null | wc -l ' % bpath
    # fromLog = float( sshLTO(check_cmd).strip() )
    # l='/tmp/%s.lto_file_count.log' % path.strip('/').replace('/','_')
    # if not os.path.exists(l) or ( ( time.time() - int(os.stat(l)[-1]) ) /60 /60 ) > 24  or  os.stat( l )[6] == 0:
    tmp = sshLTO('find %s/%s/ -type f 2>/dev/null | wc -l' % (lto_mount_path, bpath)).strip()
    print tmp
    fromFS = float( tmp )
    return fromFS

# get the number of files to create a % of done during backup (only for the current job being backed up)
# cache it every 24 hours
def jobFileCount( p ):
    lc='/tmp/%s.file_count.log' % p.strip('/').replace('/','_')
    # if os.path.basename(p) in ltoBackup:
    if not os.path.exists(lc) or ( ( time.time() - int(os.stat(lc)[-1]) ) /60 /60 ) > 24  or  os.stat( lc )[6] == 0:
        if '/LTO' in p:
            # calculate from the TAPE folder
            os.popen( wbackup.lto_ssh+''' "find %s -type f" | grep -v ':' | wc -l  2>/dev/null  >  %s ''' % ( p, lc ) )
        else:
            os.popen( "sudo find %s -type f | grep -v ':' | wc -l > %s " % ( p, lc ) )
    return float(''.join(open(lc).readlines()).strip())

# return a percentage of the job files that have
# being copied over to the tape
# def copiedPercentageLTO( p ):
#     return copiedPercentage( p, '/LTO/%s' % os.path.basename(p) )
def copiedPercentageLTO( p ):
    # create the log with the number of files in the job
    number_of_files = jobFileCount( p )
    # get the number of files in the backup, and calculate a
    # percentage with the wbackup.jobFileCound() above!
    perc = countFilesRsyncLogLTO( p ) / number_of_files
    # do a floor of the percentage * 100, so
    # to keep at least 2 decimal chars.
    # since floor() returns an int, convert to float
    # and divide by 100 to get the 'floored' 2 decimals.
    percentage = float(math.floor(perc*100.0*100.0))/100.0
    # save a timed log so we can calculate time to finish
    l = '/tmp/%s.timed_percentage.log' % p.strip('/').replace('/','_')
    f = open(l,'a')
    f.write('%s %s\n' % (Decimal(time.time()), Decimal(perc*100.0)))
    f.close()
    return percentage

# return a percentage of the job files that have
# being copied over to the target
def copiedPercentage( source, target, lto_mount_path = '/LTO' ):
    # create the log with the number of files in the job
    # get the number of files in the backup
    source_number_of_files = jobFileCount( source )
    if '/LTO' in target[0:5]:
        target_number_of_files = countFilesRsyncLogLTO( p )
    else:
        target_number_of_files = jobFileCount( target )
    # calculate a percentage with the wbackup.jobFileCound() above!
    perc = target_number_of_files / source_number_of_files
    # do a floor of the percentage * 100, so
    # to keep at least 2 decimal chars.
    # since floor() returns an int, convert to float
    # and divide by 100 to get the 'floored' 2 decimals.
    percentage = float(math.floor(perc*100.0*100.0))/100.0
    # save a timed log so we can calculate time to finish
    l = '/tmp/%s.timed_percentage.log' % source.strip('/').replace('/','_')
    f = open(l,'a')
    f.write('%s %s\n' % (Decimal(time.time()), Decimal(perc*100.0)))
    f.close()
    return percentage

# return a prediction of the amount of time remaining
# based on the percentage log for the job
def copyTimeToFinishLTO( p, returnAsString=False, deleteLog = False):
    copyTimeToFinish( p, returnAsString, deleteLog)

def copyTimeToFinish( p, returnAsString=False, deleteLog = False):
    l = '/tmp/%s.timed_percentage.log' % p.strip('/').replace('/','_')
    if deleteLog:
        os.remove( l )
    from datetime import timedelta
    ret = 0
    if returnAsString:
        ret = ''
    cmd = 'head -10 %s ; tail -n 10 %s' % (l,l)
    lines = os.popen(cmd).readlines()
    if len(lines) < 1:
        return (ret,ret)
    ztimes = {}
    ztimes2 = []
    for line in lines:
        line = line.strip().split(' ')
        perc = float(line[1])
        ztimes[perc]  = float(line[0])
        ztimes2 += [float(line[0])]

    ztimes2.sort()
    zperc = ztimes.keys()
    zperc.sort()
    tdiff = ztimes2[-1] - ztimes2[0]
    pdiff = zperc[-1] - zperc[0]
    if pdiff > 0.0:
        ret = ( (100.0-zperc[0]) / pdiff ) * tdiff
    else:
        ret = 99999999999999
    ret_simples = (tdiff/(zperc[-1]+0.00001)) * 100.0 - tdiff
    falso=''
    if ret_simples < ret:
        falso = ' (+-)'
        ret = ret_simples
    if returnAsString:
        return (
            str(timedelta(seconds=ret)).split('.')[0].replace('day','dia')+falso,
            str(timedelta(seconds=tdiff)).split('.')[0].replace('day','dia'),
        )
    return (ret, tdiff)


# check rsync return code
def checkRsyncLog( path, log='/tmp/move_%s.log' ):
    return checkRsyncLogLTO( path, lto_mount_path=None, log=log )

def checkRsyncLogLTO( path,  lto_mount_path='/LTO', log='/tmp/backup_%s.log'):
    check_cmd = 'grep "return code. 0" %s 2>/dev/null' % ( log % os.path.basename(path) )
    ret = []
    if lto_mount_path:
        ret =  [ x for x in sshLTO(check_cmd).split('\n') if x.strip() ]
    else:
        print check_cmd
        ret =  [ x for x in os.popen(check_cmd) if x.strip() ]
    return ret

# check rsync log and try to detect error in backup.
def checkRsyncLog4Errors( path, log=None, log_path='/tmp/move_%s.log' ):
    return checkRsyncLog4ErrorsLTO( path, log=log, lto_mount_path = None, log_path=log_path)

def checkRsyncLog4ErrorsLTO( path, log=None, lto_mount_path = '/LTO', log_path='/tmp/backup_%s.log' ):
    label=''
    if lto_mount_path:
        label = labelLTO(lto_mount_path)
    lines = []
    msg = ''
    if not log:
        log_path = log_path % os.path.basename(path)
        check_cmd = 'tail -n 20  %s 2>/dev/null' % log_path
        if lto_mount_path:
            log = sshLTO(check_cmd)
        else:
            log = ''.join(os.popen(check_cmd).readlines())
    log = [ x.strip() for x in log.split('\n') if x.strip() ]

    if len(log) > 5:
        error = 0
        if 'NO SPACE LEFT ON TAPE %s' % label in log[-1]:
            error = 100
        elif 'return code: 0' not in log[-1]:
            error = 1

        if 'total size is' not in log[-2]:
            error = 2
        elif 'sent' not in log[-3]:
            error = 3
        elif 'sending incremental file list' not in log[-4]:
            error = 4
            count = -4
            while True:
                if abs(count)>len(log) or abs(count)>8:
                    break
                l = log[count]
                if 'sending incremental file list' in l:
                    break
                lines += [l]
                count -= 1
            lines.reverse()

        if error >= 100:
            msg = '**JOB NAO CABE NA FITA\nREMOVA O CARTAO DA LISTA %s**' % label
        elif error > 0:
            if len(checkRsyncLogLTO( path, lto_mount_path )) <= 1:
                return msg
            msg = '**ERRO NO LOG DE BACKUP(%s)...**\n/tmp/backup_%s.log\nO sistema vai tentar novamente...\n' % (error,os.path.basename(path)) #+'\n'.join(log)
            if lines:
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

def checkIfFits( target_path, size_string ):
    pathSpace = freeSpace(target_path)
    size = convertHtoV(size_string)
    if pathSpace['free']-(size+1024*10) < 0:
        return False
    return True



# grab all cards form the weekan BACKUP board and store in hierarquical dict "d"
# and a cards dictionary. Also return jobs!
# all data is returned in a dictionary with 'data', 'cards' and 'jobs' keys!
global _getCards_result
_getCards_result = { 'data' : {}, 'cards' : {}, 'jobs' : [] }
def getCards( board = 'BACKUP' ):
    global _getCards_result
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
    _getCards_result = { 'data' : d, 'cards' : cards, 'jobs' : jobs }
    return _getCards_result


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

# return free disk space available
def freeSpace( path, lto_mount_path = '/LTO' ):
    df = {
        'free' : 0.0,
        'used' : 0.0,
        'size' : 0.0,
        'free%' : 0.0,
        'used%' : 0.0,
    }
    if lto_mount_path in path[0:6]:
        _free = sshLTO("df -h %s | grep -v Filesystem" % path)
    else:
        _free = ''.join(os.popen( "timeout 30 df -h %s | grep -v Filesystem" % path).readlines()).strip()
    if _free:
        df['free'] = convertHtoV(_free.split()[-3])
        df['used'] = convertHtoV(_free.split()[-4])
        df['size'] = convertHtoV(_free.split()[-5])
        df['used%'] = convertHtoV(_free.split()[-2])
        df['free%'] = 1.0 - df['used%']
    return df

# create/update a free space card in the given list
def updateListWithFreeSpace( list_name, zfree, getCards_result=None ):
    global _getCards_result
    if not getCards_result:
        getCards_result = _getCards_result
    d     = getCards_result['data']
    cards = getCards_result['cards']
    jobs  = getCards_result['jobs']
    list = d['BACKUP'][list_name][".class"]
    b = list.board
    free = convertVtoH( zfree['free'] )
    size = convertVtoH( zfree['size'] )
    # print zfree
    if zfree['free%'] < 0.2:
        free = '<font color="red">%s</font>' % free
    elif zfree['free%'] < 0.35:
        free = '<font color="orange">%s</font>' % free
    else:
        free = '<font color="green">%s</font>' % free

    percentage = float(math.floor(zfree['free%']*100.0*100.0))/100.0
    label = list.title.split()[-1]
    if 'JOBS' in label:
        label = '/atomo/jobs'
    title = "**%s - %s de %s livre %d%%**" % ( label, free, size, percentage )

    spaceCard = [ x for x in d[b.title][list.title].keys() if ' livre ' in x.split('\n')[0].lower() ]
    if spaceCard:
        if title != cards[spaceCard[0].replace('*','')].data['title']:
            cards[spaceCard[0].replace('*','')].modify( title=title )
    else:
        list.add_card( title )


# gather information about storages and update the storage free space card
# in the lists.
storages = {
    'LIZARD' : '/.LIZARDFS',
    'MOOSE'  : '/.MOOSEFS',
    #'BEEGFS' : '/.BEEGFS',
    'JOBS'   : '/atomo/jobs',
}
def getStoragesInfo( getCards_result=None ):
    global _getCards_result
    if not getCards_result:
        getCards_result = _getCards_result
    d     = getCards_result['data']
    cards = getCards_result['cards']
    jobs  = getCards_result['jobs']
    # get free space
    zpath = storages
    zfree = {
        'LIZARD' : freeSpace( zpath['LIZARD'] ),
        'MOOSE'  : freeSpace( zpath['MOOSE'] ),
#        'BEEGFS' : freeSpace( zpath['BEEGFS'] ),
        'JOBS'   : freeSpace( zpath['JOBS'] ),
    }
#    if not zfree['BEEGFS']['free']:
#        zfree['BEEGFS'] = freeSpace( '/mnt/beegfs' )

    zpath_list = {}
    zpath_free = {}
    for l in zfree:
        _l = [ x for x in d['BACKUP'].keys() if l in x ]
        if _l:
            zpath_list[_l[0].strip().split()[-1]] = zpath[l]
            zpath_free[_l[0].strip().split()[-1]] = zfree[l]
            updateListWithFreeSpace( _l[0], zfree[l] )

    return { 'path' : zpath_list, 'free' : zpath_free }




#
