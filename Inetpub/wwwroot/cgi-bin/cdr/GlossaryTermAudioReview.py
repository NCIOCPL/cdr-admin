#----------------------------------------------------------------------
# Support review of audio pronunciations for Glossary terms in English
# and Spanish.
#----------------------------------------------------------------------
import cgi
import cgitb
import glob
import operator
import os
import sys
import re
import time
import zipfile
import msvcrt
import xlrd
import cdr
import cdrdb
import cdrcgi

cgitb.enable()

# Constants
SCRIPT  = "GlossaryTermAudioReview.py"
HEADER  = "Glossary Term Audio Review"
BUTTONS = (cdrcgi.MAINMENU, "Logout")
ZIPDIR  = "d:/cdr/Audio_from_CIPSFTP"
REVDIR  = "%s/GeneratedRevisionSheets" % ZIPDIR
MAXNOTE = 2040
MAXFILE = 250
MAXTERM = 250
MAXNAME = 250

# Some early zipfiles included some redundant lines with this name prefix
USELESS = "__MACOSX"

# Patterns for parsing filenames:
ZIPPAT  = "%s/Week*zip" % ZIPDIR
NAMEPAT = r"(?P<base>Week_\d{1,3})(?P<rev>_Rev\d{1,3})*.zip"
REVPAT  = "_Rev(?P<num>\d{1,3})"

class TermZipFile:
    """
    Container for all information for one row of the term_audio_zipfiles
    table.
    """
    def __init__(self, zipData):
        """
        Constructor

        Pass:
            zipData - List of values from one term_audio_zipfiles row, or
                      elsewhere.
        """
        self.zipId, self.fname, self.fdate, self.complete = zipData

    def __str__(self):
        return ("zipId=%s   fname=%s   fdate=%s   complete=%s" %
                (self.zipId, self.fname, self.fdate, self.complete))

class TermMp3:
    """
    Container for values pertaining to one row in the term_audio_mp3 table.
    """
    def __init__(self, row):
        self.id            = row[0]
        self.zipfile_id    = row[1]
        self.review_status = row[2]
        self.cdr_id        = int(row[3])
        self.term_name     = row[4]
        self.language      = row[5]
        self.pronunciation = row[6]
        self.mp3_name      = row[7]
        self.reader_note   = row[8]
        self.reviewer_note = row[9]
        self.reviewer_id   = row[10]
        self.review_date   = row[11]

    def __str__(self):
        mp3Str = u"id=%s   zipfile_id=%s   review_status=%s   cdr_id=%s  \n" \
                 "term_name=%s   language=%s  pronunciation=%s  \n" \
                 "mp3_name=%s   reader_note=%s   reviewer_note=%s  \n" \
                 "reviewer_id=%s   review_date=%s\n" % \
                 (self.id, self.zipfile_id, self.review_status, self.cdr_id,
                  self.term_name, self.language, self.pronunciation,
                  self.mp3_name, self.reader_note, self.reviewer_note,
                  self.reviewer_id, self.review_date)

        # For debugging, we may need to write to an ASCII file
        # 'replace' is good enough for debugging
        return mp3Str.encode('ascii', 'replace')


def bail(ctxtMsg, e=None):
    """
    Bail out, producing a debugging message.
    May or may not include an Exception object.

    Pass:
        ctxtMsg - Error context message.
        e       - Exception object of any type.
    """
    msg = "%s:<br />\n" % ctxtMsg
    if e is not None:
        msg += "Exception Type: %s</br />\n" % type(e)
        msg += "Exception msg: %s" % str(e)
    cdrcgi.bail(msg)


def getUserId(session, cursor=None, userName=None):
    """
    Get the internal user id for a session user

    Pass:
        Session
        Cursor, or create one
    """
    if userName is None:
        userName, pw = cdr.idSessionUser(session, session)

    if not cursor:
        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
        except Exception as e:
            bail("Unable to get cursor to fetch userId")

    try:
        cursor.execute("SELECT id FROM usr WHERE name=?", userName)
        userId = cursor.fetchone()[0]
    except Exception as e:
        bail("Unable to get the userId for name='%s'" % userName, e)

    return int(userId)


def getSqlDate(cursor=None):
    """
    Get the date/time from the database.

    Pass:
        Cursor, or create one
    """
    if not cursor:
        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
        except Exception as e:
            bail("Unable to get cursor to fetch userId", e)

    try:
        cursor.execute("SELECT GETDATE()")
        now = cursor.fetchone()[0]
    except Exception as e:
        bail("Unable to get the current datetime", e)

    return now

