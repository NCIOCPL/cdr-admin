#!/usr/bin/env python
#----------------------------------------------------------------------
# Show disk size/usage on CDR Windows Server
# See http://code.activestate.com/recipes/577972-disk-usage/
#----------------------------------------------------------------------
def human(n):
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return "%sB" % n

class Disk:
    def __init__(self, drive):
        self.drive = drive.upper()
        path = "%s:\\" % drive
        _, total, free = (ctypes.c_ulonglong(), ctypes.c_ulonglong(),
                          ctypes.c_ulonglong())
        f = ctypes.windll.kernel32.GetDiskFreeSpaceExW
        ret = f(path, ctypes.byref(_), ctypes.byref(total), ctypes.byref(free))
        if ret == 0:
            raise ctypes.WinError()
        self.total = total.value
        self.free = free.value
        self.used = self.total - self.free

    def show(self):
        print(f"""\
{self.drive} DRIVE
  TOTAL: {self.total:>13} ({human(self.total)})
   USED: {self.used:>13} ({human(self.used)})
   FREE: {self.free:>13} ({human(self.free)})
""")

print("Content-type: text/plain")
print("")

try:
    import ctypes
    import cdr
    Disk("C").show()
    Disk("D").show()
except Exception as e:
    cdr.LOGGER.exception("disk free failure")
    print(e)
except:
    cdr.LOGGER.exception("disk free unexpected error")
    print("Unexpected error")
