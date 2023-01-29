import os
import re
import sys
import subprocess
import tkinter as tk
import tkinter.ttk as ttk
from operator import itemgetter, attrgetter
from aui import PopMenu
from aui import Text, TwoFrame   
from svgpath import XmlTree        
        
#---------------------------------------------------------------------------------
class ClassTree(ttk.Treeview, PopMenu):
    def __init__(self, master, select_action=None, cnf={}, **kw):
        ttk.Treeview.__init__(self, master)
        self.textbox = None
        self.data = {}
        style = ttk.Style()
        style.configure('Calendar.Treeview', rowheight=23)
        self.config(style='Calendar.Treeview')
        self.tag_configure('class', font='Mono 10 bold', foreground='#557')
        self.tag_configure('def', font='Mono 10', foreground='#555')
        self.tag_configure('if', font='Mono 10', foreground='#335')
        self.tag_configure('content', font='Mono 10', foreground='#335')
        cmds = [('Update', self.on_update)]
        self.add_popmenu(cmds)    
        self.bind('<ButtonRelease-1>', self.on_select)    
        self.bind('<Enter>', self.on_enter)  
        self.select_action = select_action    
        self.text = ''
        self.clicktime = 0     
        
    def on_enter(self, event=None):
        self.on_update()
        
    def on_update(self, event=None):
        if self.textbox != None:    
            text = self.textbox.get_text()  
            if self.text != text:
                self.set_text(text)        
        
    def on_select(self, event=None):
        self.unpost_menu()
        if event.time - self.clicktime < 500:
            doubleclick = True            
            self.on_update()
        else:
            doubleclick = False
        self.clicktime = event.time   
             
        item = self.focus()
        data = self.data.get(item)
        if data != None:
            i, name, key = data
            self.select_action(i, name, key)
        
    def get_py_tree(self, textlines):
        objlist = ['']
        prev_indent = -1
        i = 0                
        self.data = {}        
        for line in textlines:     
            i += 1          
            if line[0:2] == 'if':
                indent = 0              
                key = 'if'
                name = line
                objname = line
            else:
                m = re.search('\s*(?P<key>class|def)\s+(?P<name>\w+)\s*[\(\:]', line)
                if m == None:
                    continue
                key = m.group('key')
                name = m.group('name')
                objname = name + ' (%d)'%i
                indent = line.find(key)
            if indent == 0:
                obj = self.insert('', 'end', text=objname, tag=key)  
                self.data[obj] = (i, name, key)
                objlist.append(obj)
                prev_indent = indent
            elif indent > prev_indent:
                obj = self.insert(objlist[-1], 'end', text=objname, tag=key) 
                self.data[obj] = (i, name, key)
            elif indent <= prev_indent:
                objlist.pop()
                prev_indent = indent
                obj = self.insert(objlist[-1], 'end', text=objname, tag=key)  
                self.data[obj] = (i, name, key)                  
               
    def add_xml_obj(self, pobj, pnode):
        for obj in pobj.children:
            node = self.add_xml_node(pnode, obj)              
            self.add_xml_obj(obj, node)
            
    def get_textlines(self, tree, text):
        pass
        
    def add_xml_node(self, pnode, obj):
        tag = obj.tag
        node = self.insert(pnode, 'end', text=tag, tag=tag)         
        self.data[node] = (obj.span, obj.id, obj.tag)
        self.item(node, open=1)
        for k, v in obj.dct.items():
            node1 = self.insert(node, 'end', text='%s: %s'%(k, v), tag='content')  
        return node
        
    def get_xml_tree(self, text):
        self.objs = {}
        tree = XmlTree(self, text)
        self.get_textlines(tree, text)
        obj = tree.root
        node = self.add_xml_node('', obj)  
        self.add_xml_obj(obj, node)          
            
    def set_text(self, text):
        self.data = {}
        if text == self.text:
            return
        self.text = text
        tree = self
        for obj in self.get_children():
            self.delete(obj)
        text = text.strip()
        if text == '':
            return
        textlines = text.splitlines()       
                
        s0 = textlines[0]
        if s0[0] == '<':
            self.get_xml_tree(text)
        else:
            self.get_py_tree(textlines)   
        for obj in self.get_children():
            self.item(obj, open=1)
        return     
        
