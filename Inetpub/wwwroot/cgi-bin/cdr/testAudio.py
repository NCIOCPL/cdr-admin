# Test program for mp3 audio stored in the Glossary Term zip files.

import sys, os, msvcrt, zipfile, cgi, cdrcgi, ExcelReader

def sendMp3(zipf, mp3name):
    """
    Send the mp3 file found in the zipfile
    """
    try:
        mp3Buf = zipf.read(mp3name)
    except Exception as info:
        cdrcgi.bail("Failed to read mp3 file named '%s': %s" % (mp3name, info))

    # Write binary data
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    sys.stdout.write("Content-Type: audio/mpeg\r\n")
    sys.stdout.write("Content-Length: %d\r\n\r\n" % len(mp3Buf))
    sys.stdout.write(mp3Buf)
    sys.exit()

if __name__ == "__main__":

    USELESS = "__MACOS"
    SCRIPT  = "testAudio.py"

    try:
        zipf = zipfile.ZipFile("d:/cdr/Audio_from_CIPSFTP/Week_09.zip")
    except Exception as info:
        cdrcgi.bail("zipfile.ZipFile error: %s" % str(info))

    # Request for audio?
    fields = cgi.FieldStorage()
    mp3File = fields.getvalue("mp3", None)
    if mp3File is not None:
        # Send and exit
        sendMp3(zipf, mp3File)

    xlsName = None
    names = zipf.namelist()
    for name in names:
        if name.endswith(".xls"):
            if name.startswith("__MA"):
                continue
            xlsName = name
            break
    if xlsName is None:
        cdrcgi.bail(".xls file not found in zipfile")

    # Open with mode='U' = "universal newline support".  Same as "rb"?
    #  apparently not.
    xlsBytes = None
    try:
        xlsBytes = zipf.open(xlsName, 'r').read()
    except Exception as info:
        cdrcgi.bail("zipf.read error: %s" % str(info))
    try:
        zipf.close()
    except Exception as info:
        cdrcgi.bail("zipf.close error: %s" % str(info))

    if not xlsBytes:
        cdrcgi.bail("zipfile read produced no bytes")


    # Prepare an html doc
    html = """
    <html>
    <body>
    <table>
    """

    # Open the spreadsheet
    try:
        book = ExcelReader.Workbook(fileBuf=xlsBytes)
    except Exception as info:
        cdrcgi.bail("ExcelReader.Workbook contructor error: %s" % str(info))

    # Extract spreadsheet stuff of interest
    sheet = book[0]
    if not sheet:
        cdrcgi.bail("No worksheet found in spreadsheet")

    for row in sheet.rows:
        html += "<tr>"
        for cell in row.cells:
            html += " <td>"
            if cell.col == 4:
                html += "  <a href='%s?mp3=%s'>%s</a>" % (SCRIPT,
                                                          cell.val, cell.val)
            else:
                html += "  %s" % cell.val
            html += " </td>\n"

    html += "</body></html>\n"

    cdrcgi.sendPage(html)


