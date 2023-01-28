import numpy as np
import matplotlib as mp
from skimage import color 
from object import Object
from transobj import TransObj
from cairo_grad import CairoGradient
from mathxy import *
        
class StopObj(Object):
    def __init__(self, i, d, css):
        self.stop_alpha = 1  
        self.stop_color = (0, 0, 0)        
        self.offset = self.get_offset(d.get('offset'))   
        style = d.get('style')
        if style != None:
            self.from_style(style)
        elif css != None:
            self.from_css(css, i)
        else:
            self.from_tag(d)            
        rgb = self.get_rgb(self.stop_color)
        a = self.get_value(self.stop_alpha) 
        r, g, b = rgb
        self.rgba = r,g,b,a
        
    def __str__(self):
        return 'offset:'+str(self.offset) + ' rgba:' + str(self.rgba)
        
    def get_offset(self, s):
        if s == None:
            return 0
        if '%' in s:
            s = s.replace('%', '')
            v = eval(s) / 100
        else:
            v = eval(s)
        return v
        
    def get_color(self, rgba, filter):    
        if filter == None or filter == []:
            return rgba
        r, g, b, a = rgba
        rgb = np.array([r, g, b])
        hsv = color.rgb2hsv(rgb)
        for item in filter:
            ftype, id, result, value = item
            if ftype == 'hueRotate':
                hsv[0] += value
                rgb = color.hsv2rgb(hsv)                
        r, g, b = rgb
        return r, g, b, a         
        
    def from_tag(self, d):
        self.stop_color = d.get('stop-color')
        self.stop_alpha = d.get('stop-opacity', 1)     
             
    def from_style(self, style):
        for s in style.split(';'):
            p = s.split(':')
            if 'stop-color' in p[0]:                    
                self.stop_color = p[1].strip()
            elif 'opacity' in p[0]:
                self.stop_alpha = p[1].strip()
                
    def from_css(self, css, i):
        c = css.get('stop' + str(i))   
        for k, v in c.items():
            if k == 'stop-color':
                self.stop_color = v
            elif 'opacity' in k:
                self.stop_alpha = v        
        
