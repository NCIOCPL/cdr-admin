#!/usr/bin/python
# ******************************************************************
# This script is called by the FTP Linux server during the access
# report creation in order to retrieve all organizations to be
# included on the report
# ------------------------------------------------------------------
# Created:                              Volker Englisch - 2016-04-19
#
# History:
# --------
# OCECDR-3852: Fix and Improve FTP Licensee Report
# ******************************************************************
import cdrdb
import cgi
import lxml.etree as etree

fields = cgi.FieldStorage()
product = fields and fields.getvalue("p") or 'TEST'

cursor = cdrdb.connect().cursor()
cursor.execute("""\
                SELECT org_id, org_name, org_status,
                       activated, terminated, ftp_username
                  FROM data_partner_org o
                  JOIN data_partner_product p
                    ON p.prod_id = o.prod_id
                   AND p.prod_name = '%s'
                   AND p.inactivated IS NULL
                 ORDER BY org_status, org_name""" % product)

root = etree.Element("partners")
for oid, org_name, org_status, activated, terminated, \
    ftp_username in cursor.fetchall():

    contact = etree.SubElement(root, "org_id", oid=str(oid))
    etree.SubElement(contact, "org_name").text = org_name
    etree.SubElement(contact, "org_status").text = org_status
    etree.SubElement(contact, "activated").text = activated
    etree.SubElement(contact, "terminated").text = terminated
    etree.SubElement(contact, "ftp_userid").text = ftp_username

print """\
Content-type: text/xml

%s""" % etree.tostring(root, pretty_print=True)