def loadZipTable():
    """
    Load the complete term_audio_zipfiles table into memory, creating
    a list or dictionary of ZipFile objects.

    There should never be more than hundreds of these, so it's practical
    and efficient to have them in memory.

    Return:
        tuple of:
            Dictionary of zipId -> TermZipFile reference.
            Dictionary of fname -> TermZipFile reference.
        Structures will be empty on first ever call.
    """
    # Query for all files we know about
    sql = "SELECT id,filename,filedate,complete FROM term_audio_zipfile"

    try:
        conn = cdrdb.connect()
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
    except Exception as e:
        bail("Loading records from term_audio_zipfile table", e)

    # Load the desired data structures
    zipIdIndex   = {}
    zipNameIndex = {}
    for row in rows:
        tzf = TermZipFile(row)
        zipIdIndex[tzf.zipId]   = tzf
        zipNameIndex[tzf.fname] = tzf

    return (zipIdIndex, zipNameIndex)


def getZipfileName(zipId):
    """
    Reverse lookup, finds the name of the zip file corresponding to
    a unique id in the term_audio_zipfile table.

    Pass:
        Unique ID.

    Return:
        File name, without path.
    """
    try:
        conn = cdrdb.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM term_audio_zipfile WHERE id = ?",
                       zipId)
        filename = cursor.fetchone()[0]
    except Exception as e:
        bail("Unable to get filename for zip file id=%d" % zipId, e)

    return filename


def loadMp3Table(zipId):
    """
    Load all info from the term_audio_mp3 table into memory for one zip file.
    The zip file data must already have been stored in the database using
    installZipFile().

    Pass:
        Unique ID of the zip file in the table.

    Return:
        Dictionary of mp3id -> TermMp3 object.
    """
    # Load the data
    sql = """
     SELECT id, zipfile_id, review_status, cdr_id,
            term_name, language, pronunciation, mp3_name,
            reader_note, reviewer_note, reviewer_id, review_date
       FROM term_audio_mp3
      WHERE zipfile_id = %d
     """ % zipId
    try:
        conn = cdrdb.connect()
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
    except Exception as e:
        bail("Loading records from term_audio_mp3 table", e)

    # Create a dictionary of id->row
    mp3Index = {}
    for row in rows:
        mpRow = TermMp3(row)
        mp3Index[mpRow.id] = mpRow

    return mp3Index


def insertZipFileRow(cursor, zipName):
    """
    Insert a row into term_audio_zipfile for one zip file.

    Pass:
        Database cursor.
        Name of the zip file, as a full path.

    Return:
        Row id of the newly created row.
    """
    # Get the last modified date of the file
    fullPath = "%s/%s" % (ZIPDIR, zipName)
    try:
        m_seconds = os.path.getmtime(fullPath)
        m_tm      = time.localtime(m_seconds)
        mtime     = time.strftime("%Y-%m-%d %H:%M:%S", m_tm)
    except Exception as e:
        bail("Unable to get mtime for zip file '%s'" % zipName, e)

    try:
        cursor.execute("""
          INSERT term_audio_zipfile
                 (filename, filedate)
          VALUES (?, ?)""", (zipName, mtime))
        cursor.execute("SELECT @@IDENTITY")
        row = cursor.fetchone()
        zipId = int(row[0])
    except Exception as e:
        bail("Error inserting row in term_audio_zipfile", e)

    return zipId


def getCell(sheet, row, col, maxlen=None):
    """
    Extract the value from a cell in the worksheet.

    Pass:
        Sheet instance.
        Row index, origin 0.
        Column index, origin 0.
        Optional length:
            If passed, will trim whitespace and insure maxlen not exceeded.

    Return:
        Value in whatever data type is found.
        If empty string or no cell at all, return None
    """
    try:
        value = sheet.cell(row, col).value
    except (IndexError, ValueError):
        return None

    if maxlen:
        value = value.strip()
        if len(value) > maxlen:
            bail("Input row=%d col=%d value is too long, max=%d.  "
                 "Please check data.")
    return value


