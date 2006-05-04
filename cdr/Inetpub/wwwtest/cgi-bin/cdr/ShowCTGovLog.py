#----------------------------------------------------------------------
#
# $Id: ShowCTGovLog.py,v 1.1 2006-05-04 15:17:37 bkline Exp $
#
# Show the contents of the log for a CTGov import job.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrcgi, cgi

fields = cgi.FieldStorage()
job    = fields and fields.getvalue('job') or cdrcgi.bail('No jobname given')
try:
    body = file('d:/cdr/Output/NlmExport/%s/clinical_trials.log' % job).read()
except:
    cdrcgi.bail("Unable to read logfile for job %s" % job)
cdrcgi.sendPage("""\
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
""" % (job, job, cgi.escape(body)))