class FileView(tk.Frame):
    def __init__(self, master, **kw):       
        tk.Frame.__init__(self, master)
        self.textobj = Text(self)
        self.textobj.pack(fill='both', expand=True)
        
    def set_text(self, text):
        self.textobj.set_text(text)   
             
class ClassNotebook(tk.Frame):
    def __init__(self, master, select_action=None, cnf={}, **kw):
        tk.Frame.__init__(self, master)
        self.pages = {}
        self.select_action = select_action
        notebook = ttk.Notebook(self)
        notebook.pack(fill = 'both', expand=True)
        self.notebook = notebook
        self.tree1 = self.add_page('Class', ClassTree) 
        self.tree2 = self.add_page('Preview', FileView)                 
            
        notebook.pack(fill='both', expand=True)
        notebook.bind('<ButtonRelease-1>', self.switch_page)        
    
    def set_text(self, text):
        self.tree1.set_text(text)
        self.tree2.set_text(text)
            
    def switch_page(self, event=None):
        dct = self.notebook.tab('current')
        label = dct['text'].strip()

    def add_page(self, label, widgetclass):
        frame = tk.Frame(self.notebook)
        frame.pack(fill='both', expand=True)         
        widget = widgetclass(frame, select_action = self.select_action)
        widget.pack(fill='both', expand=True)         
        widget.notepage = frame
        self.notebook.add(frame, text=label.center(17))        
        #n = len(self.pages)        
        #self.notebook.select(n)        
        return widget                  
        