def installZipFile(zipName):
    """
    Check to see if a a zip file has been loaded into the term_audio_zipfile
    table.

    If so:
        Return its ID.
    Else:
        Read the contents from disk
        Create an entry for it in the term_audio_zipfile table.
        Create one entry in the term_audio_mp3 table for each mp3 in the file.

    Pass:
        Name of the zip file, without path.

    Return:
        Unique ID of the row created in the term_audio_zipfile table.
    """
    # Connect to the database
    try:
        conn = cdrdb.connect()
        cursor = conn.cursor()
    except Exception as e:
        bail("Unable to connect to installZipFile in database", e)

    # Check to see if we've already done this
    try:
        cursor.execute("""
         SELECT id
           FROM term_audio_zipfile
          WHERE filename = ?
        """, zipName)
        row = cursor.fetchone()
    except Exception as e:
        bail("Unable to search term_audio_zipfile for '%s'" % zipName, e)

    if row and row[0] is not None:
        # This zipfile is already installed
        return row[0]

    # Else file was not already installed.  Open it
    fullPath = "%s/%s" % (ZIPDIR, zipName)
    try:
        zipf = zipfile.ZipFile(fullPath)
    except Exception as e:
        bail("Error opening zipfile '%s'" % fullPath, e)

    # Locate the spreadsheet in the zip archive
    xlsName = None
    names = zipf.namelist()
    for name in names:
        if name.endswith(".xls"):
            if name.startswith(USELESS):
                continue
            xlsName = name
            break
    if xlsName is None:
        bail(".xls file not found in zipfile")

    # Got the spreadsheet name, open the zip file and read the
    #  spreadsheet bytes into a buffer
    xlsBytes = None
    try:
        xlsBytes = zipf.open(xlsName, 'r').read()
    except Exception as e:
        bail("zipf.open/read error", e)
    try:
        zipf.close()
    except Exception as e:
        bail("After reading spreadsheet, zipf.close errors", e)

    if not xlsBytes:
        bail("zipfile read for spreadsheet produced no bytes")

    # Open the spreadsheet
    try:
        book = xlrd.open_workbook(file_contents=xlsBytes)
    except Exception as e:
        bail("xlrd.Workbook constructor error", e)
    if not book:
        bail("Spreadsheet not created")

    # Extract spreadsheet stuff of interest
    sheet = book.sheet_by_index(0)
    if not sheet:
        bail("No worksheet found in spreadsheet")

    # Create re-usable SQL to insert each mp3 row
    mp3sql = """
     INSERT term_audio_mp3
            (zipfile_id, cdr_id, term_name, language, pronunciation, mp3_name,
             reader_note, reviewer_note, reviewer_id, review_date)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
     """

    # Use these for all records
    userId = getUserId(session, cursor)
    now    = getSqlDate(cursor)

    # Point past optional labels on the first line to the first row of data
    rowx = 0
    done = False
    while True:
        try:
            upperLeft = sheet.cell(rowx, 0).value
            num = int(upperLeft)
        except IndexError:
            # Past the end of the rows!
            bail("No data found in spreadsheet!")
        except (ValueError, TypeError) as e:
            # We got something other than the CDR ID, point past it
            rowx += 1
        else:
            # Sanity check (and to silence Pychecker unused variable warning)
            if num < 1:
                bail("Got unexpected CDR ID=%d in first row of spreadsheet."
                      % num)

            # This ought to be the first data row
            break

    # Wrap everything in a transaction
    try:
        conn.setAutoCommit(False)
    except Exception as e:
        bail("Unable to create transaction for zipfile installation", e)

    try:
        # Create the required row in the database
        zipId = insertZipFileRow(cursor, zipName)

        # Walk the spreadsheet, processing each useful mp3 row
        while True:
            # Set default values for all items in spreadsheet
            # Many of these are required, we'll catch an exception from
            #   SQL Server if they aren't there
            cdrId         = None
            termName      = None
            language      = None
            pronunciation = None
            filename      = None
            readerNote    = None
            reviewerNote  = None

            # Load values from the sheet
            try:
                cdrId = int(sheet.cell(rowx, 0).value)
                # cdr.logwrite('got rowx=%d, cdrId=%d' % (rowx, cdrId))
            except IndexError:
                # Past the end of the rows
                # cdr.logwrite('broke on rowx=%d, cdrId=%d' % (rowx, cdrId))
                done = True
                break
            except (ValueError, TypeError) as e:
                # I don't know what to do here.  It could be a bad row
                #  in the middle of the spreadsheet, a blank row in the
                #  middle, a blank row at the end, or a corrupt spreadsheet
                # The one case I've seen is blank row at the end.  I'll
                #  therefore treat it as benign but log it.
                cdr.logwrite('%s: ' % SCRIPT +
                             'Expecting CDR ID integer on row=%d, got "%s"' %
                              (rowx + 1, sheet.cell(rowx, 0).value))
                rowx += 1
                continue

            # Get the rest with less checking
            termName     = getCell(sheet, rowx, 1)
            language     = getCell(sheet, rowx, 2)
            pronunciation= getCell(sheet, rowx, 3)
            filename     = getCell(sheet, rowx, 4)
            readerNote   = getCell(sheet, rowx, 5)
            reviewerNote = getCell(sheet, rowx, 6)

            # Confirm language and fail here if it's wrong
            if language not in ("English", "Spanish"):
                bail("Expecting English or Spanish for CDR ID=%s.  Got %s" %
                      (cdrId, language))

            # Reviewer note requires a kludge for multiple input formats
            # An early version of the spreadsheet had a place for approval
            #   in column 6 with reviewer note in col 7.
            # Later versions have reviewer note in 6
            extra = getCell(sheet, rowx, 7)
            if extra:
                reviewerNote = extra

            # Got everything from this row
            rowx += 1

            # Another kludge for multiple input formats
            # Some filenames have a MAC OSX prefix.  These are redundant
            if filename and filename.startswith(USELESS):
                # Continue without inserting the row
                continue

            # A final test for missing filenames
            if not filename:
                # User has to reject this
                filename = "MISSING!"

            # Insert the row into the table
            try:
                cursor.execute(mp3sql, (zipId, cdrId, termName, language,
                                        pronunciation, filename,
                                        readerNote, reviewerNote,
                                        userId, now))
            except Exception as e:
                bail("Failed to insert row for cdrId=%d, term=%s" %
                     (cdrId, termName), e)

    finally:
        # If we processed all rows successfully, commit both tables
        if done:
            conn.commit()
        else:
            conn.rollback()
        cursor.close()

    return zipId


