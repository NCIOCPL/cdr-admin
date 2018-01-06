#!/usr/bin/python
# ******************************************************************
#
# File Name: show-PDQ-summary.py
#            -------------------
# Script to take our sample XML PDQ summary (PDQ-summary.xml) and
# apply the sample XSLT stylesheet (PDQ-summary.xsl) to create a
# sample HTML output file (PDQ-summary.html).
# These files have been created in response to PDQ partner requests
# wanting to see samples of our transformation.
#
# When this cgi is run it is expected that both files, the XML as
# well as the XSL documents, are located within the .../cgi-bin/cdr
# directory.  The user can display the entire file or an individual
# section only:
#  http://cdr-dev.cancer.gov/cgi-bin/cdr/show-PDQ-summary.py?section=*
# or
#  http://cdr-dev.cancer.gov/cgi-bin/cdr/show-PDQ-summary.py?section=2
#
# This file has been originally created by Bob Kline.
# ------------------------------------------------------------------
# Created:                              Volker Englisch - 2016-03-23
#
# History:
# --------
# OCECDR-3856: Create Content Distribution Partner Headstart
#
# ******************************************************************
import lxml.html
import lxml.etree as etree
import cgi
import cdrcgi
import cStringIO
import cdrdb

fields = cgi.FieldStorage()
doc_id = fields.getvalue("doc-id") or 62843 #62779
section = fields.getvalue("section") or "*"

XSL = "d:/Inetpub/wwwroot/cgi-bin/cdr/PDQ-summary.xsl"
XML = "d:/Inetpub/wwwroot/cgi-bin/cdr/PDQ-summary.xml"

# -------------------------------------------------------------
# Retrieve a CDR document from the database
# (function is not used if a CDR document is read from disk
# -------------------------------------------------------------
def get_doc(cursor, doc_id):
    cursor.execute("SELECT xml FROM pub_proc_cg WHERE id = ?", doc_id)
    return cursor.fetchall()[0][0]


# -------------------------------------------------------------
# Read the XSLT stylesheet and transform the passed document
# -------------------------------------------------------------
def filter_doc(doc_xml, section):
    try:
        f = open(XSL, 'r')
        myXslt = f.read()
        f.close()
    except:
        cdrcgi.bail('Unable to open XSL file %s' % XSL)

    xslt_root = etree.XML("%s" % myXslt)

    transform = etree.XSLT(xslt_root)
    fp = cStringIO.StringIO(doc_xml.encode("utf-8"))
    doc = etree.parse(fp)
    return transform(doc, section=section)


# --------------------------------------------------------------
# Read a file, apply the XSLT styles and display the HTML output
# --------------------------------------------------------------
def main():
    # Use the following section to read in the sample file from disk
    # --------------------------------------------------------------
    # <read-section Start>
    try:
        p = open(XML, 'r')
        doc_xml = p.read()
        p.close()
    except:
        cdrcgi.bail('Unable to open XML file %s' % XML)
    filtered_doc = filter_doc(unicode(doc_xml, 'utf-8'), section)
    # <read-section End>

    # Use the following section to select CDR documents from the DB
    # -------------------------------------------------------------
    # <DB-section Start>
    #cursor = cdrdb.connect("CdrGuest").cursor()
    #doc_xml = get_doc(cursor, doc_id)
    #filtered_doc = filter_doc(doc_xml, section)
    # <DB-section End>

    print """\
Content-type: text/html; charset=utf-8

<!DOCTYPE html>
%s""" % lxml.html.tostring(filtered_doc, pretty_print=True)

main()