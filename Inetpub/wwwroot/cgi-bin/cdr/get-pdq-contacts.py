#!/usr/bin/python
# ******************************************************************
#
# File Name: get-pdq-contacts.py
#            -------------------
# This script is called by the FTP Linux server during the email
# notification in order to retrieve all users that need to be
# notified.
#
# ------------------------------------------------------------------
# Created:                              Volker Englisch - 2016-04-14
#
# History:
# --------
# OCECDR-4023: Maintain PDQ Partner List on CDR Server
#
# ******************************************************************
import cdrdb
import cgi
import lxml.etree as etree

fields = cgi.FieldStorage()
product = fields and fields.getvalue("p") or 'TEST'

cursor = cdrdb.connect().cursor()
cursor.execute("""\
                SELECT contact_id, prod_name, email_addr, person_name, org_name,
                       org_status, contact_type, activated,
                       renewal, notif_date, org_id
                  FROM pdq_contact
                 WHERE org_status in ('A', 'S')
                   AND contact_type <> 'D'
                   AND terminated is NULL
                   AND prod_name = ?
union
                SELECT contact_id, prod_name, email_addr, person_name, org_name,
                       org_status, contact_type, activated, 
                       renewal, notif_date, org_id
                  FROM pdq_contact
                 WHERE org_status = 'T'
                   AND contact_type <> 'D'
                   AND terminated is NULL
                   AND prod_name = ?
order by org_status, org_name""", (product, product))

root = etree.Element("contacts")
for pid, prod_name, email_address, person_name, org_name, \
    org_status, contact_type, activation_date, \
    renewal_date, notified_date, org_id in cursor.fetchall():

    contact = etree.SubElement(root, "contact", pid=str(pid))
    etree.SubElement(contact, "product").text = prod_name
    etree.SubElement(contact, "email_address").text = email_address
    etree.SubElement(contact, "person_name").text = person_name
    etree.SubElement(contact, "org_name").text = org_name
    etree.SubElement(contact, "org_status").text = org_status
    etree.SubElement(contact, "contact_type").text = contact_type
    etree.SubElement(contact, "activation_date").text = activation_date
    etree.SubElement(contact, "renewal_date").text = renewal_date
    etree.SubElement(contact, "notified_date").text = notified_date
    etree.SubElement(contact, "org_id").text = str(org_id)

print """\
Content-type: text/xml

%s""" % etree.tostring(root, pretty_print=True)

