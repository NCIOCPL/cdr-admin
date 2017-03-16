#!/usr/bin/python
#----------------------------------------------------------------------
# Report on jobs managed by the Microsoft Windows scheduler.
#----------------------------------------------------------------------
import lxml.etree as etree
import re
import cgi
import os
import time

REPORT = "d:/cdr/Reports/schtasks.xml"

def serialize(node):
    string = etree.tostring(node)
    return string.replace("\r", "").replace("\n\n", "\n")

def local(node):
    return re.sub("{.*}", "", node.tag)

class Tag(object):
    NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
    def __getattribute__(self, name):
        return "{%s}%s" % (Tag.NS, name)
TAG = Tag()

class Trigger:
    def __init__(self, node):
        self.node = node
        self.start = self.limit = self.enabled = self.rep = self.sched = None
        self.interval = None
        for child in node:
            if child.tag == TAG.StartBoundary:
                self.start = child.text
            elif child.tag == TAG.ExecutionTimeLimit:
                self.time_limit = child.text
                limits.add(child.text)
            elif child.tag == TAG.Enabled:
                self.enabled = child.text.lower() == "true"
            elif child.tag == TAG.ScheduleByWeek:
                self.sched = ScheduleByWeek(child, self)
            elif child.tag == TAG.ScheduleByDay:
                self.sched = ScheduleByDay(child, self)
            elif child.tag == TAG.ScheduleByMonth:
                self.sched = ScheduleByMonth(child, self)
            elif child.tag == TAG.Repetition:
                for interval in child.findall(TAG.Interval):
                    self.interval = interval.text
    def __str__(self):
        if self.interval:
            match = re.match(r"PT(\d+)([HM])", self.interval)
            if match:
                unit = { "H": "hour", "M": "minute" }[match.group(2)]
                if match.group(1) == "1":
                    return "every %s" % unit
                return "every %s %ss" % (match.group(1), unit)
        if not self.sched:
            return "on demand"
            if not self.start:
                return serialize(self.node)
            return "once at %s" % self.start.replace("T", " ")
        if not self.start:
            when = "{unknown time}"
        else:
            start = self.start.split(".")[0]
            when = start[11:-3]
        return "%s at %s" % (self.sched, when)

class ScheduleByWeek:
    def __init__(self, node, trigger):
        self.trigger = trigger
        self.interval = 1
        for child in node.findall(TAG.WeeksInterval):
            self.interval = int(child.text)
        self.days = [local(c) for c in node.findall(TAG.DaysOfWeek + "/*")]
    def __str__(self):
        days = ",".join(self.days)
        if self.interval == 1:
            if len(self.days) == 7:
                return "every day"
            return "every %s" % days
        return "every %s %s" (ordinal(self.interval), days)

class ScheduleByMonth:
    path = "%s/%s" % (TAG.DaysOfMonth, TAG.Day)
    def __init__(self, node, trigger):
        self.trigger = trigger
        self.days = [int(d.text) for d in node.findall(self.path)]
        self.months = [local(c) for c in node.findall(TAG.Months + "/*")]
    def __str__(self):
        days = ",".join([ordinal(d) for d in self.days])
        months = ",".join(self.months)
        if len(self.months) == 12 or not self.months:
            months = "every month"
        return "the %s of %s" % (days, months)

class ScheduleByDay:
    def __init__(self, node, trigger):
        self.trigger = trigger
        self.interval = None
        for child in node:
            if child.tag == TAG.DaysInterval:
                self.interval = int(child.text)
    def __str__(self):
        if self.interval == 1:
            return "every day"
        if self.interval == 2:
            return "every other day"
        return "every %s day" % ordinal(self.interval)

class Email:
    def __init__(self, node):
        self.subject = None
        self.recips = []
        for child in node:
            if child.tag == TAG.Subject:
                self.subject = child.text
            elif child.tag == TAG.To:
                self.recips.append(child.text)
    def __str__(self):
        return 'Send email "%s" to %s' % (self.subject, ",".join(self.recips))