class GradientObj(Object):
    def __init__(self, e, css=None):   
        self.stops = [] 
        if e == None:
            return  
        tag = e.tag
        self.tagobj = e
        self.rotate = 0
        self.mode = tag.replace('Gradient', '')
        self.grad_unit = e.get('gradientUnits')  
        self.grad_trans = e.get('gradientTransform')        
        self.spread = e.get('spreadMethod', 'pad')
        self.css = css   
        self.transobj = TransObj(self.grad_trans) 
        self.init_stops(e)     
        if self.mode == 'radial':
            cx, cy, r = e.get_values(['cx', 'cy', 'r']) 
            fx = e.get_item_value('fx', cx)
            fy = e.get_item_value('fy', cy)
            self.geom = cx, cy, r, fx, fy
        else:
            x1, x2, y1, y2 = e.get_values(['x1', 'x2', 'y1', 'y2'])
            self.geom = x1, x2, y1, y2         
    
    def get(self, item, default=None):
        return self.tagobj.get(item, default)
        
    def init_stops(self, e):   
        self.stops = []  
        if e.xlink != None:            
            if e.href == None:
                href = e.svg.get_url_obj(e.xlink) 
            else:
                href = e.href             
            e.add_childrens(href.get_children())
        for i, obj in enumerate(e.get_children()):
            if obj.tag == 'stop':
               stopobj = StopObj(i+1, obj, self.css)
               self.stops.append(stopobj)            
                    
    def linear_gradient(self, spread):          
        if self.grad_unit == "userSpaceOnUse":
            x0, x1, y0, y1 = self.path_box
            w, h = int(x1-x0), int(y1-y0)
            img = CairoGradient((w, h)).lgrad(self.geom, self.colors, spread)
        else:            
            img = CairoGradient((200, 200)).lgrad(self.geom, self.colors, spread)    
        return img         
            
    def get_rdata(self, box=None):
        cx, cy, r, fx, fy = self.geom
        if box != None:
            x0, x1, y0, y1 = box
            w, h = x1-x0, y1-y0
            r2 = r * 2
            cx, cy = cx - x0, cy - y0
            fx, fy = fx - x0, fy - y0
            cx, cy, r, fx, fy = (cx/w, cy/h, r/r2, fx/w, fy/h)  
        if cx == None:
            cx, cy, r, fx, fy = .5, .5, .5, .5, .5  
        return cx, cy, r, fx, fy
        
    def radial_gradient(self, spread):                
        if self.grad_unit == "userSpaceOnUse":
            x0, x1, y0, y1 = self.path_box
            w, h = int(x1-x0), int(y1-y0)
            n = max(w, h)
            data = self.get_rdata(self.path_box)
            img = CairoGradient((n, n)).rgrad(data, self.colors, spread)
        else:
            data = self.get_rdata()
            img = CairoGradient((200, 200)).rgrad(data, self.colors, spread)    
        return img
    
    def get_array(self):    
        if self.mode == 'radial':
            a = self.radial_gradient(self.spread)            
        else:   
            a = self.linear_gradient(self.spread) 
        a = self.transobj.trans_array(a) 
        return a
        
    def get_colors(self, filter):
        colors = []            
        for p in self.stops:
            colors.append((p.offset, p.get_color(p.rgba, filter)))    
        self.colors = colors                
        
    def get_cmap(self, filter):           
        self.get_colors(filter)
        cmap = mp.colors.LinearSegmentedColormap.from_list('grad', self.colors) 
        return cmap      
        
    def set_box(self, box):
        w, h = int(box.width), int(box.height)
        self.size = w, h
        x0, x1, y0, y1 = box.x0, box.x1, box.y0, box.y1    
        if self.grad_unit == 'userSpaceOnUse':    
            d = (w-h)/max(w, h)
            if d > 0.1:
                y = (y0 + y1)/2
                y0 = y - w/2
                y1 = y + w/2         
            elif d < -0.1:
                x = (x0 + x1)/2
                x0, x1 = x - h/2, x + h/2
        self.box = x0, x1, y0, y1
               
    def get_box(self, path, fillobj):     
        self.set_box(path.get_extents())
        box = fillobj.pobj.path.get_extents()
        self.path_box = (box.x0, box.x1, box.y0, box.y1)
        return self.box                     
        
    def gradient_fill(self, ax, fillobj, path, alpha=1, stroke=False): 
        if self.stops == [] or path == None:
            return      
        self.rotate = fillobj.transobj.get_rotate()
        box = self.get_box(path, fillobj) 
        w, h = self.size
        if w == 0 or h == 0:
            return
        self.get_colors(fillobj.filters)  
        p = mpPath(path).get_patch(transform=ax.transData)
        z = self.get_array()   
        zo = ax.zorder
        im = ax.imshow(z, extent=box, clip_path=p, clip_on=True, origin='lower', zorder=zo)
        if stroke == True and self.rotate != 0:
            t = fillobj.transobj.get_trans()
            im.set_transform(t + ax.transData)
        if alpha != 1:
            im.set_alpha(alpha)
            
if __name__ == '__main__':         
    def test(i):
        from svgpath import test_svg
        lstr = ['grad2', 't1', 'rad_gradient1', 'gradtrans']    
        lstl = ['g_spread', 'anki', 'stroke_grad', '3depict', 'gradient', 'anjuta', 'lgrad1']
        lstg = ['g_trans', 'g_trans1',  'g_trans2', 'grad2', 'grad3', 'grad4']
        lst1 = ['gradtrans']
        
        dct = {'R':lstr, 'L':lstl, '1':lst1, 'g':lstg, 'a':lstr+lstl+lstg}
        for fn in dct.get(i, []):        
            test_svg(filename='svg/%s.svg'%fn, img=True) 
    test('1')
    