def updateZipfileCompletion(zipFilename, status):
    """
    Update the status of this zipfile in the term_audio_zipfile table.

    Pass:
        Name of the zip file, without path.
        New status
    """
    try:
        conn = cdrdb.connect()
        cursor = conn.cursor()
        cursor.execute("""
         UPDATE term_audio_zipfile
            SET complete = '%s'
          WHERE filename = '%s'
         """ % (status, zipFilename))
        conn.commit()
        cursor.close()
    except Exception as e:
        bail('Unable to set status on zipfile "%s"' % zipFilename, e)


def updateMp3Row(cursor, mp3obj):
    """
    Update a row in term_audio_mp3 with the latest values.
    Should only be called when the caller knows that something has changed.

    Pass:
        Open database cursor
        TermMp3 object with the latest values
    """
    # DEBUG
    # cdr.logwrite("Updating: %s" % mp3obj)
    mp3Sql = """
      UPDATE term_audio_mp3
         SET review_status = ?,
             reviewer_note = ?,
             reviewer_id   = ?,
             review_date   = ?
       WHERE id = ?"""
    try:
        cursor.execute(mp3Sql, (mp3obj.review_status, mp3obj.reviewer_note,
                                mp3obj.reviewer_id, mp3obj.review_date,
                                mp3obj.id))
    except Exception as e:
        bail("Error updating mp3 row for zipId=%d, cdrId=%d"
              % (mp3obj.zipfile_id, mp3obj.cdr_id), e)


def getZipFileList():
    """
    Get a list of all of the zip files in the zip directory, without paths.

    Return
        List of TermZipFile objects.
    """
    zipList  = []
    nameList = glob.glob(ZIPPAT)
    for name in nameList:
        statInfo = os.stat(name)
        fname    = os.path.split(name)[1]
        fModDate = statInfo.st_mtime
        m_tm     = time.gmtime(fModDate)
        sqlDate  = time.strftime("%Y-%m-%d %H:%M:%S", m_tm)

        # Make a more rigorous test and make the user fix errors
        m = re.match(NAMEPAT, fname)
        if not m:
            bail("""
Found a file named "%s" that is like what we want but not exactly right.<br />
Please correct the name to reflect one of the following formats or contact
programming support staff for help.<br /><br />

  Week_N.zip or Week_N_RevN.zip<br />

where "N" is 1-3 decimal digits with optional leading zeroes.
""" % fname)

        # Create object, default to 'U'nreviewed until we learn otherwise
        tzf = TermZipFile((None, fname, sqlDate, 'U'))
        zipList.append(tzf)

    return zipList


