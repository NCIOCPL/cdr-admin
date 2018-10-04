sids = {}
users = {}
for line in open("d:/cdr/sftp_log/cumulative.log"):
    if "]: open" in line:
        words = line.split()
        when = " ".join(words[:2])
        sid = int(words[3][5:-2])
        user = sids.get(sid, "").lower()
        if user and when > users.get(user, ""):
            users[user] = when
    elif "session opened for local user" in line:
        words = line.split()
        sid = int(words[3][5:-2])
        user = words[9]
        sids[sid] = user
print("Content-type: text/plain\n")
for user in sorted(users):
    print("{} {}".format(user, users[user]))
