import numpy as np
import re
import tkinter as tk
import matplotlib as mp
import matplotlib.pyplot as plt
from matplotlib import patches, transforms
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from PIL import Image
import urllib3, io
from fileio import fread
from mathxy import *
from object import *
from tagobj import TagObj
from pathobj import PathObj 
from plot import Plot

class XmlTree(object):
    def __init__(self, svg, text):
        self.get_xml_tree(svg, text)

    def get_xml_tag(self, pobj, level):
        objlevel = level + 1     
        while self.tagobjs != []:
            obj = self.tagobjs.pop(0)             
            if type(obj) == str:                                
                i = self.tagends.index(obj)
                self.tagends.pop(i)
                return             
            pobj.children.append(obj)  
            if obj.without_endtag == True:
                continue     
            tag = obj.get('tag')    
            if self.tagends.count(tag) > 0:     
                self.get_xml_tag(obj, objlevel)               
        return 
               
    def get_xml_tree(self, svg, text):
        self.tagends = []    
        self.taglist = []        
        tagobjs = []        
        lst = re.findall('\<\!\-\-[^\>]+\-\-\>|\<\!DOCTYPE[^\>]+\>|\<\?xml[^\>]+\>', text)
        for s in lst:
            if '<?xml' in s:
                svg.xmltype = s
            elif 'DOCTYPE' in s:
                svg.doctype = s
            text = text.replace(s, ' '*len(s))        
        p1 = '(\<(?P<tag>[\w\:\-\_\!\[]+))'
        p2 = '((?P<content>[^\>]*)\>)'
        p3 = '((?P<tagend>\<\/[\w\:\-\_]+)\>)'        
        pattern = '(%s[\s\n]*%s)|%s' % (p1, p2, p3)   
        for m in re.finditer(pattern, text):       
            tag = m.group('tag') 
            if tag == None:
               tag = m.group('tagend').replace('</', '')
               self.tagends.append(tag)
               obj = tag
            else:
               content = m.group('content')
               isend = ''         
               obj = TagObj(tag, content, m.span())  
               obj.svg = svg
               if obj.id != None:
                  svg.objs['#' + obj.id] = obj
               self.taglist.append(obj)
               if tag == 'text':
                   i, j = m.span()
                   j1 = text.find('</', j)
                   obj.set_text(text[j:j1])
            tagobjs.append(obj)    
        
        self.tagobjs = tagobjs.copy()
        self.root = self.tagobjs.pop(0)
        self.get_xml_tag(self.root,  0)    
        
        
