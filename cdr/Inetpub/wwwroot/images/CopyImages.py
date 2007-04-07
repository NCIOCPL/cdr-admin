import glob

for name in glob.glob("*"):
    file = open(name, "rb")
    data = file.read()
    file.close()
    file = open("../elecmail/%s" % name, "wb")
    file.write(data)
    file.close()
    print "wrote %s" % name
