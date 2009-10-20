#----------------------------------------------------------------------
#
# $Id$
#
# Show the contents of the log for a CTGov import job.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2009/05/12 21:38:59  venglisc
# Modified string passed to sendPage() to be of type Unicode. (Bug 4560)
#
# Revision 1.1  2006/05/04 15:17:37  bkline
# Show the contents of a CTGov job's log.
#
#----------------------------------------------------------------------
import cdrcgi, cgi

fields = cgi.FieldStorage()
job    = fields and fields.getvalue('job') or cdrcgi.bail('No jobname given')
try:
    body = file('d:/cdr/Output/NlmExport/%s/clinical_trials.log' % job).read()
except:
    cdrcgi.bail("Unable to read logfile for job %s" % job)
cdrcgi.sendPage(u"""\
<html>
 <head>
  <title>Log from CTGov Export Job %s</title>
 </head>
 <body>
  <h1>Log from CTGov Export Job %s</h1>
  <pre>
%s
  </pre>
 </body>
</html>
""" % (job, job, cgi.escape(unicode(body, 'utf-8'))))
