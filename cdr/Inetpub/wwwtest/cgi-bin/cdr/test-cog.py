import msvcrt, os, sys
msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
resp = open('d:/tmp/output4.txt', 'rb').read()
sys.stdout.write(resp)