#-------------------------------------------------------------------------
class FileTreeView(ttk.Treeview, PopMenu):
    def __init__(self, master, select_action=None, cnf={}, **kw):
        ttk.Treeview.__init__(self, master)
        self.data = {}
        self.dirs = []              
        self.files = []        
        self.click_select = 'double'
        style = ttk.Style()
        style.configure('Calendar.Treeview', rowheight=24)
        self.config(style='Calendar.Treeview')
        self.tag_configure('folder', font='Mono 10 bold', foreground='#557')
        self.tag_configure('file', font='Mono 10', foreground='#555')        
        self.select_action = select_action
        self.currentpath = '.'    
        os.chdir('/home/athena')
        self.text = ''
        self.data = {}
        self.pathvars = {}
        self.clicktime = 0
        self.previtem = None
        cmds = [('Open', self.on_open), ('Update', self.on_update)]
        cmds.append(('~/src/', self.go_src_path))
        cmds.append(('~/', self.go_home_path))
        cmds.append(('~/src/py', self.go_py_path))
        cmds.append(('~/src/py/test', self.go_test_path))
        self.add_popmenu(cmds)    
        self.bind('<ButtonRelease-1>', self.on_select)         
           
    def add_file(self, filename):
        pass
        
    def add_dir(self, path):
        pass
         
    def go_src_path(self, event=None):
        path = os.path.expanduser('~') + os.sep + 'src'
        self.set_path(path)
 
    def go_home_path(self, event=None):
        path = os.path.expanduser('~') 
        self.set_path(path)
        
    def go_py_path(self, event=None):
        path = os.path.expanduser('~') + os.sep + 'src/py'
        self.set_path(path)
 
    def go_test_path(self, event=None):
        path = os.path.expanduser('~') + os.sep + 'src/py/test'
        self.set_path(path)      
           
    def on_update(self, event=None):
        path = os.getcwd()
        if '__pycache__' in path:
            os.chdir('..')
            path = os.getcwd()
        self.set_path(path)
        
    def on_open(self, event=None):
        item = self.focus() 
        data = self.data.get(item)
        if data == None or self.select_action == None:
            return
        path, tag = data
        self.select_action(path, tag)
        
    def set_path(self, dirpath):
        dirpath = os.path.realpath(dirpath)
        self.currenpath = dirpath
        for obj in self.get_children():
            self.delete(obj)
        self.data = {}
        self.pathvars = {}
        self.add_path('', dirpath)
        
    def add_folder(self, item, dirpath):        
        self.add_path(item, dirpath)  
        os.chdir(dirpath)
        self.pathvars[dirpath] = item
        self.item(item, open=1) 
        
    def get_item(self, path):        
        node = None
        for item in self.data:
            fpath, tag = self.data.get(item)            
            if fpath in path:
               #print(item, tag, fpath)
               node = item               
        return node
        
    def select_folder(self, item, path):
        #self.msg.puts('select_folder', item, path)
        dirpath = os.path.dirname(path)
        if path in self.pathvars:
           return self.pathvars.get(path)     
        if item == None:
           item = self.get_item(path)
        if item == None:
           return   
        self.add_folder(item, path)
        return item
        
    def on_select(self, event=None):        
        self.unpost_menu()
        item = self.focus()           
        if self.previtem == item and event.time - self.clicktime < 500:
            doubleclick = True            
            #self.msg.puts('on_select', item, self.item(item, option='text'))
        else:
            doubleclick = False
        self.previtem = item
        self.clicktime = event.time
        data = self.data.get(item)
        if data == None:
            return
        path, tag = data 
        if tag == 'folder':            
            if doubleclick == True:
               self.set_path(path)
            else:
               self.select_folder(item, path)
            return
        if self.select_action == None or tag != 'file':
           return        
        if self.click_select == 'click' or doubleclick == True:
           self.select_action(path, tag)            
           self.add_file(path)
            
    def add_path(self, node, dirpath):
        #print('add_path', node, dirpath)
        if node == '':            
            item = self.insert('', 'end', text='..', tag='folder')
            p = os.path.realpath('..')
            self.data[item] = (p, 'folder')   
            self.pathvars[p] = item         
        if os.path.lexists(dirpath):
            os.chdir(dirpath)
        else:
            return
        lst = os.listdir(dirpath)        
        folders = []
        files = []   
        for s in lst:
            if s[0] == '.':
                continue
            path = os.path.realpath(s)
            if os.path.isfile(path) == True:
                files.append(s)
            elif os.path.isdir(path):
                folders.append(s)
        folders.sort()
        files.sort()                 
        for s in files:
           item = self.insert(node, 'end', text=s, tag='file')    
           self.data[item] = (os.path.realpath(s), 'file')
        for s in folders:
           item = self.insert(node, 'end', text=s, tag='folder') 
           self.data[item] = (os.path.realpath(s), 'folder')   
           #self.add_path(item, os.path.realpath(s))  
           #os.chdir(dirpath)      
             
    def active_item(self, item):
        self.selection_set([item])
        #self.item(item, open=True)
        self.focus(item)
        self.see(item)
        
    def active_file(self, filename): 
        path = os.path.dirname(filename)
        item = self.get_item(path)
        if item != None:
           self.select_folder(item, self.data.get(item)[0])           
           self.active_item(item) 
        item = self.get_item(filename)
        if item != None:
           self.active_item(item)
        return               

class DirTreeView(FileTreeView):
    def __init__(self, master, select_action=None, cnf={}, **kw):
        FileTreeView.__init__(self, master, select_action, cnf={}, **kw)        
        self.dirs = []              
        self.files = []
        self.history_item = ''
        
    def add_file(self, filename):
        if filename in self.files:
            return        
        fn = os.path.realpath(filename)
        fdir = fn.rsplit(os.sep, 1)[0]
        self.add_dir(fdir)           
             
        fname = fn.rsplit(os.sep, 1)[1]
        item = self.insert(self.history_item, 'end', text=fname, tag='file') 
        self.data[item] = (fn, 'file') 
        self.files.append(filename)
        
    def add_dir(self, path):
        if not path in self.dirs:
            self.dirs.insert(0, path)
            self.set_path(path)
        
    def set_path(self, dirpath):
        dirpath = os.path.realpath(dirpath)
        self.currenpath = dirpath
        for obj in self.get_children():
            self.delete(obj)
        self.data = {}
        self.pathvars = {}
        
        for s in self.dirs:            
            s1 = s.split(os.sep)[-1]
            item = self.insert('', 'end', text=s1, tag='folder') 
            self.data[item] = (os.path.realpath(s), 'folder')                 
        self.history_item = self.insert('', 'end', text='[History]', tag='')
        self.item(self.history_item, open=True)
        for s in self.files:        
            fn = os.path.realpath(s)     
            p = fn.rsplit(os.sep, 1)
            item = self.insert(self.history_item, 'end', text=p[1], tag='file') 
            self.data[item] = (fn, 'file') 


