#----------------------------------------------------------------------
# Show SQL Server processes which are blocked or are blocking.
#----------------------------------------------------------------------
import cdr, cdrdb, socket, time, sys, cdrcgi

#----------------------------------------------------------------------
# Collect some values we'll need for the entire run.
#----------------------------------------------------------------------
host   = socket.gethostname()
conn   = cdrdb.connect()
cursor = conn.cursor()
LOG    = cdr.DEFAULT_LOGDIR + "/blocking.log"

#----------------------------------------------------------------------
# Object which keeps track of a process which blocks other processes.
#----------------------------------------------------------------------
class Process:
    def __init__(self, row):
        self.spid         = row[ 0]
        self.waitTime     = row[ 1]
        self.lastWaitType = row[ 2]
        self.waitResource = row[ 3]
        self.db           = row[ 4]
        self.uid          = row[ 5]
        self.cpu          = row[ 6]
        self.physicalIO   = row[ 7]
        self.memUsage     = row[ 8]
        self.loginTime    = row[ 9]
        self.lastBatch    = row[10]
        self.ecid         = row[11]
        self.openTrans    = row[12]
        self.status       = row[13]
        self.hostName     = row[14]
        self.programName  = row[15]
        self.hostProcess  = row[16]
        self.cmd          = row[17]
        self.ntDomain     = row[18]
        self.ntUserName   = row[19]
        self.netAddress   = row[20]
        self.netLibrary   = row[21]
        self.loginName    = row[22]
        self.blockedBy    = row[23]

    #------------------------------------------------------------------
    # Convert the object to a human-readable string representation.
    #------------------------------------------------------------------
    def toHtml(self):
        return u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
""" % (fix(self.spid), fix(self.blockedBy),
       fix(self.waitTime), fix(self.lastWaitType),
       fix(self.waitResource), fix(self.cpu), fix(self.physicalIO),
       fix(self.memUsage), fix(self.db), fix(self.uid), fix(self.loginName),
       fix(self.ntUserName), fix(self.ntDomain), fix(self.hostName),
       fix(self.programName), fix(self.hostProcess),
       fix(self.cmd), fix(self.netAddress), fix(self.netLibrary),
       fix(self.loginTime), fix(self.lastBatch),
       fix(self.ecid), fix(self.openTrans), fix(self.status))

def fix(me):
    if type(me) in (unicode, str):
        me = me.strip().replace('\0', '')
        if not me:
            return u"&nbsp;"
    return me

#----------------------------------------------------------------------
# Find processes of interest.
#----------------------------------------------------------------------
def report(conn, cursor):
    cursor.execute("SELECT GETDATE()")
    now = cursor.fetchall()[0][0]
    cursor.execute("""
         SELECT p.spid, p.waittime, p.lastwaittype, p.waitresource,
                d.name, p.uid, p.cpu, p.physical_io, p.memusage, p.login_time,
                p.last_batch, p.ecid, p.open_tran, p.status, p.hostname,
                p.program_name, p.hostprocess, p.cmd, p.nt_domain,
                p.nt_username, p.net_address, p.net_library, p.loginame,
                p.blocked
           FROM master..sysprocesses p
           JOIN master..sysdatabases d
             ON p.dbid = d.dbid
          WHERE blocked <> 0
             OR spid IN (SELECT blocked FROM master..sysprocesses)""")
    rows = cursor.fetchall()
    html = [u"""\
<html>
 <head>
  <title>SQL Server Process Blocks (%s)</title>
  <style type='text/css'>
   body { font-family: Arial; font-size: 9pt; }
   h1   { font-size: 14pt; }
   h2   { font-size: 12pt; }
  </style>
 </head>
 <body>
  <h1>SQL Server Process Blocks (%s)</h1>
""" % (now, now)]
    if False and not rows:
        html.append(u"""\
  <h2>No blocks to report</h2>
""")
    else:
        html.append(u"""\
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>SPID</th>
    <th>Blocked By</th>
    <th>Wait Time</th>
    <th>Last Wait Type</th>
    <th>Wait Resource</th>
    <th>CPU Usage</th>
    <th>Physical I/O</th>
    <th>Memory Usage</th>
    <th>Database</th>
    <th>User ID</th>
    <th>Login Name</th>
    <th>NT User Name</th>
    <th>NT Domain</th>
    <th>Host Name</th>
    <th>Program Name</th>
    <th>Host Process</th>
    <th>Current Command</th>
    <th>Net Address</th>
    <th>Net Library</th>
    <th>Login Time</th>
    <th>Last Request</th>
    <th>ECID</th>
    <th>Open Transaction Count</th>
    <th>Status</th>
   </tr>
""")
        for row in rows:
            process = Process(row)
            html.append(process.toHtml())
        html.append(u"""\
  </table>
""")
    html.append(u"""\
 </body>
</html>
""")
    html = u"".join(html)
    cdrcgi.sendPage(html)
if __name__ == "__main__":
    report(conn, cursor)
