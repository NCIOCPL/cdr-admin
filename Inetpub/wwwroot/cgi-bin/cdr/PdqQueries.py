#!/usr/bin/python
#----------------------------------------------------------------------
#
# $Id$
#
# Ad-hoc SQL query tool for PDQ database.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

import win32api, cdrcgi, os
os.environ['PATH'] = '%s;%s' % (r'd:\usr\oracle\ora92\bin', os.environ['PATH'])
win32api.LoadLibrary("d:/usr/oracle/ora92/bin/oci.dll")
#cdrcgi.bail(os.environ['PATH'])
import CgiQuery, DCOracle2

class PdqQuery(CgiQuery.CgiQuery):
    def __init__(self):
        conn = DCOracle2.Connect('bkline/bkline@pdq')
        CgiQuery.CgiQuery.__init__(self, conn, "PDQ", "PdqQueries.py")

pdqQuery = PdqQuery()
pdqQuery.run()
