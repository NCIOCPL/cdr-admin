#!/usr/bin/python
# $Id$
# JIRA::OCECDR-3734

import cdr
import cdrdb
import cgi
import cdrcgi
import datetime
import msvcrt
import os
import sys
import requests
import xlwt

def main():
    """
    Report on GP mailers which have bounced.

    Omit mailers for persons with blocked CDR documents.
    Sort by Person document ID, then by mailer date.
    """
    mailers = GPMailers()
    mailers.report()

class GPMailers:
    """
    Information for PDQ Genetics Professional emailers.

    Attributes:
        info - sequence of dictionaries, one for each emailer; each
               dictionary has column values from the gp_emailer table
    """

    URL = "%s/ListGPEmailers?raw=1" % cdr.emailerCgi()

    def __init__(self):
        """
        Populates the info member with the mailer history.

        1. Ask the gpemailer server for the latest information on all mailers
        2. Parse the information into a sequence of dictionaries, one per
           mailer
        """
        fields = cgi.FieldStorage()
        session = cdrcgi.getSession(fields)
        response = requests.get(self.URL, { "Session": session })
        lines = response.text.splitlines()
        cols = eval(lines.pop(0))
        rows = [eval(row) for row in lines]
        self.info = [dict(zip(cols, row)) for row in rows]

    def report(self):
        """
        Generate and send the report as an Excel workbook.
        """
        self.cursor = cdrdb.connect("CdrGuest").cursor()
        rows = []
        for mailer in self.info:
            if mailer["bounced"] and self._active(mailer["cdr_id"]):
                rows.append((mailer["cdr_id"], mailer["mailed"], mailer["name"],
                             mailer["email"], mailer["bounced"]))
        book = self._create_workbook(rows)
        now = datetime.datetime.now()
        name = "BouncedGPMailer-%s.xls" % now.strftime("%Y%m%d%H%M%S")
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        print "Content-type: application/vnd.ms-excel"
        print "Content-disposition: attachment; filename=%s" % name
        print
        book.save(sys.stdout)

    def _active(self, cdr_id):
        """
        Find out if the Person document for a mailer is still active.
        """
        self.cursor.execute("SELECT active_status FROM document WHERE id = ?",
                            cdr_id)
        rows = self.cursor.fetchall()
        return rows and rows[0][0] == "A" or False

    def _create_workbook(self, rows):
        """
        Create the Excel workbook and populate it with the report data.
        """
        book = xlwt.Workbook(encoding="UTF-8")
        sheet = book.add_sheet("Bounced Mailers")
        self._add_column_headers(sheet)
        self._set_column_widths(sheet)
        row_number = 1
        prev_id = None
        for row in sorted(rows):
            mailed = row[1] and row[1].strftime("%Y-%m-%d") or ""
            bounced = row[4] and row[4].strftime("%Y-%m-%d") or ""
            doc_id = row[0] != prev_id and row[0] or ""
            prev_id = row[0]
            sheet.write(row_number, 0, doc_id)
            sheet.write(row_number, 1, row[2])
            sheet.write(row_number, 2, row[3])
            sheet.write(row_number, 3, mailed)
            sheet.write(row_number, 4, bounced)
            row_number += 1
        return book

    def _add_column_headers(self, sheet):
        """
        Write column headers to the first row of the spreadsheet.
        """
        style = self._create_header_style()
        sheet.write(0, 0, "CDR ID Person", style)
        sheet.write(0, 1, "Full Name", style)
        sheet.write(0, 2, "Email Address", style)
        sheet.write(0, 3, "Mailed Date", style)
        sheet.write(0, 4, "Date Marked as Bounced", style)

    def _create_header_style(self):
        """
        Create a style to make the column headers bold.
        """
        font = xlwt.Font()
        font.bold = True
        style = xlwt.XFStyle()
        style.font = font
        return style

    def _set_column_widths(self, sheet):
        """
        Set the column widths for the report.
        """
        widths = (4000, 6000, 8000, 3000, 6000)
        for i, width in enumerate(widths):
            sheet.col(i).width = width

#----------------------------------------------------------------------
# Entry point.
#----------------------------------------------------------------------
if __name__ == "__main__":
    main()
