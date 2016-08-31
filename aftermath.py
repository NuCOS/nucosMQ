import sys

filename = sys.argv[1]
py = sys.argv[2]

raw_fn = filename.split(".")[0]

f = open(filename, "r")
txt = f.read()
f.close()

f = open(raw_fn+"_"+py+".xml", "w")
txt = txt.replace("UTestClient", "UTestClient_"+py)
f.write(txt)
f.close