def listZipFiles(session):
    """
    Display a web page of information for all of the zipfiles available
    containing term audio pronunciations.

    Those which have not been completely reviewed are hyperlinked to enable
    a user to select one of them.

    This function does not return to the caller.  It displays the web
    page and exits.
    """

    # Set up the web page
    html = cdrcgi.header(HEADER + " - Select File", HEADER,
                         "Select file to review",
                         script=SCRIPT, buttons=BUTTONS)

    # Instructions and output table column headers
    html += u"""
<p>Click a link to a zip file to review from the table below.  Only those files
that have not yet been completely reviewed are hyperlinked.</p>

<table border='1'>
  <tr>
    <th>File name</th>
    <th>Review status</th>
    <th>Date modified</th>
  </tr>

"""
    # Load what we know about files reviewed so far
    zipIdIndex, zipNameIndex = loadZipTable()

    # Get a list of objects representing zip files on the disk
    fileList = getZipFileList()

    # Sort the list by filename
    nameList = sorted(fileList, key=operator.attrgetter("fname"))

    # Supersort by category,  name is within category
    sortedList = []

    # Started files
    for tzf in nameList:
        if zipNameIndex.has_key(tzf.fname):
            if zipNameIndex[tzf.fname].complete == 'N':
                sortedList.append(tzf)

    # Unreviewed files
    for tzf in nameList:
        if not zipNameIndex.has_key(tzf.fname):
            sortedList.append(tzf)

    # Completed files - all the rest
    for tzf in nameList:
        if zipNameIndex.has_key(tzf.fname):
            if zipNameIndex[tzf.fname].complete == 'Y':
                sortedList.append(tzf)

    # Populate the table
    for tzf in sortedList:

        refName = tzf.fname

        # Has this file been reviewed at all?
        if zipNameIndex.has_key(tzf.fname):

            # We've seen this file before, get all info about it
            tzf = zipNameIndex[tzf.fname]

            # If we haven't completed reviewing, hyperlink database id
            if tzf.complete == 'N':
                refName = "<a href='%s?zipId=%d&%s=%s'>" % \
                            (SCRIPT, tzf.zipId, cdrcgi.SESSION, session) + \
                          "%s</a>" % tzf.fname
        else:
            # Hyperlink name, using the filename
            refName = "<a href='%s?zipName=%s&%s=%s'>" % \
                       (SCRIPT, tzf.fname, cdrcgi.SESSION, session) + \
                      "%s</a>" % tzf.fname

        # Interpret review status for user
        revStatus = "Unreviewed"
        if tzf.complete == 'Y':
            revStatus = "Completed"
        elif tzf.complete == 'N':
            revStatus = "Started"

        # Add it to the table
        html += "   <tr>\n" \
                "    <td>%s</td>\n" % refName + \
                "    <td>%s</td>\n" % revStatus + \
                "    <td>%s</td>\n" % tzf.fdate + \
                "   </tr>\n"

    # Termination
    html += """
 </table>
 <input type='hidden' name='%s' value='%s' />
</form>
</body>
</html>
""" % (cdrcgi.SESSION, session)

    cdrcgi.sendPage(html)


def escape(str):
    """
    cgi.escape a value, or return "" for an empty value.
    """
    val = ""
    if str:
        val = cgi.escape(str, True)
    return val


def makeOneMp3FormRow(mp3obj, zipFilename):
    """
    Create HTML for the display of one single spreadsheet/database row
    for an mp3 file.

    Pass:
        TermMp3 object for the row.
        Name of the zip file containing it, used in a hyperlink.

    Return:
        HTML string for one row of a table.
    """
    # We'll use the database row ID a lot
    mId = mp3obj.id

    # Create the review form controls
    acheck = rcheck = ucheck = ""
    if mp3obj.review_status == 'A': acheck = " checked='1'"
    if mp3obj.review_status == 'R': rcheck = " checked='1'"
    if mp3obj.review_status == 'U': ucheck = " checked='1'"

    html = u"""
 <tr><td>
  <input type='radio' name='appr%d' value='A'%s />
  <input type='radio' name='appr%d' value='R'%s />
  <input type='radio' name='appr%d' value='U'%s />
 </td>
""" % (mId, acheck, mId, rcheck, mId, ucheck)

    # CDR ID
    html += u"  <td>%d</td>\n" % mp3obj.cdr_id

    # Term name
    html += u" <td>%s</td>\n" % mp3obj.term_name

    # Language
    html += u"  <td>%s</td>\n" % mp3obj.language

    # Pronunciation
    html += u"  <td>%s</td>\n" % (escape(mp3obj.pronunciation) or "&nbsp;")

    # mp3 filename, hyprlinked to allow user to hear it
    val = escape(mp3obj.mp3_name)
    html += u"  <td><a href='%s?mp3=%d&zName=%s'>%s</a></td>\n" % \
               (SCRIPT, mp3obj.id, zipFilename, val)

    # Note from the reader (currently Vanessa)
    html += u"  <td>%s</td>\n" % (escape(mp3obj.reader_note) or "&nbsp;")

    # Place to add or update reviewer's note, and row close
    html += \
u"""  <td><textarea name="revNote%d" rows="1" cols="40">%s</textarea>
  </td>
 </tr>
""" % (mId, escape(mp3obj.reviewer_note))

    return html


def listMp3ByStatus(mp3List, revStatus):
    """
    Filter a list, selecting just those objects that have the passed
    rev_status.

    Pass:
        List of TermMp3 objects to filter.
        Review status to select for.

    Return:
        New list of just those objects with the desired status.
        May be empty if there aren't any.
    """
    newList = []
    for mp3obj in mp3List:
        if mp3obj.review_status == revStatus:
            newList.append(mp3obj)

    return newList


