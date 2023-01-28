import tkinter as tk
import re
from matplotlib import patches, transforms
from object import Object
from pathobj import PathObj
from gradient import GradientObj  
from transobj import TransObj
from mathxy import *

class TagObj(Object):
    def __init__(self, tag, content='', span=None):
        self.style = {}
        self.children = []
        self.tag = tag       
        self.span = span  
        self.svg = None
        self.css_style = None
        self.items = []
        if type(content) == dict:
            self.dct = content
            for k, v in self.dct.items():
                self.items.append((k, v))
        else:
            content = content.strip()    
            self.content = content   
            self.dct, self.items = self.get_dct(self.content)
            self.without_endtag = content.endswith('/') 
        self.init_style()        
        if 'CDATA' in self.tag: 
            self.without_endtag = True
        self.pobj = None
        self.group = None
        self.href = None      
        self.clip_path = None  
        self.filters = None  
        self.path = None
        self.stroke = None    
        self.patches = [] 
        
        self.id = self.dct.get('id')        
        self.xlink = self.dct.get('href')
        self.init_obj()
        
    def init_obj(self):  
        self.lw = self.get_item_value('stroke-width')    
        self.transobj = TransObj(self.dct.get('transform'))  
        
    def __str__(self):
        return str(self.dct)
               
    def get(self, key, default=None):        
        if key in self.dct:
            return self.dct.get(key)
        if key in ['tag','isend', 'content', 'span']:
            return self.__getattribute__(key) 
        if self.svg != None:                   
           if key in self.svg.style:
               return self.svg.style.get(key)   
        return default            
        
    def copy(self):
        obj = TagObj(self.tag, self.content, self.span)
        obj.children = self.children.copy()
        return obj  
        
    def get_children(self):
        return self.children
        
    def add_childrens(self, lst):
        for obj in lst:
            self.children.append(obj)
        
    def set_text(self, text):
        self.dct['text'] = text
        
    def init_style(self):
        style_str = self.dct.get('style') 
        if style_str == None:
            self.style = {}
            return
        self.style = self.get_style_dct(style_str)
        for k, v in self.style.items():
            self.dct[k] = v
        
    def get_style_dct(self, style_str):
        #"fill:rgb(0,0,255);stroke-width:3;stroke:rgb(0,0,0)"
        dct = {}
        for s in style_str.split(';'):
            if not ':' in s:
                continue
            p = s.split(':')
            k, v = p[0].strip(), p[1].strip()                        
            dct[k] = v
        return dct  
        
    def get_linestyle(self):
        cap = self.get('stroke-linecap')
        join = self.get('stroke-linejoin')
        if cap == None:
            cap = 'butt'
        if join == None:
            join = 'miter'
        limit = 4    
        return cap, join, limit
        
    def set_feColorMatrix(self, obj):        
        id, type, result = obj.get_items(('id', 'type', 'result'))
        value = obj.get_values(['values'])[0]        
        if type == 'hueRotate':
            value = (value/360) * 255            
            self.filters.append(('hueRotate', id, result, value))
        else:
            self.filters.append((type, id, result, value))
            print('set_feColorMatrix   ', id, type, result, value)   
        
    def init_filter(self):
        self.filters = []
        filter = self.get('filter')
        if filter == None:
            return
        filter = self.svg.get_url_obj(filter)             
        for obj in filter.children:
            if obj.tag == 'feColorMatrix':
                self.set_feColorMatrix(obj)
            else:
                print(obj.dct)          

    def add_trans(self, trans):
        self.transobj.add_trans(trans)
            
    def add_clip(self, clip):
        self.clip_path = clip

    def get_fill_path(self, path):
        if path == None:
            return  
        if self.clip_path == None:
            return path
        if self.clip_path.contains_path(path):
            return path
        return self.pobj.get_fill_path(path, self.clip_path)        
        
    def get_trans(self, ax):
        trans = self.transobj.get_trans()
        if trans == None:
            return ax.transData
        else:
            return trans + ax.transData
            
    def get_alpha(self, tag):
        opacity = self.get_item_value('opacity')
        alpha = self.get_item_value(tag + '-opacity')        
        if opacity == 0 or alpha == 0:
            return 0             
        if opacity == None:
            opacity = 1
        if alpha == None:
            alpha = 1   
        alpha *= opacity
        return alpha

    def get_patch(self, ax, fc, a):                
        patch = patches.PathPatch(self.path, fc=fc, ec='none', lw=0, alpha=a, zorder=self.zorder)
        if self.clip_path != None:            
           patch.set_clip_path(self.clip_path, ax.transData)    
        ax.add_patch(patch)          
        return patch
        
    def draw_patch(self, svg, ax, css):                
        alpha = self.get_alpha('fill')
        self.patch_alpha = alpha         
        fc = self.get('fill')     
        if fc != None and 'url' in fc:        
            e = self.svg.get_url_obj(fc) 
            if e == None:
                return   
            self.patch = self.get_patch(ax, 'none', 0)
            path = self.get_fill_path(self.path)   
            GradientObj(e, css).gradient_fill(ax, self, path, alpha)                     
            return 
        if fc in [None, 'transparent', 'none']:
            return
        fc = self.get_rgb(fc)          
        self.patch = self.get_patch(ax, fc, alpha)   
            
    def get_stroke(self, ax, fill='none', a=1):        
        if self.stroke == None:
            return
        path = self.stroke    
        patch = patches.PathPatch(path, fc=fill, alpha=a, ec='none', lw=0, zorder=self.zorder)
        if self.clip_path != None:            
            patch.set_clip_path(self.clip_path, ax.transData)    
        ax.add_patch(patch)        
        return patch  
        
    def draw_stroke(self, svg, ax, css):        
        if self.stroke == None:
            return                
        alpha = self.get_alpha('stroke')
        lw = self.get_item_value('stroke-width')       
        if alpha == 0 or lw == 0:
            return              
        self.stroke_alpha = alpha
        ec = self.get('stroke') 
        if ec != None and 'url' in ec:             
            grad = self.svg.get_url_obj(ec) 
            self.stroke_patch = self.get_stroke(ax, fill='none', a=1)
            if self.stroke_patch != None:              
                path = self.get_fill_path(self.stroke)   
                GradientObj(grad, css).gradient_fill(ax, self, path, alpha, stroke=True) 
            return               
        if ec == 'none' or ec == None:    
            return           
        ec = self.get_rgb(ec)                  
        patch = self.get_stroke(ax, fill=ec, a=alpha)   
            
    def test_stroke(self, ax):
        if self.stroke != None:
           patch = patches.PathPatch(self.stroke, fc='gray', ec='black', lw=1, alpha=0.3)
           if self.clip_path != None:            
               patch.set_clip_path(self.clip_path, ax.transData)
           ax.add_patch(patch)
           
    def test_path(self, ax):
        if self.path != None:
           patch = patches.PathPatch(self.path, fc='none', ec='blue', lw=1)
           if self.clip_path != None:            
               patch.set_clip_path(self.clip_path, ax.transData)
           ax.add_patch(patch)        
        
    def init_path(self):
        self.pobj = PathObj(self, self.tag)                
        self.path = self.pobj.path
        self.stroke = self.pobj.stroke
        if self.path == None:
            return
        self.trans = self.transobj.get_trans() 
        if self.trans != None:
           t = self.trans 
           self.path = t.transform_path(self.path)
           if self.pobj.stroke == None:
               return
           self.stroke = t.transform_path(self.stroke)               
           
    def draw_obj(self, svg, ax):   
        self.ax_trans = ax.transData
        self.patches = []
        self.init_path()  
        if self.path == None:
            return False          
        self.svg = svg    
        css = self.css_style  
        if css != None:
            for k, v in css.items():
                if not k in self.dct:
                   self.dct[k] = v
        if self.get_item_value('opacity') == 0:
            return False         
        if self.get('fill') == None and self.get('stroke') == None:
            self.dct['fill'] = 'black'  
        self.init_filter()        
        self.zorder = ax.zorder   
        if 0:     
            self.test_path(ax)  
            self.test_stroke(ax)               
        else:  
            self.draw_patch(svg, ax, css)   
            self.draw_stroke(svg, ax, css)
        ax.set_zorder(self.zorder + 1) 
        return True

if __name__ == '__main__':     
    from svgpath import test_svg
    from matplotlib import pyplot as plt
    def test_file(s):    
        from svgpath import test_svg        
        plt.style.use('seaborn-dark')
        filename = 'svg/%s.svg' %s
        test_svg(filename=filename, img=True) 
        
    for fn in [ 'css_cdata', 'lgrad1']:
        test_file(fn) 