class TreeNotebook(tk.Frame):
    def __init__(self, master, select_action=None, cnf={}, **kw):
        tk.Frame.__init__(self, master)
        self.pages = {}
        self.select_action = select_action
        notebook = ttk.Notebook(self)
        notebook.pack(fill = 'both', expand=True)
        self.notebook = notebook
        self.tree1 = self.add_page('File', FileTreeView) 
        self.tree2 = self.add_page('Favorite', DirTreeView)                 
            
        notebook.pack(fill='both', expand=True)
        notebook.bind('<ButtonRelease-1>', self.switch_page)
        self.tree1.set_path(os.getcwd())
        p0 = '/home/athena/src'
        p1 = p0 + '/py'
        for s in [p0, p1, p1 + '/example', p1 + '/test']:
            self.tree2.add_dir(s)            
    
    def set_path(self, path):
        self.tree1.set_path(path)
            
    def switch_page(self, event=None):
        dct = self.notebook.tab('current')
        label = dct['text'].strip()

    def add_page(self, label, widgetclass):
        frame = tk.Frame(self.notebook)
        frame.pack(fill='both', expand=True)         
        widget = widgetclass(frame, select_action = self.select_action)
        widget.pack(fill='both', expand=True)         
        widget.notepage = frame
        self.notebook.add(frame, text=label.center(17))        
        #n = len(self.pages)        
        #self.notebook.select(n)        
        return widget             
           
import aui
from aui import Messagebox 
class TestFrame(tk.Frame):
    def __init__(self, master, select_act=None):       
        tk.Frame.__init__(self, master)
        self.select_act = select_act
        frame = TwoFrame(self, sep=0.8, type='v')
        frame.pack(fill='both', expand=True)
        frame1 = TwoFrame(frame.top, sep=0.5, type='v')
        frame1.pack(fill='both', expand=True)
        notebook1 = ClassNotebook(frame1.top, select_action=self.on_select_class)
        notebook1.pack(fill='both', expand=True)
        self.classview = notebook1.tree1
        self.fileview = notebook1.tree2
        self.textbox = self.fileview.textobj
        
        notebook2 = TreeNotebook(frame1.bottom, select_action=self.on_select_file)
        notebook2.pack(fill='both', expand=True)
        msg = Messagebox(frame.bottom)
        msg.pack(side='bottom', fill='x', expand=False)
        statusbar = msg.add_statusbar()
        self.msg = msg
        treeview = notebook2.tree1
        treeview.msg = self
        treeview.click_select = 'click'
        treeview.set_path('/home/athena/src')
        treeview.active_file('/home/athena/src/menutext/idle.py')
        treeview.update()
        self.treeview = treeview
        notebook2.tree2.add_file(__file__)
        notebook2.tree2.add_file('/home/athena/src/menutext/menutext.py')
        
    def puts(self, *lst, end='\n'):
        for text in lst:
            self.msg.puts(str(text) + ' ')
        
    def fread(self, filename):
        with open(filename, 'r') as f:
            text = f.read()
            f.close()
            return text
            
    def set_path(self, path):
        self.treeview.set_path(path)
        
    def on_select_file(self, filename, tag):
        self.puts(filename)
        text = self.fread(filename)
        self.classview.set_text(text)
        self.fileview.set_text(text)
        if self.select_act != None:
            self.select_act(filename)
        
    def on_select_class(self, i, name, key):              
        self.puts(i, name, key)
        if type(i) is tuple:
            text = self.textbox.text[:i[0]]     
            n = text.count('\n') + 1      
            #self.textbox.see('%d.0' %n)
            self.textbox.goto(n) 
        
        #self.textbox.goto(i, name, key)       
        

if __name__ == '__main__':      
    def main():
        root = tk.Tk()
        root.title('Frame and Canvas')
        root.geometry('500x900') 
        frame = TestFrame(root)
        frame.pack(fill='both', expand=True)
        frame.on_select_file('/home/athena/src/svgview/svg/path.svg', '')
        frame.set_path('/home/athena/src/svgview/svg')
        frame.mainloop()   
    
    main()