class SvgObj(TagObj):
    def __init__(self):
        self.css_styles = {}
        self.pobjs = []
        self.draw_tags = ['path', 'rect', 'ellipse', 'polygon', 'circle', 'line']        
     
    def draw_obj(self, e):     
        styles = self.css_styles
        e.css_style = styles.get(e.id, styles.get(e.tag))  
        if e.draw_obj(self, self.ax) == True:
           self.pobjs.append(e)
        
    def draw_text(self, e):
        x, y, dx, dy = e.get_values(('x', 'y', 'dx', 'dy'))
        fontsize, fontfamily, fc, ec = e.get_values(('font-size', 'font-family', 'fill', 'stroke'))        
        if fontfamily != None and '-' in fontfamily:
            fontfamily = fontfamily.replace('-', ' ')
        fp = FontProperties(family=fontfamily)
        text = e.get("text").strip()
        if dx != None:
           x += int(dx)
        if dy != None:
           y += int(dy)        
        path = TextPath((0, 0), text, size=fontsize, prop=fp) 
        t = transforms.Affine2D().scale(1,-1).translate(x, y)
        path1 = path.transformed(t)                 
        patch = patches.PathPatch(path1, fc=fc, ec=ec)        
        trans = e.transobj.get_trans()        
        if trans != None:
            patch.set_transform(trans + self.ax.transData)
        self.ax.add_patch(patch)
     
    def get_feBlend(self, obj):
        in1, in2, mode = obj.get_values(('in', 'in2', 'mode'))
        if in1 == 'SourceGraphic':
            pass
        patch = self.objs.get('patch:' + in2)  
        if patch != None:
            if mode == 'multiply':
                patch.set_alpha(0.5)  
   
    def get_feFlood(self, obj):
        x, y, w, h, fc, op = obj.get_values(('x', 'y', 'width', 'height', 'flood-color', 'flood-opacity'), None) 
        patch = patches.Rectangle((x, y), w, h, fc=fc, alpha=op) 
        self.ax.add_patch(patch)
        result = obj.get('result') 
        if result != None:
           self.objs['patch:' + result] = patch
        
    def get_feColorMatrix(self, obj):
        id, type, result = obj.get_items(('id', 'type', 'result'))
        values = obj.get_value('values')
        print('get_feColorMatrix', id, type, result, values)        
        
    def get_filter(self, filter):
        if not 'url' in filter:
            print('filter', filter)
            return
        e = self.get_url_obj(filter)        
        for obj in e.children:
            print(obj.tag, obj.dct)
            if obj.tag == 'feColorMatrix':
                self.get_feColorMatrix(obj)
            elif obj.tag == 'feFlood':
                self.get_feFlood(obj)
            elif obj.tag == 'feBlend':
                self.get_feBlend(obj)
        
    def draw_use(self, uobj, href):
        obj1 = href.copy()    
        for k, v in uobj.dct.items():
            if k != 'href':
               obj1.dct[k] = v
        obj1.init_obj()  
        print(obj1.transobj.items)
        self.draw_obj(obj1)          
            
    def read_use(self, e):
        print('read_use', e.dct)
        for k, v in e.items:                 
            if k == 'filter':
                e.filter = v
                self.get_filter(v)
            elif k.endswith('href'):
                href = self.objs.get(v)     
                self.draw_use(e, href)  
                
    def read_g(self, e): 
        for k, v in e.items:            
            if k == 'clip-path':                
                obj = self.get_url_obj(v)
                e.add_clip(obj.clip_path)
            else:
                self.style[k] = v   
        e.trans = e.transobj.trans
        for obj in e.get_children():  
            if e.trans != None:    
                obj.add_trans(e.trans)  
            if e.clip_path != None:
                obj.add_clip(e.clip_path)                   
            if obj.tag in ['g', 'use', 'image']:
                exec('self.read_' + obj.tag + '(obj)')   
            elif obj.tag == 'text':
                self.draw_text(obj)            
            elif obj.tag in self.draw_tags:
                self.draw_obj(obj)
            else:
                print('undefined ', obj.tag, obj.id)       
        
    def read_url(self, url, rawdata=False, method='get', fields={}):
        self.filename = url        
        http = urllib3.PoolManager()        
        if method == 'get':
           response = http.request('GET', url)
        else:
           response = http.request('POST', url, fields=fields) 
        status = response.status
        readable = response.readable()
        if status != 200 or readable == False:
            print(url, 'status=', status, 'readable=', readable)
            return 'error', ''       
        content_type = response.info().get('Content-Type')
        data_type = content_type.split('/', 1)[0]   
        if data_type == 'text':
            f = io.BytesIO(response.data)
            text = f.read().decode('utf-8')
            return data_type, text
        else:
            return data_type, response.data
        
    def get_url_path(self, path):
        i = path.find('//')
        j = path.find('/', i+2)
        return path[i:j]
        
    def read_image(self, e):     
        x, y, w, h, href = e.get_values(('x', 'y', 'width', 'height', 'href'))
        filter = e.get('filter')
        if href[0:2] == '//':
            href = 'http:' + href         
            datatype, rawdata = self.read_url(href, rawdata=True)
            if rawdata == '':
                return
            img = Image.open(io.BytesIO(rawdata))
        else:    
            path = os.path.realpath(href)
            print(href, path)
            img = Image.open(path)
        self.ax.imshow(img, extent=[x, x+w, y, y+h]) 
        if filter != None:            
            self.get_filter(filter)
                 
    def get_css_data(self, text):
        dct = {}
        for m in re.finditer('(?P<name>[^\:\s]+)\s*\:\s*(?P<value>[^\;]+)', text):
            dct[m.group('name')] = m.group('value')
        return dct
        
    def get_css_style(self, e):
        obj_name = ''
        for name, data in e.items:
            dct = self.get_css_data(data)
            if '#' in name:
                obj_name = name[1:]
                self.css_styles[obj_name] = dct                 
            elif '.' in name:
                s = name[1:]
                self.css_styles[obj_name][s] = dct
            else:
                self.css_styles[name] = dct        
            
    def read_defs_style(self, e):   
        for obj in e.get_children():
            if 'CDATA' in obj.tag:
                print(obj.tag, obj.style)
                self.get_css_style(obj)   
                 
    def get_defs_clip_path(self, e):
        for obj in e.get_children():
            obj.init_path() 
            pobj = obj.pobj            
            if pobj == None:
                continue
            e.add_clip(pobj.path)
            e.pobj = pobj
        
    def read_defs(self, e):                     
        for obj in e.get_children():  
            tag = obj.tag 
            if tag == 'style':
               self.read_defs_style(obj) 
            elif tag == 'clipPath':
               self.get_defs_clip_path(obj)  
            elif 'Gradient' in tag:
                pass              
            else:
               print('defs ->', obj.tag)        
                
    def get_draw_data(self, e, level):  
        if e.tag in self.draw_tags:
            self.draw_obj(e)
        level += 1
        for obj in e.get_children():      
            objdata = self.get_draw_data(obj, level)       
                          
         
