#!/usr/bin/python
# ******************************************************************
#
# File Name: update-pdq-contact.py
#            ---------------------
# This script is called by the FTP Linux server during the email
# notification in order to update the notification count and set
# the expiration date, etc.
#
# ------------------------------------------------------------------
# Created:                              Volker Englisch - 2016-04-14
#
# History:
# --------
# OCECDR-4023: Maintain PDQ Partner List on CDR Server
#
# ******************************************************************
import cgi
import cdrdb

conn = cdrdb.connect()
cursor = conn.cursor()
fields = cgi.FieldStorage()

# The action values are:
#    notified: update notification date
#              update counter
#    expired:  update notification date
#              update counter
#              update termination date
# ------------------------------------------
action = fields.getvalue("action", "notified")
vendor_id = fields.getvalue("id")

if action == "notified":
    cursor.execute("""\
    UPDATE data_partner_contact
       SET notif_date = GETDATE(), 
           notif_count = notif_count + 1
     WHERE contact_id = ?""", vendor_id)
elif action == "expired":
    cursor.execute("""\
    UPDATE data_partner_org
       SET terminated = GETDATE()
     WHERE org_id = ?""", vendor_id)
#    cursor.execute("""\
#    UPDATE data_partner_contact
#       SET notified_date = GETDATE(), 
#           notified_count= notified_count + 1,
#           termination = GETDATE()
#     WHERE org_name = ?""", vendor_id)

conn.commit()

# Return OK if everything finished successfully
# ---------------------------------------------
print """\
Content-type: text/plain

OK"""
