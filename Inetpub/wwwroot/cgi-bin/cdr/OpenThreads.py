#----------------------------------------------------------------------
#
# $Id: OpenThreads.py,v 1.1 2002-08-12 20:59:19 bkline Exp $
#
# Display of threads which are still running in the CDR Server (mostly
# a debugging tool).
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cdrcgi

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
        SELECT MAX(id) 
          FROM debug_log 
         WHERE thread = 1""")
startId = cursor.fetchone()[0]
oldQuery = """\
        SELECT dl.thread, dl.recorded, dl.msg
          FROM debug_log dl
         WHERE dl.id >= %d
           AND dl.source = 'Thread Starting'
           AND NOT EXISTS (SELECT * 
                             FROM debug_log
                            WHERE id >= %d
                              AND thread = dl.thread
                              AND source = 'Thread Stopping')""" % \
           (startId, startId)
cursor.execute("""\
        SELECT thread, recorded, source, msg
          FROM debug_log
         WHERE id >= %d
           AND source in ('Thread Starting', 'Thread Stopping')
      ORDER BY id""" % startId)
rows = cursor.fetchall()
class Thread:
    def __init__(self, logId, recorded, id):
        self.logId    = logId
        self.recorded = recorded
        self.id       = id
        self.open     = 1
threads = {}
for row in rows:
    (logId, recorded, source, id) = row
    if source == 'Thread Starting':
        threads[logId] = Thread(logId, recorded, id)
    else:
        threads[logId].open = 0
openThreads = []
keys = threads.keys()
keys.sort()
for key in keys:
    if threads[key].open: 
        openThreads.append(threads[key])
html = """\
<html>
 <head>
  <title>Open CDR Threads</title>
 </head>
 <body>
  <h3>%d Open CDR Threads</h3>
  <table border=1 cellspacing=0 cellpadding=2>
   <tr>
    <th nowrap=1>Log ID</th>
    <th>Started</th>
    <th nowrap=1>Thread ID</th>
   </tr>
""" % len(openThreads)
for thread in openThreads:
    html += """\
   <tr>
    <td align=left>%d</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (thread.logId, thread.recorded, thread.id)
cdrcgi.sendPage( html + """\
  </table>
 </body>
</html>""")
