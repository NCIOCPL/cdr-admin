#----------------------------------------------------------------------
# Sanity check for CDR configuration files for a given CBIIT tier.
#----------------------------------------------------------------------
import cdrcgi
import re
import socket
import requests
from cdrapi import db as cdrdb
from cdrapi.settings import Tier

TIER = Tier()
SQL_SERVER_PORT = TIER.port("cdr")
ROLES = {
    "APPC": 443,
    "APPWEB": 443,
    "DBWIN": SQL_SERVER_PORT,
    "SFTP": 22,
    "CG": 443,
    "DRUPAL": 443,
}

DATABASES = {
    "cdr": ("cdrsqlaccount", "CdrPublishing", "CdrGuest"),
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

def db_account_ok(database, account):
    try:
        conn = cdrdb.connect(user=account, database=database)
        return True
    except:
        return False

def error(message):
    return cdrcgi.Report.Cell(str(message), classes="error")

class Host:
    checked = set()
    def __init__(self, role):
        self.aname = self.ip = self.dns = self.error = None
        self.info = TIER.hosts.get(role)
        if not self.info:
            self.error = "MISSING"
        else:
            self.dns = self.info.rstrip(".")
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

R = cdrcgi.Report
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
    except Exception as e:
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
    host = TIER.hosts.get("%sC" % name.upper())
    url = "%s://%s/cgi-bin/check-cdr-tier-settings.py" % (proto, host)
    response = requests.get(url)
    roles, accounts = eval(response.content)
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

report = R('Tier Report', tables, banner="%s Tier Check" % TIER.name)
report.send('html')
