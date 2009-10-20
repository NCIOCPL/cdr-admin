#----------------------------------------------------------------------
#
# $Id$
#
# We need a report with lists the CTEP_Institution_Code, the Organization
# Name (from the CDR record) and the entire address of the Organization.
#
# Would it be possible for there to be a user interface which allows the
# report output to be selected in either XML or an Excel spreadsheet?
#
# It needs to be place in the Admin menu under Reports/Protocols/Data Import
# reports/CTEP Institutions with Address Information
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdrdb, cdrdocobject, sys, time

fields = cgi.FieldStorage()
output = fields.getvalue('output') or 'xml'

class CtepOrgReport:
    def __init__(self, output = 'xml'):
        self.output = output
    def run(self):
        cursor = cdrdb.connect('CdrGuest').cursor()
        cursor.execute("""\
    SELECT m.doc_id, m.value, t.value
      FROM external_map m
      JOIN query_term t
        ON t.doc_id = m.doc_id
      JOIN external_map_usage u
        ON u.id = m.usage
     WHERE u.name = 'CTEP_Institution_Code'
       AND t.path = '/Organization/OrganizationNameInformation'
                  + '/OfficialName/Name'
  ORDER BY m.value""")
        rows = cursor.fetchall()#[:10]
        if self.output == 'xml':
            print "Content-type: text/xml;charset=utf-8\n"
            print u"<?xml version='1.0' encoding='utf-8'?>\n<CtepOrgs>"
        elif self.output == 'csv':
            try:
                import os, msvcrt
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
            except:
                pass
            now = time.strftime("%Y%m%d%H%M%S")
            name = "CtepOrgs-%s.csv" % now
            sys.stdout.write("Content-type: application/vnd.ms-excel\r\n")
            sys.stdout.write("Content-Disposition: attachment; ")
            sys.stdout.write("filename=%s\r\n\r\n" % name)
            import csv
            writer = csv.writer(sys.stdout)
            writer.writerow(("CDR ID", "CTEP ID", "Organization Name",
                             "Address", "Phone"))
        else:
            import ExcelWriter
            book = ExcelWriter.Workbook()
            sheet = book.addWorksheet('CTEP Orgs')
            font = ExcelWriter.Font(bold = True)
            style = book.addStyle(font = font)
            sheet.addCol(1, 50)
            sheet.addCol(2, 50)
            sheet.addCol(3, 200)
            sheet.addCol(4, 200)
            sheet.addCol(5, 75)
            row = sheet.addRow(1, style)
            row.addCell(1, u"CDR ID", style)
            row.addCell(2, u"CTEP ID", style)
            row.addCell(3, u"Organization Name", style)
            row.addCell(4, u"Address", style)
            row.addCell(5, u"Phone", style)
            align = ExcelWriter.Alignment('Left', 'Top', wrap = True)
            style = book.addStyle(alignment = align)
            rowNum = 2
        for docId, ctepId, orgName in rows:
            try:
                contact = cdrdocobject.Organization.CipsContact(docId)
            except:
                contact = None
            if self.output == 'xml':
#                org = [u"""\
# <Org PdqID='%s' CtepId='%s'>
                org = [u"""\
 <Org>
  <CdrId>%d</CdrId>
  <CtepId>%s</CtepId>
  <OfficialName>%s</OfficialName>
""" % (docId,
       cgi.escape(ctepId),#.replace(u"'", u"&apos;"),
       cgi.escape(orgName))]
                if contact:
                    city = contact.getCity() or u""
                    country = contact.getCountry() or u""
                    lines = contact.getStreetLines()
                    state = contact.getState()
                    phone = contact.getPhone()
                    org.append(u"""\
  <Address>
""")
                    for line in lines:
                        org.append(u"""\
   <Street>%s</Street>
""" % cgi.escape(line))
                    if contact.getCity():
                        org.append(u"""\
   <City>%s</City>
""" % cgi.escape(contact.getCity()))
                    if contact.getCitySuffix():
                        org.append(u"""\
   <CitySuffix>%s</CitySuffix>
""" % cgi.escape(contact.getCitySuffix()))
                    if contact.getPostalCode():
                        pos = u""
                        if contact.getCodePosition():
                            pos = u" position='%s'" % contact.getCodePosition()
                        org.append(u"""\
   <PostalCode%s>%s</PostalCode>
""" % (pos, cgi.escape(contact.getPostalCode())))
                    if contact.getState():
                        org.append(u"""\
   <StateOrProvince>%s</StateOrProvince>
""" % cgi.escape(contact.getState()))
                    if contact.getCountry():
                        org.append(u"""\
   <Country>%s</Country>
""" % cgi.escape(contact.getCountry()))
                    org.append(u"""\
  </Address>
""")
                    if phone:
                        org.append(u"""\
  <Phone>%s</Phone>
""" % cgi.escape(phone))
                org.append(u"""\
 </Org>""")
                org = u"".join(org)
                print org.encode('utf-8')
            elif self.output == 'csv':
                address = u''
                phone = u''
                if contact:
                    address = u"\r\n".join(contact.getAddressLines(False,
                                                                   False))
                    phone = contact.getPhone() or u''
                row = (docId, ctepId.encode('utf-8'), orgName.encode('utf-8'),
                       address.encode('utf-8'), phone.encode('utf-8'))
                writer.writerow(row)
            else:
                row = sheet.addRow(rowNum, style)
                rowNum += 1
                row.addCell(1, docId)
                row.addCell(2, ctepId)
                row.addCell(3, orgName)
                if contact:
                    row.addCell(4, u"\n".join(contact.getAddressLines(False,
                                                                      False)))
                    phone = contact.getPhone()
                    if phone:
                        row.addCell(5, phone)
        if self.output == 'xml':
            print "</CtepOrgs>"
        elif self.output in ('excel', 'xls'):
            if sys.platform == "win32":
                import os, msvcrt
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
            now = time.strftime("%Y%m%d%H%M%S")
            name = "CtepOrgs-%s.xls" % now
            print "Content-type: application/vnd.ms-excel"
            print "Content-Disposition: attachment; filename=%s" % name
            print
            book.write(sys.stdout, True)
job = CtepOrgReport(output)
job.run()
