import cdr
import cdrdb
import cdrcgi
import cgi
import datetime

class Control:
    def __init__(self):
        cursor = cdrdb.connect().cursor()
        fields = cgi.FieldStorage()
        query = cdrdb.Query("grp", "id", "name").order("name")
        rows = query.execute(cursor).fetchall()
        self.groups = [Group(cursor, id, name) for id, name in rows]
        query = cdrdb.Query("usr", "id", "fullname").order("fullname")
        query.where("expired IS NULL")
        query.where("(password IS NULL OR password = '')")
        rows = query.execute(cursor).fetchall()
        self.users = [User(id, name) for id, name in rows]
        #session = cdrcgi.getSession(fields)
        self.excel = fields.getvalue("fmt") == "excel"
        #self.users = []
        #for name in cdr.getUsers(session):
        #    user = cdr.getUser(session, name)
        #    if user == "CdrGuest" or user.authMode != "local":
        #        self.users.append(user)
        #self.groups = cdr.getGroups(session)
    def report(self):
        columns = [cdrcgi.Report.Column("")]
        columns.extend([cdrcgi.Report.Column(u.name) for u in self.users])
        rows = [group.row(self.users) for group in self.groups]
        #for group in self.groups:
        #    row = [cdrcgi.Report.Cell(group, bold=True)]
        #    for user in self.users:
        #        row.append((group in user.groups) and "X" or "")
        #    rows.append(row)
        table = cdrcgi.Report.Table(columns, rows)
        report = cdrcgi.Report("CDR Group Membership", [table],
                               banner="CDR Group Membership",
                               subtitle=str(datetime.date.today()))
        report.send(self.excel and "excel" or "html")
class Group:
    def __init__(self, cursor, id, name):
        self.id = id
        self.name = name
        query = cdrdb.Query("grp_usr", "usr")
        query.where(query.Condition("grp", id))
        self.members = set([row[0] for row in query.execute(cursor).fetchall()])
    def row(self, users):
        rows = [cdrcgi.Report.Cell(self.name, bold=True)]
        for user in users:
            rows.append(user.id in self.members and "X" or "")
        return rows
class User:
    def __init__(self, id, name):
        self.id = id
        self.name = name
Control().report()
