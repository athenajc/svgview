import re
import numpy as np
from matplotlib import colors as mp_colors
import math
from svgcolors import svg_colors

class Object(object):            
    def get_value(self, s):
        if type(s) != str:
            return s        
        if '%' in s:
            s = s.replace('%', '/100')  
        m = re.findall('\#[abcdef\d]+|[\+\-\d\.e\/]+', s)
        if m == []:
            return None
        lst = []
        for s in m:
            if s == 'e':
                continue
            if s[0] == '#':
                lst.append(mp_colors.to_rgb(s))
            else:
                lst.append(eval(s))        
        if len(lst) == 1:
            return lst[0]
        return tuple(lst)        
     
    def get_value_size(self, s, size=1):
        if '%' in s:
            s = s.replace('%', '/100')                  
            v = self.get_value(s) * size
            return v
        return self.get_value(s)
               
    def get_item_value(self, k, default=None):
        v = self.get(k, None)
        if v != None:
            if k in ['stroke', 'fill', 'color', 'rgb'] or '#' in v:
                v = self.get_rgb(v)
            else:
                v = self.get_value(v)
        else:
            v = default
        return v
               
    def get_items(self, items):
        lst = []
        for k in items:      
            lst.append(self.get(k, None))
        return lst   
        
    def get_values(self, items, default=None):
        lst = []
        for k in items:
            v = self.get_item_value(k, default)
            lst.append(v)
        return lst
        
    def get_dct_values(self, dct, items, default=None):
        lst = []
        for k in items:
            v = dct.get(k, None)
            if v != None:
                v = self.get_value(v)
            else:
                v = default
            lst.append(v)
        return lst      
       
    def get_style_dct(self, text):
        #"fill:rgb(0,0,255);stroke-width:3;stroke:rgb(0,0,0)"
        dct = {}
        for s in text.split(';'):
            if not ':' in s:
                continue
            p = s.split(':')
            k, v = p[0], p[1].strip()                        
            dct[k] = v
        return dct
            
    def get_rgb(self, color):              
        if color == None or color == 'none':
            return color
        if 'url' in color:
            return color
        if type(color) == tuple:
            r, g, b = color            
            if type(r+g+b) == int and max(r, g, b) > 1:
               r, g, b = r/255, g/255, b/255 
            return (r, g, b)        
        if 'rgb' in color:
            s = color.replace('rgb', '')     
            if '%' in s:
                s = s.replace('%', '/100')   
                r, g, b = eval(s)                
                return r, g, b                
            r, g, b = eval(s)  
            if max(r, g, b) > 1:
               r, g, b = r/255, g/255, b/255
            return (r, g, b)                
        elif '#' in color:
            r, g, b = mp_colors.to_rgb(color)
        else:
            r, g, b = mp_colors.to_rgb(svg_colors.get(color, 'black'))
        return (r, g, b)          
        
    def get_url_obj(self, text):
        # "url(#grad1)"
        text = text.replace('url(', '').replace(')', '')        
        obj = self.objs.get(text.strip()) 
        if obj == None:
            print(text, 'not found')
        return obj
        
    def get_href(self):
        if self.href == None:
           self.href = self.svg.get_url_obj(self.xlink)
           
    def get_dct(self, text):
        dct = {}       
        lst = []    
        if 'CDATA' in self.tag:          
            pattern = '(?P<item>[\w\.\/\-\#]+)\s*\{\s*(?P<value>[^\}]+)\s*\}'        
        else:    
            pattern = '(?P<item>[\w\.\:\/\-\#]+)\s*\=\s*[\"\'](?P<value>[^\"]+)[\"\']'        
        for m in re.finditer(pattern, text):    
            item, value = m.group('item'), m.group('value')    
            if ':' in item:
                item = item.split(':')[-1].strip()       
            dct[item] = value  
            lst.append((item, value))          
        return dct, lst


if __name__ == '__main__':         
    from svgpath import test_svg    
    from mathxy import tlog
    #test_svg(filename='svg/gradtrans.svg', img=True) 
    print(type(1.1 + 2 + 3))
    obj = Object()
    for s in ['10px,2', '1.2cm', '-2', '3.3e4', '10 3 43', '3%', '(5%, 12%, 34%)', '(.1,.3, .5)', '#ff9933', '#660066']:
        v = obj.get_value(s)
        print(v)

        



