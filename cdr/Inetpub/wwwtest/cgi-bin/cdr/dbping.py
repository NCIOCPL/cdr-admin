############
# CGI script invoked by the Big Brother system monitor to determine if
# the CDR database is up and responding properly.
#
# If error, reports to default log file (debug.log) and to web client.
#
# $Id: dbping.py,v 1.1 2008-08-07 19:39:29 ameyer Exp $
#
# $Log: not supported by cvs2svn $
############
import cdr, cdrdb

def report(what):
    print """\
Content-type: text/plain

CDR DATABASE %s""" % what

# Uncomment if we need to show it's being called
# cdr.logwrite("dbping called")
try:
    cursor = cdrdb.connect('CdrGuest').cursor()
    cursor.execute("SELECT COUNT(*) FROM document", timeout = 10)
    count = cursor.fetchall()[0][0]
    if not count:
        cdr.logwrite("dbping: doc count=%s, returning 'CORRUPT'" % count)
    report(count and "OK" or "CORRUPT")
except Exception, e:
    cdr.logwrite("dbping: caught exception type=%s  value=%s" %
                 (type(e), e))
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
            cdr.logwrite("dbping: blockers=\n%s" % rows)
            report("UNAVAILABLE; BLOCKER(S):\n%s" % rows)
        else:
            cdr.logwrite("dbping: no blockers")
            report("UNAVAILABLE; NO BLOCKERS")
    except Exception, e:
        cdr.logwrite("dbping: caught secondary exception type=%s  value=%s" %
                     (type(e), e))
        report("UNAVAILABLE")
    except:
        cdr.logwrite("dbping: caught unknown exception")
        report("UNAVAILABLE")