class Exec:
    def __init__(self, node):
        self.node = node
        self.command = self.arguments = self.workdir = None
        for child in node:
            if child.tag == TAG.Command:
                self.command = child.text
            elif child.tag == TAG.Arguments:
                self.arguments = child.text
            elif child.tag == TAG.WorkingDirectory:
                self.workdir = child.text
    def __str__(self):
        cmd = self.command
        if self.arguments:
            cmd += " %s" % self.arguments
        if self.workdir:
            cmd += " [in %s]" % self.workdir
        return cmd

class Settings:
    def __init__(self, node=None):
        self.enabled = True
        if node is not None:
            for child in node:
                if child.tag == TAG.Enabled:
                    self.enabled = child.text.lower() == 'true'

class Task:
    HTML = True
    def __init__(self, node, name):
        self.name = name
        self.created = self.author = self.description = None
        self.triggers = []
        self.actions = []
        self.settings = Settings()
        for child in node.findall(TAG.Settings):
            self.settings = Settings(child)
        for child in node.findall(TAG.RegistrationInfo + "/*"):
            tags.add(child.tag)
            if child.tag == TAG.Date:
                self.created = child.text
            elif child.tag == TAG.Author:
                self.author = child.text
            elif child.tag == TAG.Description:
                self.description = child.text
        for child in node.findall(TAG.Triggers + "/*"):
            tags.add(child.tag)
            self.triggers.append(Trigger(child))
        for child in node.findall(TAG.Actions + "/*"):
            if child.tag == TAG.SendEmail:
                self.actions.append(Email(child))
            elif child.tag == TAG.Exec:
                self.actions.append(Exec(child))
            else:
                tags.add(child.tag)
                self.actions.append(serialize(child))
    def enabled(self):
        if self.settings.enabled == False:
            return False
        for trigger in self.triggers:
            if trigger.enabled:
                return True
        return False
    def is_cdr_task(self):
        if self.name.startswith(r"Microsoft\Windows"):
            return False
        if re.match(r"At\d+", self.name):
            return False
        return True
    def __str__(self):
        if Task.HTML:
            status = self.enabled() and "enabled" or "disabled"
            description = disabled = ""
            if not self.enabled():
                disabled = " (disabled)"
            if self.description:
                description = "<br><i>%s</i>" % cgi.escape(self.description)
            triggers = "<br>".join([str(trigger) for trigger in self.triggers])
            actions = []
            for action in self.actions:
                actions.append("<li>%s</li>" % cgi.escape(str(action)))
            return """\
<div class="%s">
<b>%s</b>%s%s<br>
Runs %s
<ol>%s</ol>
</div>""" % (status, cgi.escape(self.name), disabled, description,
           triggers, "\n".join(actions))
        line = "-" * 100
        actions = []
        for i, action in enumerate(self.actions):
            actions.append(" %d. %s\n" % (i + 1, action))
        triggers = "\n".join([str(trigger) for trigger in self.triggers])
        description = ""
        if self.description:
            description = "\n (%s)" % self.description
        return """\
Name: %s (%s)%s
Runs %s
%s
%s
""" % (self.name, self.enabled() and "enabled" or "disabled",
       description, triggers, "".join(actions), line)

ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n/10%10!=1)*(n%10<4)*n%10::4])

tags = set()
limits = set()
stat = os.stat(REPORT)
when = time.asctime(time.localtime(stat.st_mtime))
doc = open(REPORT).read()
#doc = open("schtasks.xml").read()
#doc = re.search("<Tasks>.*</Tasks>", msg, re.DOTALL).group(0)
tree = etree.XML(doc) #re.sub("<\\?xml[^>]*>\\s*", "", doc))
name = None
tasks = []
for node in tree:
    if isinstance(node.tag, basestring):
        tasks.append(Task(node, name))
    else:
        name = node.text.strip()[1:]
if Task.HTML:
    print """\
Content-type: text/html

<!DOCTYPE html>
<html>
 <head>
  <title>CDR Scheduled Tasks</title>
  <style>
h1 { color: maroon; font-size: 14pt; }
div { border: solid 1px black; color: green; margin: 10px; padding: 5px;
padding-top: 15px; }
.disabled { color: red; }
* { font-family: Arial, sans-serif; }
  </style>
 </head>
 <body>
  <h1>CDR Scheduled Tasks as of %s</h1>""" % when
else:
    print "Content-type: text/plain\n"
for task in tasks:
    if task.is_cdr_task():
        print task
if Task.HTML:
    print " </body>\n</html>"
