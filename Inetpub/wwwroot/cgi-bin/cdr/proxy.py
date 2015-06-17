#----------------------------------------------------------------------
#
# $Id$
#
# Passthrough to get resources from unsecured URLs.
#
# JIRA::OCECDR-3588
#
#----------------------------------------------------------------------
import cgi
import cdr
import urllib2
import re
import sys
import datetime
import time
try:
    import os
    import msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
except:
    pass

CHUNK = 32000

#----------------------------------------------------------------------
# Record errors.
#----------------------------------------------------------------------
def log(url, problem):
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fp = open("%s/proxy.log" % cdr.DEFAULT_LOGDIR, "a")
        fp.write("%s %s: %s\n" % (now, repr(url), problem))
        fp.close()
    except:
        pass

#----------------------------------------------------------------------
# It turns out that Internet Explorer (or at least the most recent
# versions of IE) will not wait for us to parse nvcg.css. So I had to
# abandon the use of the csstools module and do the work with regular
# expressions. Not as robust, but it works (for now).
#
# Code from my prototype test of the new approach:
#   css = open("nvcg.css").read()
#   print re.sub("url[(]([^)]+)[)]", src_replacer, css)
#----------------------------------------------------------------------
def src_replacer(match):
    src = match.group(1).strip()
    src = src.strip("'\"")
    if src.startswith("data:"):
        return match.group(0)
    if src.startswith("https"):
        return match.group(0)
    if not src.startswith("http"):
        if src.startswith("/"):
            src = "%s/%s" % (absolute_base, src)
        else:
            src = "%s/%s" % (relative_base, src)
    return "url(\"%s?url=%s\")" % (proxy, src)


#----------------------------------------------------------------------
# Relative URLs in proxied CSS files won't work. Proxy those, too.
# Probably wouldn't be hard to break this parsing with edge cases.
# 2015-04-20: took too long to parse nvcg.css with the cssutils
# package, so I'm falling back on regular expression. Will be even
# less robust, but at least it will work with IE.
#----------------------------------------------------------------------
def fix_css(original, url):
    try:
        return re.sub(r"url\s*\(([^)]+)\)", src_replacer, original)
    except Exception, e:
        log(url, e)
        return original

#----------------------------------------------------------------------
# Send the payload back through our own web server. Have to do this
# in slices of the bytes, because of a Windows bug:
# See https://bugs.python.org/issue11395.
#----------------------------------------------------------------------
def send(what, content_type=None):
    if content_type is None:
        content_type = "Content-type: text/plain"
    sys.stdout.write("%s\r\n\r\n" % content_type)
    written = 0
    while written < len(what):
        portion = what[written:written+CHUNK]
        sys.stdout.write(portion)
        written += CHUNK
    sys.exit(0)

start = time.time()
fields = cgi.FieldStorage()
url = fields.getvalue("url")
try:
    conn = urllib2.urlopen(url)
    code = conn.getcode()
    if code != 200:
        log(url, "code: %s" % repr(code))
        send("")
    payload = conn.read()
    headers = conn.headers.headers
    content_type = None
    for header in conn.headers.headers:
        if header.lower().startswith("content-type"):
            content_type = header.strip()
            break
    if isinstance(content_type, basestring) and "/css" in content_type:
        proxy = "%s/cgi-bin/cdr/proxy.py" % cdr.CBIIT_NAMES[2]
        proxy = "/cgi-bin/cdr/proxy.py"
        parsed_url = urllib2.urlparse.urlparse(url)
        scheme = parsed_url.scheme
        netloc = parsed_url.netloc
        path = parsed_url.path
        path, resource = os.path.split(path)
        absolute_base = "%s://%s" % (scheme, netloc)
        relative_base = absolute_base + path
        payload = fix_css(payload, url)
    elapsed = time.time() - start
    log(url, "elapsed: %s" % elapsed)
except Exception, e:
    log(url, e)
    send("")
send(payload, content_type)
