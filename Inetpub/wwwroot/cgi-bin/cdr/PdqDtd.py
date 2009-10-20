#----------------------------------------------------------------------
#
# $Id$
#
# Display the licensee DTD (used for the online CDR documentation).
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrcgi, cgi

file = open('d:/cdr/licensee/pdq.dtd')
doc  = file.read()
file.close
cdrcgi.sendPage("""\
<html>
 <head>
  <title>PDQ DTD</title>
 </head>
 <body>
  <pre>
   %s
  </pre>
 </body>
</html>
""" % cgi.escape(doc))
