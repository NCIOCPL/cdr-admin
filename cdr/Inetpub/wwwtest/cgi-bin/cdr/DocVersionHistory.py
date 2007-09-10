#----------------------------------------------------------------------
#
# $Id: DocVersionHistory.py,v 1.20 2007-09-10 22:25:24 venglisc Exp $
#
# Show version history of document.
#
# $Log: not supported by cvs2svn $
# Revision 1.19  2007/08/24 13:42:35  bkline
# Fixed bug trying to subscript the value in a NULL database column.
#
# Revision 1.18  2006/09/18 20:06:25  bkline
# Tweaked timing code and query for publication job type.
#
# Revision 1.17  2006/08/19 03:13:10  bkline
# Drastic overhaul of the report to improve performance (the report was
# timing out for documents with many versions).  The report now takes
# an average of 94 milliseconds to process on Mahler for the document
# with the most versions (CDR67126 with 522 versions).
#
# Revision 1.16  2004/07/27 16:03:16  venglisc
# In the case that a blocked document never got published before the
# report failed to extract a removal date from Cancer.gov.
# The program has been changed to catch this error and display a message
# to this effect.
#
# Revision 1.15  2004/07/13 19:20:21  venglisc
# Added code to display information on why the removal date of a document
# can not be displayed, i.e. blocked via full-load, not versioned yet
# (Bug #216).
#
# Revision 1.14  2004/05/11 17:32:03  bkline
# Plugged in information about publication blocks and removals.
#
# Revision 1.13  2004/03/23 22:43:46  venglisc
# Modified to display an "R " in front of version if document has been
# removed from Cancer.gov display.
#
# Revision 1.12  2004/02/05 13:36:47  bkline
# Changed title bar from "QC Reports" to "Document Version History" (request
# #1096).
#
# Revision 1.11  2003/02/12 16:19:10  pzhang
# Showed Vendor or CG job suffix with publication dates.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, sys, time

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle = "Document Version History Report"
fields   = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
title    = "CDR Administration"
section  = "Document Version History"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script   = "DocVersionHistory.py"
header   = cdrcgi.header(title, title, section, script, buttons, method='GET')
docId    = fields.getvalue(cdrcgi.DOCID) or None
docTitle = fields.getvalue("DocTitle")   or None
if docId:
    digits = re.sub('[^\d]+', '', docId)
    intId  = int(digits)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# If we have a document type but no doc ID or title, ask for the title.
#----------------------------------------------------------------------
if not docId and not docTitle:
    form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <TABLE>
   <TR>
    <TD>Document ID:&nbsp;</TD>
    <TD><INPUT SIZE='60' NAME='DocId'></TD>
   </TR>
   <TR>
    <TD>Document title:&nbsp;</TD>
    <TD><INPUT SIZE='60' NAME='DocTitle'></TD>
   </TR>
  </TABLE>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# If we have a document title but not a document ID, find the ID.
#----------------------------------------------------------------------
if docTitle and not docId:
    try:
        cursor.execute("""\
            SELECT id
              FROM document
             WHERE title LIKE ?""", docTitle + '%', timeout = 300)
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Unable to find document with title '%s'" % docTitle)
        if len(rows) > 1:
            cdrcgi.bail("Ambiguous title '%s'" % docTitle)
        intId = rows[0][0]
        docId = "CDR%010d" % intId
    except cdrdb.Error, info:
        cdrcgi.bail('Failure looking up document title: %s' % info[1][0])

