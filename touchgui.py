from Tkinter import *
import tkFileDialog
import tkMessageBox
import itertools
import subprocess
import traceback
import pygame.midi as pym

class Port(Frame):
    def __init__(self, parent, label, names):
        Frame.__init__(self, parent)
        Label(self, text=label).pack(side=TOP, expand=1, fill=X)
        self.listbox = Listbox(self, exportselection=0)
        self.listbox.pack(side=BOTTOM, expand=1, fill=X)
        for name in names:
            self.listbox.insert(END, name)

    def get_selected_port_name(self):
        return [self.listbox.get(int(x)) for x in self.listbox.curselection()][0]


class MultiPort(Frame):
    def __init__(self, parent, labels_and_mappings):
        Frame.__init__(self, parent)
        self.ports = [Port(self, label, mapping) for label, mapping in labels_and_mappings]
        height = max(port.listbox.size() for port in self.ports)
        for port in self.ports:
            port.listbox["height"] = height
            port.pack(side=LEFT, expand=1, fill=X)

    def get_selected_port_names(self):
        return [port.get_selected_port_name() for port in self.ports]


class FileControl(Frame):
    def __init__(self, parent, label, filetypes, extension, save):
        Frame.__init__(self, parent)
        Label(self, text=label).pack(side=LEFT)
        self.entry = Entry(self)
        self.entry.pack(side=LEFT, expand=1, fill=BOTH)

        def browse():
            dialog = tkFileDialog.asksaveasfilename if save else tkFileDialog.askopenfilename
            filename = dialog(title=label, initialfile=self.entry.get(), filetypes=filetypes, defaultextension=extension)
            if filename:
                self.entry.delete(0, END)
                self.entry.insert(0, filename)

        Button(self, text="Browse...", command=browse).pack(side=RIGHT)


pym.init()
inputs = []
outputs = []
for i in xrange(pym.get_count()):
    info = pym.get_device_info(i)
    if info[2]:
        inputs.append(info[1])
    if info[3]:
        outputs.append(info[1])

tk = Tk()
tk.wm_title("TouchOSC Cubase Mapper")

midi_frame = MultiPort(tk, [("Cubase to MOSC", inputs), ("MOSC to Cubase", outputs)])
midi_frame.pack(side=TOP, fill=BOTH)
layout = FileControl(tk, "Layout", [("TouchOSC Layout", "*.touchosc")], "touchosc", False)
layout.pack(side=TOP, expand=1, fill=X)
mosc = FileControl(tk, "MOSC", [("MOSC mapping", "*.txt")], "txt", True)
mosc.pack(side=TOP, expand=1, fill=X)
remote = FileControl(tk, "Generic remote", [("Generic remote", "*.xml")], "xml", True)
remote.pack(side=TOP, expand=1, fill=X)
port_frame = Frame(tk)
port_frame.pack(side=TOP, expand=1, fill=X)
Label(port_frame, text="OSC Port").pack(side=LEFT)
port_entry = Entry(port_frame)
port_entry.insert(0, "10000")
port_entry.pack(side=LEFT)

def create_mapping():
    try:
        layoutpath = layout.entry.get()
        moscpath = mosc.entry.get()
        remotepath = remote.entry.get()
        oscport = port_entry.get()
        cubasetomosc, mosctocubase = midi_frame.get_selected_port_names()
        command = ["touchmapper.py", layoutpath, moscpath, remotepath, oscport, cubasetomosc, mosctocubase]
        subprocess.check_call(command, shell=True)
        tkMessageBox.showinfo("Success", "Finished successfully!")
    except:
        traceback.print_exc()
        tkMessageBox.showerror("Failure", "Error in operation")

create_mapping_button = Button(tk, text="Create mapping", command=create_mapping)
create_mapping_button.pack(side=TOP, expand=1, fill=X)
tk.mainloop()