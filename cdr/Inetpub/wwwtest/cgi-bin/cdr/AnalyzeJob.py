import cgi, glob, os, re, time

job = "d:/bkline/vendors/test-20020901"
try:
    fields = cgi.FieldStorage()
    job    = fields and fields.getvalue("job") or job
except:
    pass
os.chdir(job)
failedPattern = re.compile(r"Error for document \d+: ")

class Set:
    def __init__(self, filtered, failed, invalid, time):
        self.filtered   = filtered
        self.failed     = failed
        self.invalid    = invalid
        self.time       = time

def countFailed(directory):
    return len(failedPattern.findall(open("%s/FilterAndValidate.out" %
                    directory).read()))
    
def countInvalid(directory):
    invalid = {}
    for line in open("%s/FilterAndValidate.log" % directory).readlines():
        try: invalid[line.split(":")[1]] = 1
        except: pass
    return len(invalid)

def calculateTimes(files):
    earliest = 0
    latest   = 0
    for file in files:
        s = os.stat(file)
        if not earliest or s[8] < earliest: earliest = s[8]
        if not latest or s[8] > latest:     latest   = s[8]
    return latest - earliest + 1
        
def analyzeSet(directory):
    xmlFiles = glob.glob("%s/*.xml" % directory)
    return Set(len(xmlFiles), countFailed(directory), countInvalid(directory),
            0) #calculateTimes(xmlFiles))

def showTime(secs):
    hours = secs / (60 * 60)
    secs %= (60 * 60)
    minutes = secs / 60
    secs %= 60
    return "&nbsp;&nbsp;&nbsp;%dh %02dm %02ds" % (hours, minutes, secs)

def groupNum(num):
    if not num:
        return '0'
    prefix = ''
    if num < 0:
        prefix = '-'
        num = -num
    s = ''
    comma = ''
    while num:
        part = num % 1000
        num /= 1000
        if num:
            s = "%03d%s%s" % (part, comma, s)
        else:
            s = "%d%s%s" % (part, comma, s)
        comma = ','
    return prefix + s

def showSet(name, set, italic = ''):
    selected  = set.filtered + set.failed
    if selected:
        pctFailed = (set.failed * 100.0) / selected
    else:
        pctFailed = 0.0
    if set.filtered:
        pctInvalid = (set.invalid * 100.0) / set.filtered
    else:
        pctInvalid = 0.0
    italic = italic and " class='it'" or ""
    print """\
   <tr>
    <td%s>%s</td>
    <td %salign='right'>&nbsp;&nbsp;&nbsp;%s</td>
    <td %salign='right'>&nbsp;&nbsp;&nbsp;%s</td>
    <td %salign='right'>&nbsp;&nbsp;&nbsp;%.2f%%</td>
    <td %salign='right'>&nbsp;&nbsp;&nbsp;%s</td>
    <td %salign='right'>&nbsp;&nbsp;&nbsp;%s</td>
    <td %salign='right'>&nbsp;&nbsp;&nbsp;%.2f%%</td>
   </tr>
""" % (italic, name, 
       italic, groupNum(selected), 
       italic, groupNum(set.failed),
       italic, pctFailed,
       italic, groupNum(set.filtered), 
       italic, groupNum(set.invalid),
       italic, pctInvalid)

dirs = os.listdir('.')
dirs.sort()
totals = Set(0, 0, 0, 0)
now = time.strftime("%Y-%m-%d %H:%M:%S")
print """\
<html>
 <head>
  <title>Stats for vendor document generation job %s at %s</title>
  <style type='text/css'>
   body    { font-family: Arial, Helvetica, sans-serif; color: black;
             background: white }
   table   { border: 0px; }
   tr      { border: 0px; }
   td      { border: 0px; }
   th      { border: 0px; }
   th.bb   { border-bottom: 1px; background: #DDDDDD; }
   tr.bb   { border-bottom: 1px; }
   /*td.it   { font-style: italic; }*/
   td.it   { background: #DDDDDD; }
  </style>
 </head>
 <body>
  <h2>Stats for vendor document generation</h2>
  <table>
   <tr>
    <th align='right'>&nbsp;&nbsp;&nbsp;Job location:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th align='right'>&nbsp;&nbsp;&nbsp;Report time:&nbsp;</th>
    <td>%s</td>
   </tr>
  </table>
  <br />
  <table border='0' cellspacing='0' cellpadding='2'>
   <tr class='bb'>
    <th class='bb'>&nbsp;&nbsp;&nbsp;Doc Type&nbsp;&nbsp;&nbsp;</th>
    <th class='bb'>&nbsp;&nbsp;&nbsp;Selected&nbsp;&nbsp;&nbsp;</th>
    <th class='bb'>&nbsp;&nbsp;&nbsp;Failed&nbsp;&nbsp;&nbsp;</th>
    <th class='bb'>&nbsp;&nbsp;&nbsp;Percent&nbsp;&nbsp;&nbsp;</th>
    <th class='bb'>&nbsp;&nbsp;&nbsp;Exported&nbsp;&nbsp;&nbsp;</th>
    <th class='bb'>&nbsp;&nbsp;&nbsp;Invalid&nbsp;&nbsp;&nbsp;</th>
    <th class='bb'>&nbsp;&nbsp;&nbsp;Percent&nbsp;&nbsp;&nbsp;</th>
   </tr>
""" % (job, now, job, now)
for d in dirs:
    if os.path.isdir(d):
        set = analyzeSet(d)
        totals.filtered += set.filtered
        totals.failed   += set.failed
        totals.invalid  += set.invalid
        #totals.time     += set.time
        #print d, set.filtered, set.failed, set.invalid, set.time
        showSet(d, set)
#print 'Totals', totals.filtered, totals.failed, totals.invalid, totals.time
showSet('Totals', totals, 1)
print """\
  </table>
 </body>
</html>"""
