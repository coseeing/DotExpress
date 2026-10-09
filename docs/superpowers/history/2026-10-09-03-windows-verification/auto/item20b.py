import sys, os, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dx, docs as D
EXE, d = sys.argv[1], sys.argv[2]
ws = os.path.join(d, "workspace")
app, w = dx.launch(EXE, d)
print("add Alpha:", D.add(app, w, "Alpha"))
D.set_input(w, "Alpha body")
print("close:", D.close(app, w))
subprocess.run(["attrib", "+r", os.path.join(ws, "Alpha.dep")])
app, w = dx.launch(EXE, d, fresh=False)
D.select(w, "Alpha")
print("rename Alpha->alpha with +r:", D.rename(app, w, "alpha"))
D.cancel_open(app, w)
print("list:", D.docs(w), "state:", D.ws_state(d), os.listdir(ws))
print("close:", D.close(app, w))
subprocess.run(["attrib", "-r", os.path.join(ws, "*.dep")])
