############
# CGI script invoked by the Big Brother system monitor to determine if
# the CDR database is up and responding properly.
#
# If error, reports to default log file (debug.log) and to web client.
#
# $Id: dbping.py,v 1.2 2009-03-31 21:59:18 ameyer Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2008/08/07 19:39:29  ameyer
# Version modified to include logging.
#
############
import os, subprocess, cdr, cdrdb

LF             = cdr.DEFAULT_LOGDIR + "/dbping.log"
ERR_STATE_FILE = cdr.DEFAULT_LOGDIR + "/dbpingErrFlag"

def report(what):
    print """\
Content-type: text/plain

CDR DATABASE %s""" % what


def errState(errOn):
    """
    Check and, if necessary, manipulate the ERR_STATE_FILE.

    Pass:
        errOn - True  = Error, create the file if it doesn't exist.
                False = No error, remove the file if it exists.

    Return:
        Previous state before this call.
    """
    oldErrState = os.path.exists(ERR_STATE_FILE)
    if errOn:
        if not oldErrState:
            # File doesn't exist but needs to, create it
            try:
                fp = file(ERR_STATE_FILE, "w")
                fp.close()
            except IOError, info:
                cdr.logwrite("Error creating state file: %s" % str(info), LF)
    else:
        if oldErrState:
            # File exists, but should not exist now
            try:
                os.remove(ERR_STATE_FILE)
            except IOError, info:
                cdr.logwrite("Error removing state file: %s" % str(info), LF)

    # Tell caller what we had
    return oldErrState


def saveTaskList(msg):
    """
    Write information about the current state of the system to a log
    file.  Used when errors occur and when we recover from them.

    Pass:
        msg - Message to associate with this invocation.
    """
    # Execute an external program to see what's going on, capture output
    subproc = subprocess.Popen("tasklist", stdout=subprocess.PIPE)
    output  = subproc.stdout.read()

    cdr.logwrite("\n%s\n%s\n" % (msg, output), LF)


# Uncomment if we need to show it's being called
# cdr.logwrite("dbping called")
try:
    cursor = cdrdb.connect('CdrGuest').cursor()
    cursor.execute("SELECT COUNT(*) FROM document", timeout = 30)
    # raise Exception("Testing 1234")
    count = cursor.fetchall()[0][0]
    if not count:
        cdr.logwrite("dbping: doc count=%s, returning 'CORRUPT'" % count, LF)
    report(count and "OK" or "CORRUPT")
except Exception, e:
    # Remember between runs that an error occurred on this run
    errState(True)

    # Record the current task environment
    saveTaskList("dbping: caught exception type=%s  value=%s" %
                 (type(e), e))

    # Check for database blockers
    try:
        cursor.execute("""\
         SELECT p.spid, p.waittime, p.lastwaittype, p.waitresource, p.dbid,
                p.uid, p.cpu, p.physical_io, p.memusage, p.login_time,
                p.last_batch, p.ecid, p.open_tran, p.status, p.hostname,
                p.program_name, p.hostprocess, p.cmd, p.nt_domain,
                p.nt_username, p.net_address, p.net_library, p.loginame
           FROM master..sysprocesses p
          WHERE p.blocked = 0
            AND p.spid IN (SELECT blocked
                           FROM master..sysprocesses)""") #, timeout = 300)
        rows = cursor.fetchall()
        if rows:
            cdr.logwrite("dbping: blockers=\n%s" % rows, LF)
            report("UNAVAILABLE; BLOCKER(S):\n%s" % rows)
        else:
            cdr.logwrite("dbping: no blockers", LF)
            report("UNAVAILABLE; NO BLOCKERS")
    except Exception, e:
        cdr.logwrite("dbping: caught secondary exception type=%s  value=%s" %
                     (type(e), e), LF)
        report("UNAVAILABLE")
    except:
        cdr.logwrite("dbping: caught unknown exception", LF)
        report("UNAVAILABLE")

else:
    # No error this time.  Be sure remembered error state is off
    prevErrState = errState(False)

    # If it just now flipped from on to off, save a task list
    if prevErrState:
        saveTaskList("Saving task list after error recovery")
