#----------------------------------------------------------------------
#
# $Id: GetReportWorkbook.py,v 1.2 2006-05-04 14:22:14 bkline Exp $
#
# Sends back Excel workbook report to client.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2005/11/22 13:43:18  bkline
# CGI program to send back Excel workbook report to web client.
#
#----------------------------------------------------------------------
import cgi, cdrcgi, os, msvcrt, sys

msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
fields = cgi.FieldStorage()
name   = fields and fields.getvalue('name') or cdrcgi.bail('Missing name')
try:
    fobj = file('d:/cdr/Reports/%s' % name, 'rb')
except:
    cdrcgi.bail('Report %s not found' % name)
book = fobj.read()
fobj.close()

print """\
Content-type: application/vnd.ms-excel
Content-disposition: attachment;filename=%s
""" % name
sys.stdout.write(book)