def sendMp3(mp3Id):
    """
    Send the mp3 file found in the zipfile to the user's browser.

    Pass:
        Unique ID of the mp3 row in term_audio_mp3
    """
    # Find the stored zip and mp3 filenames in the database
    try:
        conn = cdrdb.connect()
        cursor = conn.cursor()
        cursor.execute("""
         SELECT zip.filename, mp3.mp3_name
           FROM term_audio_zipfile AS zip
           JOIN term_audio_mp3 AS mp3
             ON zip.id = mp3.zipfile_id
          WHERE mp3.id = ?
         """, mp3Id)
        row = cursor.fetchone()
    except Exception as e:
        bail("Unable to get zipfile name + mp3 file name for id=%d" % mp3Id, e)

    # zipName needs a path, mp3Name already has one
    zipName = "%s/%s" % (ZIPDIR, row[0])
    mp3Name = row[1]

    # Load the zip file and open it for reading
    try:
        zipf = zipfile.ZipFile(zipName)
    except Exception as e:
        bail("Failed to read mp3 file named '%s'" % zipName, e)

    # Unzip the mp3 file from the zip file
    try:
        mp3Buf = zipf.read(mp3Name)
    except Exception as e:
        bail("Failed to read mp3 file named '%s'" % mp3Name, e)

    # Write binary mp3 audio data back to the browser
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    sys.stdout.write("Content-Type: audio/mpeg\r\n")
    sys.stdout.write("Content-disposition: inline; filename=%s\n\n" % mp3Name)
    sys.stdout.write("Content-Length: %d\r\n" % len(mp3Buf))
    sys.stdout.write(mp3Buf)
    sys.exit()


def showZipfile(zipId, session):
    """
    Show all mp3 info for a single zipfile / spreadsheet.  Include
    form controls that allow a user to download the mp3 file to his
    browser configured player, and to set the approval status for
    the mp3 to accepted, rejected, or unreviewed (removing an accepted
    or rejected status.)

    Pass:
        The ID for a term_audio_zipfile row.

    Return:
        No return, sends a page to the browser.
    """
    # Load all info for this zipfile
    zipIdIndex = loadMp3Table(zipId)
    zipFilename = getZipfileName(zipId)

    # Prepare an output web page
    html = []
    buttons = ("Save", "Cancel")
    html.append(cdrcgi.header(HEADER + " - Review MP3 Files", HEADER,
                              "Review and approve or reject mp3 files",
                              script=SCRIPT, buttons=buttons))

    html.append(u"""
<p>Click a hyperlinked mp3 filename to play the sound in your browser
configured mp3 player (already reviewed files are at the bottom of the list
of files.)</p>
<p>Use the radio buttons to approve or reject a file.</p>
<p>When finished, click "Save" to save any changes to the database.  If all
files in the set have been reviewed and any have been rejected, a
spreadsheet containing rejected terms will be created and displayed on
your workstation.  Please save it for future use.
</p>

<table border='1' style='empty-cells: show'>
<tr>
 <th>Approve<br />
     &nbsp; Reject<br />
     &nbsp; &nbsp; None</th>
 <th>CDR ID</th>
 <th>Term name</th>
 <th>Lang</th>
 <th>Pronunciation</th>
 <th>MP3 file</th>
 <th>Reader note</th>
 <th>Reviewer note</th>
</tr>
""")

    # Sort the terms for display
    #   By approval status: 'U', 'R', 'A'
    #      By CDR ID
    #         By language
    unsortedList = zipIdIndex.values()
    mp3List      = []

    for status in ('U', 'R', 'A'):
        partList = listMp3ByStatus(unsortedList, status)
        mp3List += sorted(partList,
                          key=operator.attrgetter("cdr_id", "language"))

    # Append each one in the sorted list to our html
    for mp3obj in mp3List:
        html.append(makeOneMp3FormRow(mp3obj, zipFilename))

    # Add footers
    html.append("""
</table>
<input type="hidden" name="ReviewedZipfileId" value="%d" />
<input type="hidden" name="%s" value="%s" />
</form>
</body>
</html>
""" % (zipId, cdrcgi.SESSION, session))

    finalHtml = u"".join(html)

    cdrcgi.sendPage(finalHtml)


def isReviewComplete(mp3List):
    """
    Have all mp3 files been reviewed?

    Pass:
        List of TermMp3 objects in the reviewed zip file.

    Return:
        True  = All have been reviewed.
        False = One or more remain to review.
    """
    for mp3obj in mp3List:
        if mp3obj.review_status == 'U':
            return False
    return True