class SvgPath(SvgObj):
    def __init__(self, plot, filename=None, text=None):
        SvgObj.__init__(self)
        self.ax = plot.ax        
        self.plot = plot
        self.fig = plot.fig
        self.dpi = self.fig.dpi
        self.ax.set_zorder(2)
        self.w, self.h = self.fig.get_figwidth(), self.fig.get_figheight()
        self.dct = {}
        self.text = text
        self.xmltype = ''
        self.doctype = ''
        self.filename = filename
        self.zorder = 1        
        self.load_svg(filename, text) 
        plot.draw_bkg(self.get_size())               
        
    def get_size(self):   
        lst = []
        for e in self.pobjs:
            if e.path == None:
                continue
            lst.append(e.path.get_extents())
        if lst == []:
            return self.ax.bbox
        b = lst[0].union(lst)            
        return b
            
    def set_size(self, w, h):  
        dpi = self.fig.dpi        
        self.size = (w, h)
        #print('set_size', (w, h), (self.w, self.h), dpi)  
        self.ax.plot()
            
    def load_svg_root(self, e):
        w, h = self.fig.get_figwidth(), self.fig.get_figheight()
        self.size = w, h
        for k, v in e.items:
            if k == 'width':            
                w = self.get_value_size(v, self.size[0])
            elif k == 'height':
                h = self.get_value_size(v, self.size[1])
            elif k == 'viewBox':
                if not ',' in v:
                    v = v.replace(' ', ',')
                self.viewbox = eval(v)  
                x, y, w, h = self.viewbox
            self.dct[k] = v
            #print('svg ', k, ':', v)          
        self.set_size(w, h)
        
    def load_children(self, e):        
        self.style = {}        
        self.trans = None
        tag = e.tag
        if tag in ['defs', 'g', 'use', 'image']:
            exec('self.read_' + tag + '(e)')               
        elif tag in self.draw_tags:
            self.draw_obj(e)    
        elif 'Gradient' in tag:
            pass     
        elif tag == 'svg':
            self.load_svg_root(e) 
            for e1 in e.get_children():  
                self.clip_path = None 
                self.load_children(e1)      
        else: 
            print('root - ', e.tag) 
        
    def load_root(self, tree_root):
        if tree_root.tag == 'svg':
            self.load_svg_root(tree_root)    
        for e in tree_root.get_children():   
            self.clip_path = None 
            self.load_children(e)       
             
    def load_svg(self, filename, text):
        if text == None:
           text = fread(filename)
        self.objs = {}
        self.tree = XmlTree(self, text)
        tree_root = self.tree.root
        self.load_root(tree_root)      

def test_xml(text=None, filename=None):
    from fileio import fread
    if text != None:
       s0 = text[0:4].strip()
       if s0 != '<svg' and s0 != '<?xm':
          return
    print('test file', filename)        
    if text == None:
       text = fread(filename)
    tree = XmlTree(text=text)                
    
def test_svg(filename='arc1', text=None, img=True):
    if text == None:
        fn = filename.split('/')[-1]
        if not '.svg' in filename:
            filename = 'svg/' + filename + '.svg'
    if text != None:
       s0 = text[0:4].strip()
       if s0 != '<svg' and s0 != '<?xm':
          return
    print('\nTest file ------- %s -------' % filename)
    plot = Plot()
    
    if text == None:
       text = fread(filename)
    svg = SvgPath(plot, text=text)    
    if img is not None:
        plot.show_image(filename)
    plot.ax.set_title(fn)
    plot.show()   


def view_text(text):
    plot = Plot()
    svg = SvgPath(plot, text=text)    

    plot.show()   
        
if __name__ == '__main__':     
    import os, sys      
    def test():        
        path = os.path.dirname(__file__)        
        test_svg(filename=path + '/svg/circle.svg', img=True) 
          
    if len(sys.argv) > 1:
        filename = sys.argv[1] 
        test_svg(filename, img=True)        
    else:        
        test() 
   
    



