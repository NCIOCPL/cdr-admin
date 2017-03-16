#!/usr/bin/python
#----------------------------------------------------------------------
# GP Mailers Bounced Email Report
# JIRA::OCECDR-3734
#----------------------------------------------------------------------

import cdr
import cdrdb
import cgi
import cdrcgi
import datetime
import msvcrt
import os
import sys
import requests

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
        styles = cdrcgi.ExcelStyles()
        sheet = styles.add_sheet("Bounced Mailers", frozen_rows=1)
        widths = (15, 25, 35, 12, 25)
        labels = ("CDR Person ID", "Full Name", "Email Address",
                  "Mailed Date", "Date Marked as Bounced")
        assert(len(widths) == len(labels))
        for i, chars in enumerate(widths):
            sheet.col(i).width = styles.chars_to_width(chars)
        for i, label in enumerate(labels):
            sheet.write(0, i, label, styles.header)
        row_number = 1
        prev_id = None
        for row in sorted(rows):
            mailed = row[1] and row[1].strftime("%Y-%m-%d") or ""
            bounced = row[4] and row[4].strftime("%Y-%m-%d") or ""
            doc_id = row[0] != prev_id and row[0] or ""
            prev_id = row[0]
            sheet.write(row_number, 0, doc_id, styles.left)
            sheet.write(row_number, 1, row[2], styles.left)
            sheet.write(row_number, 2, row[3],  styles.left)
            sheet.write(row_number, 3, mailed, styles.center)
            sheet.write(row_number, 4, bounced, styles.center)
            row_number += 1
        return styles.book

#----------------------------------------------------------------------
# Entry point.
#----------------------------------------------------------------------
if __name__ == "__main__":
    main()