def saveChanges(fields, session):
    """
    Process form fields after a Save request.
    If any approvals or note fields changed, update them on disk.

    Pass:
        CGI form fields.
        CDR client session to find user id.

    Return:
        True  = Some changes were made.
        False = No changes.
    """
    # Get all of the database info corresponding to the submitted data
    zipId    = int(fields.getvalue("ReviewedZipfileId"))
    mp3index = loadMp3Table(zipId)
    mp3List  = mp3index.values()

    # Get SQL Server connection and datetime stamp for updates.
    try:
        conn = cdrdb.connect()
        cursor = conn.cursor()
    except Exception as e:
        bail("Unable to connect to SQL Server to save changes", e)

    # Get the internal CDR user ID
    userId = getUserId(session, cursor)

    # Database date to use in all saves (so they don't differ by milliseconds)
    now = getSqlDate(cursor)

    # Easiest way to process the form is to walk through the in-memory
    #  objects and then query the form fields for the submitted values
    for mp3obj in mp3List:
        # Get values from the form for this object
        mId = mp3obj.id
        revStatus = fields.getvalue("appr%d" % mId)
        revNote   = fields.getvalue("revNote%d" % mId, None)

        # User may have input utf-8 Spanish chars in reviewer note
        if revNote:
            # Fix character set and remove leading/trailing whitespace
            revNote = revNote.decode('utf-8', 'replace').strip()

            # Fix whitespace and newline translation problems
            # DEBUG cdr.logwrite('revNote="%s"' % revNote)
            revNote = re.sub(r"[\r\n]+", "\n", revNote).strip()

            # Limit the length for database input
            if len(revNote) > MAXNOTE:
                revNote = revNote[:MAXNOTE]

        # Compare
        if revStatus != mp3obj.review_status or \
             revNote != mp3obj.reviewer_note:

            # Update the object
            mp3obj.review_status = revStatus
            mp3obj.reviewer_note = revNote
            mp3obj.review_date   = now
            mp3obj.reviewer_id   = userId

            # Update on disk
            updateMp3Row(cursor, mp3obj)

    # Changes go in regardless of whether subsequent processing fails
    conn.commit()

    # If processing is complete, perform end of review processing
    if isReviewComplete(mp3List):
        zipFilename = getZipfileName(zipId)
        doneZipfileReview(session, zipFilename, mp3List)

    # Else go back to reviewing the same page
    showZipfile(zipId, session)


def doneZipfileReview(session, oldZipName, mp3List):
    """
    Update the status of a spreadsheet to show completion.
    Create a spreadsheet for rejected term recordings if required.

    Pass:
        Name of the spreadsheet for which these are rejects.
        List of TermMp3 objects containing possible rejects.

    Return:
        Logged in session.
        If any rejects found, writes the spreadsheet and sends it to the
           user's browser.
        Else displays a message that all recordings were approved.
    """
    # Construct a new spreadsheet based on the old one
    m = re.match(NAMEPAT, oldZipName)
    if not m:
        bail('The filename "%s" doesn\'t match the expected pattern')
    basePrefix = m.group("base")
    revSuffix  = m.group("rev")
    if not revSuffix:
        # File will contain rejects from an original zip file.
        newXlsName = basePrefix + "_Rev1"
    else:
        # File wil contain rejects from a revised file
        m = re.match(REVPAT, revSuffix)
        if not m:
            bail('Badly formed revision number in "%s"' % oldZipName)
        revNum = int(m.group("num"))
        newXlsName = "%s_Rev%d" % (basePrefix, revNum + 1)

    # Spreadsheet filename is the .xls name plus ".xls"
    newXlsFileName = "%s.xls" % newXlsName

    # Create the output spreadsheet objects
    styles = cdrcgi.ExcelStyles()
    sheet = styles.add_sheet("Term Names")

    # Set the column widths
    widths = (10, 30, 10, 30, 30, 20, 30)
    for col, chars in enumerate(widths):
        sheet.col(col).width = styles.chars_to_width(chars)

    # Column labels
    headers = ("CDR ID", "Term Name", "Language", "Pronunciation",
               "Filename", "Notes (Vanessa)", "Notes (NCI)")
    assert(len(headers) == len(widths))
    for i, header in enumerate(headers):
        sheet.write(0, i, header, styles.header)

    # First row for data after labels
    row = 1

    # Haven't found any rejected mp3s yet
    haveRejects = False

    # Check each record, saving the rejected ones in the spreadsheet
    for mp3obj in mp3List:
        if mp3obj.review_status == 'R':
            # Construct new mp3 filename
            if mp3obj.language == "English":
                isoLang = "en"
            elif mp3obj.language == "Spanish":
                isoLang = "es"
            else:
                bail("Unsupported language name=%s for CDR ID=%s" %
                      (mp3obj.language, mp3obj.cdr_id))
            new_mp3_name = "%s/%d_%s.mp3" % (newXlsName,
                                             mp3obj.cdr_id, isoLang)

            # Add the row
            sheet.write(row, 0, mp3obj.cdr_id)
            sheet.write(row, 1, mp3obj.term_name)
            sheet.write(row, 2, mp3obj.language)
            sheet.write(row, 3, mp3obj.pronunciation)
            sheet.write(row, 4, new_mp3_name)
            sheet.write(row, 5, mp3obj.reader_note)
            sheet.write(row, 6, mp3obj.reviewer_note)

            row += 1
            haveRejects = True

    # If there were no rejects, we're done
    # cdr.logwrite("doneZipfileReview found no rejects")
    if not haveRejects:
        html = cdrcgi.header(HEADER + " - Processing complete", HEADER,
                         "Proccessing of this file is complete",
                         script=SCRIPT, buttons=["Continue",]) + \
