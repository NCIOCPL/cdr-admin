#!/usr/bin/python

def bail(msg):
    print """\
Content-type: text/html

<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>CDR Open Issues</title>
  <style type='text/css'>
   h1         { font-family: serif; font-size: 16pt; color: black; }
   span.bugno { font-family: Arial; font-size: 12pt; color: blue; }
   span.short { font-family: Arial; font-size: 12pt; color: blue;
                font-weight: bold; }
   span.info  { font-family: Arial; font-size: 10pt; color: black; }
   pre        { font-family: Courier; font-size: 9pt; color: black; }
  </style>
 </head>
 <body>
  <h1>Bailing out!</h1>
  %s
 </body>
</html>""" % cgi.escape(msg)
    sys.exit(1)
import sys, cgi, time
## try:
##     sys.path.append("/var/www/cgi-bin/cdr/lib")
## except:
##     bail("can't insert!")
try:
    import MySQLdb
except ImportError, err:
    bail("ImportError: %s" % str(err))
except:
    bail("can't import MySQLdb!")

fields = cgi.FieldStorage()
flavor = fields and fields.getvalue("flavor") or ""
when   = fields and fields.getvalue("when")   or ""

try:
    conn = MySQLdb.connect(db='bugs', user='bugsbackup',
                           host='verdi.nci.nih.gov')
except:
    bail("can't connect!")
try:
    curs = conn.cursor()
except:
    bail("can't get a cursor!")
try:
    dependsOn = {}
    blocking  = {}
    curs.execute("""\
          SELECT blocked, dependson
            FROM dependencies""")
    for row in curs.fetchall():
        if not dependsOn.has_key(row[0]):
            dependsOn[row[0]] = []
        dependsOn[row[0]].append(row[1])
        if not blocking.has_key(row[1]):
            blocking[row[1]] = []
        blocking[row[1]].append(row[0])
    op = when == "future" and "=" or "<>"
    curs.execute("""\
          SELECT b.bug_id, a.realname, b.bug_severity, b.bug_status,
                 b.component, b.creation_ts, b.short_desc, b.priority,
                 r.realname, b.resolution, q.realname, b.votes
            FROM bugs b
 LEFT OUTER JOIN profiles a
              ON a.userid = b.assigned_to
 LEFT OUTER JOIN profiles r
              ON r.userid = b.reporter
 LEFT OUTER JOIN profiles q
              ON q.userid = b.qa_contact
           WHERE bug_status <> 'CLOSED'
             AND priority %s 'P5'
             AND resolution <> 'DUPLICATE'
             /*
          AND a.userid = b.assigned_to
          AND r.userid = b.reporter
          AND q.userid = b.qa_contact */
     ORDER BY b.bug_id""" % op)
except:
    bail("can't execute query!")
try:
    rows = curs.fetchall()
except:
    bail("can't fetch rows!")
print """\
Content-type: text/html

<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>CDR Open %s Issues</title>
  <style type='text/css'>
   h1         { font-family: serif; font-size: 16pt; color: black; }
   span.bugno { font-family: Arial; font-size: 12pt; color: blue; }
   span.short { font-family: Arial; font-size: 12pt; color: blue;
                font-weight: bold; }
   span.info  { font-family: Arial; font-size: 10pt; color: black; }
   pre        { font-family: Courier; font-size: 9pt; color: black; }
  </style>
 </head>
 <body>
  <h1>%d Open CDR %sIssues %s</h1>""" % (when == "future" and "Future " or "",
                                         len(rows),
                                         when == "future" and "Future " or "",
                                         time.strftime("%Y-%m-%d"))
for row in rows:
    id, assignee, severity, status, component, created, short, priority, \
        reporter, resolution, qa, votes = row
    if resolution: status += "-%s" % resolution
    print """\
  <span class='bugno'>
   <a href='http://verdi.nci.nih.gov/tracker/show_bug.cgi?id=%d'>[%d]</a>
  </span>
""" % (id, id)
    if flavor == 'shortest': continue
    print """\
  <span class='short'>%s</span><br>
""" % cgi.escape(short)
    if flavor == 'shorter': continue
    deps = ""
    if dependsOn.has_key(id):
        deps += "Depends On: "
        sep = ""
        for blocker in dependsOn[id]:
            deps += "%s%d" % (sep, blocker)
            sep = ",&nbsp;"
    if blocking.has_key(id):
        if deps:
            deps += ";&nbsp;&nbsp;"
        deps += "Blocking:&nbsp;"
        sep = ""
        for blockee in blocking[id]:
            deps += "%s%d" % (sep, blockee)
            sep = ",&nbsp;"
    if deps:
        deps += "<br>\n"
    print """\
  <span class='info'>
   Severity:&nbsp;%s&nbsp;Priority:&nbsp;%s&nbsp;
   Status:&nbsp;%s&nbsp;Votes:&nbsp;%d<br>
   Reported:&nbsp;%s By:&nbsp;%s&nbsp;
   Assigned To:&nbsp;%s&nbsp;QA:&nbsp;%s<br>%s
  </span><br>""" % (severity, priority,
                    status, votes, created, reporter, assignee, qa, deps)
    if flavor == 'short': continue
    curs.execute("""\
        SELECT p.realname, d.bug_when, d.thetext
          FROM longdescs d, profiles p
         WHERE d.who = p.userid
           AND bug_id = %d
      ORDER BY d.bug_when""" % id)
    for name, when, text in curs.fetchall():
        print """\
  <span class='info'>
   <b>Comments entered %s by %s:</b><br>
   <pre>%s</pre><br>
  </span>
""" % (when, name, cgi.escape(text))
    print "  <hr>"
print """\
 </body>
</html>"""