#----------------------------------------------------------------------
# Object for the document-level information we need.
#----------------------------------------------------------------------
class Document:
    def __init__(self, cursor, docId):
        self.__start = time.time()
        try:
            cursor.execute("""\
                SELECT doc_title,
                   doc_type,
                   doc_status,
                   created_by,
                   created_date,
                   mod_by,
                   mod_date
              FROM doc_info 
             WHERE doc_id = ?""", docId, timeout = 300)
            row = cursor.fetchone()
        except Exception, e:
            cdrcgi.bail('Database error looking up CDR%s: %s' % (docId, e))
        if not row:
            cdrcgi.bail("Unable to find document info for CDR%s" % docId)
        self.__t1             = time.time() - self.__start
        self.__docId          = docId
        self.__cursor         = cursor
        self.__docTitle       = row[0]
        self.__docType        = row[1]
        self.__docStatus      = row[2]
        self.__createdBy      = row[3]
        self.__createdDate    = row[4]
        self.__modBy          = row[5]
        self.__modDate        = row[6]
        self.__lastPubJob     = None
        self.__lastPubVersion = None
        self.__removeDate     = u''
        self.__blocked        = self.__docStatus == 'I'
        self.__versions       = self.__loadVersions()
        self.__versionNumbers = self.__versions.keys()
        self.__versionNumbers.sort()
        self.__versionNumbers.reverse()

    def __onCancerDotGov(self):
        try:
            self.__cursor.execute("SELECT id FROM pub_proc_cg WHERE id = ?",
                                self.__docId)
            rows = self.__cursor.fetchall()
            return rows and True or False
        except Exception, e:
            cdrcgi.bail("Failure checking whether CDR%s is on Cancer.gov" %
                        (self.__docId, e))

    def __firstFullLoadAfterLastPubJob(self):
        if not self.__lastPubJob:
            return None
        try:
            self.__cursor.execute("""\
                SELECT MIN(started)
                  FROM pub_proc
                 WHERE status = 'Success'
                   AND pub_subset = 'Full-Load'
                   AND id > ?""", self.__lastPubJob)
            rows = self.__cursor.fetchall()
            return rows and rows[0][0] and rows[0][0][:10] or None
        except Exception, e:
            cdrcgi.bail("Failure finding full-load publication job: %s" % e)

    def __loadVersions(self):
        try:
            t = time.time()
            self.__cursor.execute("""\
                SELECT v.num, 
                       v.comment,
                       u.fullname,
                       v.dt,
                       v.val_status,
                       v.publishable
                  FROM doc_version v
                  JOIN usr u
                    ON u.id = v.usr
                 WHERE v.id = ?""", self.__docId, timeout = 300)
            versions = {}
            rows = self.__cursor.fetchall()
            self.__t2 = time.time() - t
            for num, comment, user, date, status, publishable in rows:
                versions[num] = self.Version(num, comment, user, date,
                                             status, publishable)
        except Exception, e:
            cdrcgi.bail("Failure extracting version information: %s" % e)

        # Fold in the publication events.
        try:
            self.__cursor.execute("""\
                 SELECT doc_version,
                        started,
                        pub_proc,
                        removed,
                        CASE
                            WHEN output_dir IS NULL OR output_dir = '' THEN 'C'
                            ELSE 'V'
                        END AS job_type
                   FROM primary_pub_doc
                  WHERE doc_id = ?
               ORDER BY started""", self.__docId, timeout = 300)
            for row in self.__cursor.fetchall():
                (num, started, pubProcId, removed, jobType) = row
                pubDate = started[:10]
                versions[num].addPubEvent(pubDate, jobType, pubProcId, removed)
                if removed == 'Y' and self.__blocked:
                    self.__removeDate = pubDate
                if not self.__lastPubJob or pubProcId > self.__lastPubJob:
                    self.__lastPubJob = pubProcId
                if not self.__lastPubVersion or num > self.__lastPubVersion:
                    self.__lastPubVersion = num
            return versions
        except Exception, e:
            cdrcgi.bail("Failure extracting pub job information: %s" % e)

    def toHtml(self):

        # Build the report header.
        now  = time.localtime()
        html = [u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>CDR%010d - %s</title>
  <style type='text/css'>
   body   { font-family: Arial, Helvetica, sans-serif }
   h1     { font-size: 14pt }
   h2     { font-size: 12pt }
   .red   { color: red }
   .timer { color: green; font-size: 7pt; font-style: oblique }
  </style>
  <!-- Report generation processing time: @@TIME@@ seconds -->
 </head>
 <body>
  <center>
   <h1>Document Version History Report</h1>
   <h2>%s</h2>
  </center>
  <br />
  <br />
  <table border='0' width='100%%'>
   <tr>
    <th align='right' nowrap='1'>Document ID:&nbsp;</th>
    <td nowrap='1'>CDR%010d</td>
    <th align='right' nowrap='1'>Document Type:&nbsp;</th>
    <td nowrap='1'>%s</td>
   </tr>
   <tr>
    <th nowrap='1' align='right' valign='top'>Document Title:&nbsp;</th>
    <td colspan='3'>%s</td>
   </tr>
""" % (self.__docId, 
       time.strftime("%m/%d/%Y", now), 
       time.strftime("%B %d, %Y", now),
       self.__docId,
       self.__docType,
       self.__docTitle)]

        # If a document has been blocked for publication (doc_status is 'I' --
        # for "Inactive") we display an extra row showing the status and the
        # date the document was pulled from Cancer.gov (assuming it has been
        # pulled).
        if self.__blocked:

            # Make sure we have a removal date.  Normally we will, if the
            # document has ever been published, because when the document is
            # blocked the next publication event sends an instruction to
            # Cancer.gov to withdraw the document, in which case we will have
            # picked up the removal date when we collected the information
            # on publication events.
            if not self.__removeDate:

                # No.  Is the document still on Cancer.gov?
                if self.__onCancerDotGov():

                    # Yes, which means the document was blocked since last
                    # published and will be removed as part of the next
                    # publication job.  However, only a versioned document
                    # can be removed, so we check to see if a version has
                    # been created since the last version which got published.
                    self.__removeDate = u"Needs versioning"
                    if self.__versions:
                        if self.__versionNumbers[0] > self.__lastPubVersion:
                            self.__removeDate = u"Not yet removed"

                else:

                    # The document isn't on Cancer.gov.  Was it removed by
                    # a full load (meaning the sequence of events was
                    # publication of the document when it was active,
                    # followed by a change of status to inactive, after
                    # which the next publication event was a full load)?
                    self.__removeDate = self.__firstFullLoadAfterLastPubJob()
                    if not self.__removeDate:

                        # If that didn't happen, then presumably the document
                        # was never published.
                        if not self.__lastPubJob:
                            self.__removeDate = u'Never published'

                        else:

                            # Otherwise, we have a data corruption problem.
                            self.__removeDate = u"CAN'T DETERMINE REMOVAL DATE"

            # One way or another, we now have a string for the "removal date".
            html.append(u"""\
   <tr>
    <th nowrap='1' valign='top' align='right'>Document Status:&nbsp;</th>
    <td><b class='red'>BLOCKED FOR PUBLICATION</b></td>
    <th nowrap='1' valign='top' align='right'>Removal Date:&nbsp;</th>
    <td><b class='red'>%s</b></td>
   </tr>
""" % self.__removeDate)

        # Finish the report header block.
        html.append(u"""\
   <tr>
    <th nowrap='1' valign='top' align='right'>Created By:&nbsp;</th>
    <td>%s</td>
    <th nowrap='1' valign='top' align='right'>Date:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th nowrap='1' valign='top' align='right'>Last Updated By:&nbsp;</th>
    <td>%s</td>
    <th nowrap='1' valign='top' align='right'>Date:&nbsp;</th>
    <td>%s</td>
   </tr>
  </table>
  <br />
  <table border='1' width='100%%' cellspacing='0' cellpadding='2'>
   <tr>
    <th>VERSION #</th>
    <th>COMMENT</th>
    <th>DATE</th>
    <th>USER</th>
    <th>VALIDITY</th>
    <th>PUBLISHABLE?</th>
    <th>PUBLICATION DATE(S)</th>
   </tr>
""" % (self.__createdBy or u"[Conversion]",
       self.__createdDate and self.__createdDate[:10] or "2002-06-22",
       self.__modBy or "N/A",
       self.__modDate and self.__modDate[:10] or "N/A"))

        #----------------------------------------------------------------------
        # Build the report body using a table with one row for each version.
        # Put the most recent versions at the top, because those are the ones
        # we're most likely to be interested in.
        #----------------------------------------------------------------------
        for versionNumber in self.__versionNumbers:
            html.append(self.__versions[versionNumber].toHtml())
        delta = time.time() - self.__start
        html.append(u"""\
  </table>
  <br />
  <span class='timer'>Report generation time: %.0f milliseconds</span>
 </body>
</html>
""" % (delta * 1000))
        timings = (u"query 1: %f query 2: %f; total time: %f" %
                   (self.__t1, self.__t2, delta))
        return u"".join(html).replace(u"@@TIME@@", timings)

    #----------------------------------------------------------------------
    # Object to hold info for a single version.
    #----------------------------------------------------------------------
    class Version:
        def __init__(self, num, comment, user, date, status, publishable):
            self.__num         = num
            self.__comment     = comment and cgi.escape(comment) or u""
            self.__user        = user
            self.__date        = date[:10]
            self.__status      = status
            self.__publishable = publishable
            self.__pubEvents   = []

        def addPubEvent(self, jobDate, jobType, jobId, removed):
            if removed == 'Y':
                self.__pubEvents.append("<span class='red'>%s(%s-%d)R</span>" % (jobDate, jobType, jobId))
            else:
                self.__pubEvents.append("%s(%s-%d)" % (jobDate, jobType, jobId))

        def toHtml(self):
            return u"""\
   <tr>
    <td valign='top' align='center'>%d</td>
    <td valign='top'>%s</td>
    <td valign='top' align='center'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top' align='center'>%s</td>
    <td valign='top' align='center'>%s</td>
    <td valign='top' align='center'>%s</td>
   </tr>
    """ % (self.__num,
           self.__comment or u"&nbsp;",
           self.__date,
           self.__user,
           self.__status,
           self.__publishable == 'Y' and 'Y' or 'N',
           self.__pubEvents and u"<br>".join(self.__pubEvents) or u"&nbsp;")

#----------------------------------------------------------------------
# Send out the report.
#----------------------------------------------------------------------
doc = Document(cursor, intId)
html = doc.toHtml()
cdrcgi.sendPage(doc.toHtml())
