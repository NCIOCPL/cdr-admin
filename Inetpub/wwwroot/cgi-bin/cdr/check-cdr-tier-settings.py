#----------------------------------------------------------------------
#
# $Id$
#
# Sanity check for CDR configuration files for a given CBIIT tier.
#
#----------------------------------------------------------------------
import cdrcgi
import cdr
import cdrdb
import cdrutil
import re
import socket
import urllib2

MYSQL_PORT = cdr.h.tier == "QA" and 3631 or 3600
SQL_SERVER_PORTS = { "PROD": 55733, "STAGE": 55459, "QA": 53100 }
ROLES = {
    "APP": 22,
    "APPC": 443,
    "APPWEB": 443,
    "DBNIX": MYSQL_PORT,
    "DBWIN": SQL_SERVER_PORTS.get(cdr.h.tier, 55373),
    "BASTION": None,
    "BASTIONC": None,
    "GLOSSIFIER": 22,
    "GLOSSIFIERC": 80,
    "GLOSSIFIERWEB": 80,
    "GLOSSIFIERDB": MYSQL_PORT,
    "EMAILERS": 22,
    "EMAILERSC": 443,
    "EMAILERSWEB": 443,
    "EMAILERSDB": MYSQL_PORT,
    "SFTP": 22,
    "GK": 80,
    "CG": 80,
    "CGMOBILE": 80
}

DATABASES = {
    "cdr": ("cdrsqlaccount", "CdrPublishing", "CdrGuest"),
    "dropbox": ("dropbox",),
    "glossifier": ("glossifier",),
    "emailers": ("emailers",),
}
CHECKMARK_TD = cdrcgi.Page.B.TD(
    cdrcgi.Page.B.IMG(src="/images/checkmark.gif", alt="check mark"),
    cdrcgi.Page.B.CLASS("center"))

def checkmark(cell, output):
    return CHECKMARK_TD
CHECK = cdrcgi.Report.Cell("", callback=checkmark)

def custom_style(table, page):
    page.add_css("""\
xxtable caption { border: none; border-bottom: 2px solid white; }""")

def db_account_ok(db, account):
    try:
        if db == "cdr":
            conn = cdrdb.connect(account)
            #conn.close()
        else:
            conn = cdrutil.getConnection(db)
            #conn.close()
        return True
    except:
        #raise
        return False

def error(message):
    return cdrcgi.Report.Cell(str(message), classes="error")

class Host:
    checked = set()
    def __init__(self, role):
        self.aname = self.ip = self.dns = self.error = None
        self.info = cdr.h.host.get(role)
        if not self.info:
            self.error = "MISSING"
        else:
            self.dns = ("%s.%s" % self.info).rstrip(".")
            try:
                self.ip = socket.gethostbyname(self.dns)
                try:
                    port = ROLES.get(role)
                    if port:
                        key = (self.dns, port)
                        if key not in Host.checked:
                            conn = socket.create_connection(key)
                            conn.close()
                            Host.checked.add(key)
                except:
                    self.error = "CONNECTION REFUSED"
            except:
                self.error = "NOT FOUND"
        #response = cdr.runCommand("d:\\cygwin\\bin\\host %s" % self.dns)
        #if not response.code:
        #    match = re.search("\\S is an alias for (\\S+)", response.output)
        #    if match:
        #        self.aname = match.group(1).rstrip(".")
        #    else:
        #        self.aname = self.dns
        #    match = re.search("\\S has address (\\S+)", response.output)
        #    if match:
        #        self.ip = match.group(1)

R = cdrcgi.Report
#cursor = cdrdb.connect('CdrGuest').cursor()
host_columns = (
    R.Column("Role", width="125px"),
    R.Column("Name", width="300px"),
    R.Column("IP Address"),
    R.Column("Status")
)
rows = []
tables = []
for role in sorted(ROLES):
    try:
        host = Host(role)
        if host.error:
            status = error(host.error)
        else:
            status = CHECK
        rows.append((role, host.dns or "", host.ip or "", status))
    except Exception, e:
        rows.append((role, "", "", error(e)))
tables.append(R.Table(host_columns, rows,
                      caption='Host Name Mappings on Windows Server',
                      html_callback_pre=custom_style))
db_columns = (
    R.Column("Database", width="125px"),
    R.Column("Account", width="200px"),
    R.Column("Status")
)
rows = []
for db in sorted(DATABASES):
    for account in DATABASES[db]:
        if db_account_ok(db, account):
            status = CHECK
        else:
            status = error("LOGIN FAILED")
        rows.append((db, account, status))
tables.append(R.Table(db_columns, rows,
                      caption='Database Credentials on Windows Server'))
def check_server(name, tables):
    role = "%sC" % name.upper()
    port = ROLES[role]
    proto = port == 80 and "http" or "https"
    host = cdr.h.host.get("%sC" % name.upper())
    host = "%s.%s" % host
    url = "%s://%s/cgi-bin/check-cdr-tier-settings.py" % (proto, host)
    conn = urllib2.urlopen(url)
    roles, accounts = eval(conn.read())
    rows = []
    for role, dns, ip, status in roles:
        if status:
            status = error(status)
        else:
            status = CHECK
        rows.append((role, dns, ip, status))
    tables.append(R.Table(host_columns, rows,
                          caption="Host Name Mappings on %s Server" % name))
    rows = []
    for db, account, ok in accounts:
        if ok:
            status = CHECK
        else:
            status = error("LOGIN FAILED")
        rows.append((db, account, status))
    tables.append(R.Table(db_columns, rows,
                          caption="Database Credentials on %s Server" % name))

for server in ("Glossifier", "Emailers"):
    try:
        check_server(server, tables)
    except:
        raise
        pass

report = R('Tier Report', tables, banner="%s Tier Check" % cdr.h.tier)
report.send('html')
