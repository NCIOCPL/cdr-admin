"""
Create a login session for a vetted NIH domain user account

Extraction of just enough functionality from the CDR API to be able
to connect to the CDR database and create a CDR login session. We
haven't figured out all the details of what's going on, but with
Windows authentication mode enforced on the cgi-bin/secure directory,
IIS runs into one or both of the following problems, depending on the
user account whose credentials are supplied for the script request:

 * unable to load modules from %PYTHONPATH% (permissions problems?)
 * unable to load the full cdr.py from anywhere (insufficient permission
   to invoke the Windows CryptoGen API calls, which are used for
   the random module, which is imported by the cgi module, which the
   cdr module uses)

See https://tracker.nci.nih.gov/browse/WEBTEAM-5879

So this module has no dependencies on any CDR libraries.

JIRA::OCECDR-3849
"""

import os
import string
import time
import adodbapi


class DatabaseWrapper:

    CDRSQLACCOUNT = "cdrsqlaccount"
    DB = "CDR"
    APPHOSTS = "{}:/etc/cdrapphosts.rc"
    TIER = "{}:/etc/cdrtier.rc"
    PASSWORDS = "{}:/etc/cdrdbpw"
    PORTS = "{}:/etc/cdrdbports"
    LETTERS = string.ascii_uppercase + string.digits
    SELECT = "SELECT ABS(CHECKSUM(NewId())) % {:d}".format(len(LETTERS))

    @property
    def conn(self):
        if not hasattr(self, "_conn"):
            parms = {
                "Provider": "SQLOLEDB",
                "Data Source": "{},{}".format(self.host, self.port),
                "Initial Catalog": self.DB,
                "User ID": self.CDRSQLACCOUNT,
                "Password": self.password
            }
            parms = ";".join(["{}={}".format(*p) for p in parms.items()])
            self._conn = adodbapi.connect(parms)
        return self._conn

    @property
    def cursor(self):
        if not hasattr(self, "_cursor"):
            self._cursor = self.conn.cursor()
        return self._cursor

    @property
    def drive(self):
        if not hasattr(self, "_drive"):
            self._drive = None
            for letter in "DCEFGHIJKLMNOPQRSTUVWXYZ":
                if os.path.exists(self.APPHOSTS.format(letter)):
                    self._drive = letter
                    return letter
        if self._drive is None:
            raise Exception("CDR host file not found")
        return self._drive
            
    @property
    def tier(self):
        if not hasattr(self, "_tier"):
            with open(self.TIER.format(self.drive)) as fp:
                self._tier = fp.read().strip().upper()
        return self._tier

    @property
    def host(self):
        if not hasattr(self, "_host"):
            self._host = None
            key = "CBIIT:{}:DBWIN".format(self.tier)
            with open(self.APPHOSTS.format(self.drive)) as fp:
                for line in fp:
                    if line.startswith(key):
                        pieces = line.strip().split(":")
                        hosting, tier, role, localname, domain = pieces
                        self._host = ".".join((localname, domain))
                        return self._host
        if self._host is None:
            raise Exception("Database host not found")
        return self._host

    @property
    def port(self):
        if not hasattr(self, "_port"):
            self._port = None
            key = "{}:CDR".format(self.tier)
            with open(self.PORTS.format(self.drive)) as fp:
                for line in fp:
                    if line.upper().startswith(key):
                        tier, db, port = line.strip().split(":")
                        self._port = int(port)
                        return self._port
        if self._port is None:
            raise Exception("Database port not found")
        return self._port

    @property
    def password(self):
        if not hasattr(self, "_password"):
            self._password = None
            key = "CBIIT:{}:CDR:CDR".format(self.tier)
            with open(self.PASSWORDS.format(self.drive)) as fp:
                for line in fp:
                    if line.upper().startswith(key):
                        pieces = line.strip().split(":", 4)
                        hosting, tier, db, user, password = pieces
                        self._password = password
                        return password
        if self._password is None:
            raise Exception("Database credentials not found")
        return self._password

    def generate_random_string(self, length):
        """
        Let SQL Server do the random number generation

        This avoids the problems described above when trying to load the
        Python CryptoGen API calls, which are used for the random module.
        """
        return "".join([self.__pick_character() for _ in range(length)])

    def __pick_character(self):
        self.cursor.execute(self.SELECT)
        row = self.cursor.fetchone()
        return self.LETTERS[row[0]]


def login(user_name):
    """
    Create CDR session for user whose NIH domain account has been vetted
    """

    db = DatabaseWrapper()
    db.cursor.execute("""\
SELECT id
  FROM usr
 WHERE name = ?
   AND expired IS NULL""", (user_name,))
    row = db.cursor.fetchone()
    if not row:
        raise Exception("Unknown or expired user")
    uid = row.id
    secs, msecs = [int(n) for n in "{:.9f}".format(time.time()).split(".")]
    secs = secs & 0xFFFFFFFF
    msecs = msecs & 0xFFFFFF
    suffix = db.generate_random_string(12)
    name = "{:08X}-{:06X}-{:03d}-{}".format(secs, msecs, uid, suffix)
    cols = "name, usr, comment, initiated, last_act, ip_address"
    vals = "?, ?, 'Login through IIS secure page', GETDATE(), GETDATE(), ?"
    insert = "INSERT INTO session({}) VALUES({})".format(cols, vals)
    db.cursor.execute(insert, (name, uid, os.environ.get("REMOTE_ADDR")))
    db.conn.commit()
    return name
