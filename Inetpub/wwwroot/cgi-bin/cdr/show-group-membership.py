import cdr
from cdrapi import db
import cdrcgi
import cgi
import datetime

class Control:

    def __init__(self):
        cursor = db.connect().cursor()
        fields = cgi.FieldStorage()
        query = db.Query("grp", "id", "name").order("name")
        rows = query.execute(cursor).fetchall()
        self.groups = [Group(cursor, id, name) for id, name in rows]
        query = db.Query("usr", "id", "name", "fullname")
        query.where("expired IS NULL")
        query.where("(password IS NULL OR password = '')")
        rows = query.execute(cursor).fetchall()
        self.users = sorted([User(row) for row in rows])
        self.excel = fields.getvalue("fmt") == "excel"

    def report(self):
        columns = [cdrcgi.Report.Column("")]
        columns.extend([cdrcgi.Report.Column(u.name) for u in self.users])
        rows = [group.row(self.users) for group in self.groups]
        table = cdrcgi.Report.Table(columns, rows)
        report = cdrcgi.Report("CDR Group Membership", [table],
                               banner="CDR Group Membership",
                               subtitle=str(datetime.date.today()))
        report.send(self.excel and "excel" or "html")


class Group:
    def __init__(self, cursor, id, name):
        self.id = id
        self.name = name
        query = db.Query("grp_usr", "usr")
        query.where(query.Condition("grp", id))
        self.members = set([row[0] for row in query.execute(cursor).fetchall()])
    def row(self, users):
        rows = [cdrcgi.Report.Cell(self.name, bold=True)]
        for user in users:
            if user.id in self.members:
                rows.append(cdrcgi.Report.Cell("X", center=True))
            else:
                rows.append("")
        return rows


class User:
    def __init__(self, row):
        self.__row = row
    @property
    def name(self):
        if not hasattr(self, "_name"):
            self._name = self.__row.name
            if self.__row.fullname:
                self._name = f"{self._name} ({self.__row.fullname})"
        return self._name
    @property
    def id(self):
        return self.__row.id
    def __lt__(self, other):
        return self.name < other.name


Control().report()