u"""
<p>All %d mp3 files in the zip file named "%s" have been reviewed and
approved.</p>

<p>No revision spreadsheet is required or has been produced.</p>

<p>Review of the zip file is now completed and closed.</p>

<p>Please press the continue button to return to the list of zip files
for review.</p>

<input type="hidden" name="%s" value="%s" />
</form>
</body>
</html>
""" % (len(mp3List), oldZipName, cdrcgi.SESSION, session)
        # No output file needed but update the status
        updateZipfileCompletion(oldZipName, 'Y')

        # We're done
        cdrcgi.sendPage(html)

    # Save the file to our special directory
    try:
        fp = open("%s/%s" % (REVDIR, newXlsFileName), "wb")
    except Exception as e:
        bail('Unable to open "%s" for output' % newXlsFileName, e)
    try:
        styles.book.save(fp)
    except Exception as e:
        bail('Unable to write spreadsheet "%s"' % newXlsFileName, e)

    # We've saved an output file, update the status to completed
    updateZipfileCompletion(oldZipName, 'Y')

    # Download the spreadsheet to the user's workstation
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    sys.stdout.write("Content-Type: application/vnd.ms-excel\r\n")
    sys.stdout.write("Content-disposition: attachment; filename=%s\n\n" %
                      newXlsFileName)
    styles.book.save(sys.stdout)
    sys.exit()


#----------------------------------------------------------
#  MAIN
#----------------------------------------------------------
if __name__ == "__main__":

    # Defaults
    session = None
    request = None      # Submit button value
    zipName = None      # Name of a zipfile, without path
    zipId   = None      # Id of a row in term_audio_zipfile
    mp3Id   = None      # Id of a row in term_audio_mp3

    # Parse form variables
    fields = cgi.FieldStorage()
    if fields:

        # If user wants to hear an mp3 file, we won't require authentication
        # Just send it to him, leaving the browser still on the same page
        mp3Id = fields.getvalue("mp3", None)
        if mp3Id:
            sendMp3(mp3Id)

        # Establish user session and authorization
        session = cdrcgi.getSession(fields)
        if not session:
            cdrcgi.bail ("Unknown or expired CDR session")
        if not cdr.canDo (session, "REVIEW TERM AUDIO"):
            cdrcgi.bail ("User not authorized to review term audio files")

        # The following fields tell us what to do
        request = cdrcgi.getRequest(fields)
        zipName = fields.getvalue("zipName", None)
        zipIdStr= fields.getvalue("zipId", None)
        if zipIdStr:
            zipId = int(zipIdStr)

    # XXX DEBUG
    # cdr.logwrite("request=%s zipName=%s zipIdStr=%s" %
    #              (request, zipName, zipIdStr))

    # If here for the first time (no fields), show available files
    if not fields:
        listZipFiles(session)

    # Back to admin?
    elif request == cdrcgi.MAINMENU:
        cdrcgi.navigateTo("Admin.py", session)

    elif request == "Logout":
        cdrcgi.navigateTo("Logout.py", session)

    # Cancel display of a spreadsheet set
    elif request == "Cancel":
        listZipFiles(session)

    # User saving changes for one zipfile
    elif request == "Save":
        saveChanges(fields, session)

    # Specific zipfile display requested by name
    elif zipName is not None:
        zipId = installZipFile(zipName)
        showZipfile(zipId, session)
    # By ID
    elif zipId is not None:
        showZipfile(zipId, session)

    # Default if nothing else, or completed everything else (Continue button)
    listZipFiles(session)
