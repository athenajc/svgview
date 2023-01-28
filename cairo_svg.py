import numpy as np
import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk
import cairo
import math 
from svgpath import XmlTree
from fileio import fread    
from ui import ImageObj
from pathobj import PathObj
from mathxy import *     

def _append_path(ctx, path, transform, clip=None):
    for points, code in path.iter_segments(
            transform, remove_nans=True, clip=clip):
        if code == Path.MOVETO:
            ctx.move_to(*points)
        elif code == Path.CLOSEPOLY:
            ctx.close_path()
        elif code == Path.LINETO:
            ctx.line_to(*points)
        elif code == Path.CURVE3:
            cur = np.asarray(ctx.get_current_point())
            a = points[:2]
            b = points[-2:]
            ctx.curve_to(*(cur / 3 + a * 2 / 3), *(a * 2 / 3 + b / 3), *b)
        elif code == Path.CURVE4:
            ctx.curve_to(*points)
                
class CairoSurface(object):
    def __init__(self):
        self.surface = None
        self.context = None
        self.dpi = 10
        
    def init_surface(self, w, h):
        self.size = w, h
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)    
        self.context = cairo.Context(self.surface)  
        
    def get_array(self):
        w, h = self.size
        surface = self.surface
        surface.flush()
        pb = Gdk.pixbuf_get_from_surface(surface, 0, 0, w, h)
        surface.finish()  
        imgobj = ImageObj(pixbuf=pb)
        img = imgobj.get_array()
        return img     
                        
    def show(self):
        img = self.get_array()     
        plot, ax = new_plot()     
        ax.imshow(img, zorder=1)
        plot.show()
        

class CairoGradient():     
    def __init__(self, e, gobj):
        self.eobj = e
        self.gobj = gobj
        self.get_stops(gobj)        
        self.spread = gobj.get('spreadMethod', 'pad')
        self.mode = gobj.tag 
        self.box = e.box
        x0, x1, y0, y1 = e.box
        w, h = int(abs(x1-x0)), int(abs(y1-y0))
        self.size = w, h
        if self.mode == 'radialGradient':
            cx, cy, cr = gobj.get_values(['cx', 'cy', 'r'])
            if cx == None:
                cx, cy, cr, fx, fy = .5, .5, .5, .5, .5
            else:
                fx = gobj.get_item_value('fx', cx)
                fy = gobj.get_item_value('fy', cy)  
            self.data = cx, cy, cr, fx, fy
            self.grad = self.radial_gradient()               
        else:
            self.data = gobj.get_values(['x1', 'x2', 'y1', 'y2'])  
            self.grad = self.linear_gradient()            
            
    def get_grad(self):
        return self.grad
        
    def get_stops(self, gobj):
        self.offsets = []
        self.colors = []
        for stop in gobj.get_children():
            offset = stop.get_item_value('offset')
            r, g, b = stop.get_rgb(stop.get('stop-color'))
            a = stop.get_item_value('stop-opacity', 1)
            self.offsets.append(offset)
            self.colors.append((r, g, b, a))
            
    def add_stops(self, grad):
        for offset, rgba in zip(self.offsets, self.colors):            
            r, g, b, a = rgba
            grad.add_color_stop_rgba(offset, r, g, b, a)       
                         
    def linear_gradient(self):            
        x1, x2, y1, y2 = self.data 
        bx0, bx1, by0, by1 = self.box
        w, h = self.size 
        if x1 == None:
            x1, x2, y1, y2 = 0, 1, 0, 0           
        if max(self.data) <= 1:        
            x1, y1, x2, y2 = x1*w, y1*h, x2*w, y2*h             
        grad = cairo.LinearGradient(bx0+x1, by0+y1, bx0+x2, by0+y2)   
        self.add_stops(grad)
        return grad
        
    def radial_gradient(self):            
        cx, cy, cr, fx, fy = self.data       
        x0, x1, y0, y1 = self.box
        w, h = self.size
        if max(self.data) <= 1:         
            cx, cy, cr, fx, fy = cx*w, cy*h, cr*max(w,h), fx*w, fy*h
        grad = cairo.RadialGradient(x0+fx, y0+fy, 0, x0+cx, y0+cy, cr)   
        self.add_stops(grad)   
        return grad
        

class CairoGradientSpread(CairoGradient):     
    def add_stops(self, grad):
        i0, i1 = self.gradpad
        print('gradpad', i0, i1)
        spread = self.spread 
        m = 1/i1   
        i = i0    
        colors = self.colors.copy()
        while i < 1:
            if spread == 'reflect':
                colors.reverse()
            for offset, rgba in zip(self.offsets, colors):            
                r, g, b, a = rgba
                if a == None:
                    grad.add_color_stop_rgb(i + offset/m, r, g, b)
                else:
                    grad.add_color_stop_rgba(i + offset/m, r, g, b, a)
            if spread == 'pad':
                break
            i += i1                   
    
    def get_dxyr(self, data, size):
        w, h = size
        cx, cy, r, fx, fy = data
        e = Ellipse((cx, cy), (r, r))
        a = e.get_angle((fx, fy))
        x1, y1 = e.get_point(a)
        dx1, dy1 = x1-fx, y1-fy 
        d1 = np.hypot(dx1, dy1)        
        d2 = np.hypot(w, h) /2
        d3 = d2-r
        n = int(d3 / d1)
        dr = r - d1/2
        t = np.deg2rad(a) 
        dx = -(dr*math.cos(t) - dx1)
        dy = -(dr*math.sin(t) - dy1)
        return dx, dy, dr, n+1       
                
    def get_rgrad(self, data, size):
        w, h = size
        cx, cy, cr, fx, fy = data        
        cx, cy, cr, fx, fy = cx*w, cy*h, cr*w, fx*w, fy*h   
        dx, dy, dr, n = self.get_dxyr((cx, cy, cr, fx, fy), size)                    
        grad = cairo.RadialGradient(fx, fy, 0, cx+dx*n, cy+dy*n, cr+dr*n)            
        self.add_stops_pad(grad)      
        return grad                
        
    def linear_gradient(self):            
        x1, x2, y1, y2 = self.data 
        bx0, bx1, by0, by1 = self.box
        w, h = self.size 
        if x1 == None:
            x1, x2, y1, y2 = 0, 1, 0, 0           
        if max(self.data) <= 1:        
            if x1 != x2 and abs(x2-x1) < 1:
                self.gradpad = (x1, x2)
            if y1 != y2 and abs(y2-y1) < 1:
                self.gradpad = (y1, y2)
            x1, y1, x2, y2 = x1*w, y1*h, x2*w, y2*h      
        if x1 == x2:
            y1, y2 = by0, by1
            x1, x2 = bx0+x1, bx0+x2            
        elif y1 == y2:
            x1, x2 = bx0, bx1        
            y1, y2 = by0+y1, by0+y2
        grad = cairo.LinearGradient(x1, y1, x2, y2)   
        self.add_stops(grad)
        return grad
        
    def radial_gradient(self):            
        cx, cy, cr, fx, fy = self.data       
        x0, x1, y0, y1 = self.box
        w, h = self.size
        if max(self.data) <= 1:      
            self.gradpad = 0, cr      
            cx, cy, cr, fx, fy = cx*w, cy*h, cr*max(w,h), fx*w, fy*h
        else:
            self.gradpad = 0, cr/w   
        grad = cairo.RadialGradient(x0+fx, y0+fy, 0, x0+cx, y0+cy, cr)   
        self.add_stops(grad)   
        return grad        
        

class CairoSvg(CairoSurface):
    def __init__(self, xmltext):
        self.objs = {}
        self.style = {}
        self.pobjs = []
        self.dpi = 10
        self.xmltext = xmltext
        self.surface = None
        tree = XmlTree(self, xmltext)
        if tree.root.tag == 'svg':
           self.init_svg(tree.root)    
        else:               
            for obj in tree.root.get_children():
                if obj.tag == 'svg':
                    self.init_svg(obj)
                    break
        for obj in tree.root.get_children():
            self.get_child(obj, 0)       
        box = self.get_box()
        w, h = box.width, box.height
        w1, h1 = w/20, h/20
        w += w1*2
        h += h1*2
        if w > 1000 or h > 1000:
            self.dpi = 0.5
        elif w > 100 or h > 100:
            self.dpi = 1
        else:
            self.dpi = 10
        self.init_surface(int(w*self.dpi), int(h*self.dpi))
        self.context.translate(-box.x0+w1, -box.y0+h1)
        self.context.scale(self.dpi, self.dpi)
        for obj in self.pobjs:
            self.draw_obj(obj, self.context)      
        
    def init_svg(self, obj):                    
        w = obj.get_item_value('width', 100)
        h = obj.get_item_value('height', 100)
        viewbox = obj.get('viewBox')
        #print('viewBox', viewbox)
        if viewbox != None:
            x, y, w, h = eval(viewbox.replace(' ', ','))
        #print('size', w, h)        
        
    def get_box(self):   
        lst = []
        for e in self.pobjs:
            if e.path == None:
                continue
            lst.append(e.path.get_extents())
        if lst == []:
            w, h = self.size
            return (0, 0, w, h)
        b = lst[0].union(lst)     
        self.box = b       
        return b
        
    def read_g(self, e): 
        for k, v in e.items:            
            if k == 'clip-path':                
                obj = self.get_href_obj(v)
                e.add_clip(obj.clip_path)
            else:
                self.style[k] = v   
        e.trans = e.transobj.trans
        for obj in e.get_children():  
            if e.trans != []:    
                obj.add_trans(e.trans)  
            if e.clip_path != None:
                obj.add_clip(e.clip_path) 
                
    def get_child(self, e, level):
        if e.id != None:
           self.objs[e.id] = e
        #print('   ' * level, e.tag, e.id)
        if e.tag in ['path', 'rect', 'ellipse', 'polygon', 'circle', 'line'] :
            self.get_path(e)     
            self.pobjs.append(e)     
        elif e.tag == 'g':
            self.read_g(e)
        for obj in e.get_children():
            self.get_child(obj, level+1)
            
    def get_href_obj(self, href):
        url = href.replace('url(#', '').replace(')', '')
        obj = self.objs.get(url)
        return obj
            
    def copy_href(self, gobj):
        href = gobj.get('href')
        if href != None:
            hobj = self.get_href_obj(href)
            gobj.add_childrens(hobj.get_children())
        
    def get_grad(self, e, url):
        gobj = self.get_href_obj(url)
        self.copy_href(gobj)
        gobj.spread = gobj.get('spreadMethod', 'pad')            
        if gobj.spread == 'pad':
            grad = CairoGradient(e, gobj).get_grad()          
        else:
            grad = CairoGradientSpread(e, gobj).get_grad()
        return grad
                
    def set_source(self, e, cxt, color):      
        if color == None or color == 'none':
            return
        #print('set_source', color)
        if 'url' in color:
            grad = self.get_grad(e, color)            
            cxt.set_source(grad)
        else:
            r, g, b = e.get_rgb(color)
            cxt.set_source_rgb(r, g, b)            
        return color       
            
    def draw_path(self, path, cxt):
        prev = None
        for a, c in path.iter_segments():            
            if c == 1:
                cxt.move_to(a[0], a[1])                
            elif c == 2:     
                cxt.line_to(a[0], a[1])
            elif c == 3:
                x, y = prev
                c, d, e, f = a
                cxt.curve_to(x, y, c, d, e, f)   
            elif c == 4:
                x, y, c, d, e, f = a
                cxt.curve_to(x, y, c, d, e, f)   
            elif c == 79:
                cxt.close_path()                    
            prev = a[-2:]
            
    def get_path(self, e):
        pobj = PathObj(e)
        path = pobj.path
        if path == None:
            return False
        trans = e.transobj.get_trans() 
        if trans != None:
           path = trans.transform_path(path)    
        box = path.get_extents()    
        e.box = (box.x0, box.x1, box.y0, box.y1)
        e.pobj = pobj
        e.path = path
        return True
        
    def draw_obj(self, e, cxt):         
        tag = e.tag
        if e.path == None:
            return
        self.draw_path(e.path, cxt)
        fc = self.set_source(e, cxt, e.get('fill'))
        stroke = e.get('stroke')
        if fc != None:
            if stroke == None:
                cxt.fill()
                return
            cxt.fill_preserve()   
        ec = self.set_source(e, cxt, stroke)
        lw = e.get_item_value('stroke-width', 1)
        if ec != None and lw != 'none':
            cxt.set_line_width(lw)
            cxt.stroke()       
            

if __name__ == '__main__':     
    def test(filename):
        text = fread('/home/athena/src/svg/svg/' + filename + '.svg')
        #print(text)
        svg = CairoSvg(text)
        svg.show()
        
    lstr = ['grad2', 't1', 'rad_gradient1', 'gradtrans']    
    lstl = ['g_spread', 'anki', 'stroke_grad', '3depict', 'gradient', 'anjuta']
    lstg = ['g_trans', 'g_trans1',  'g_trans2', 'grad2', 'grad3', 'grad4']
    lst1 = ['gradtrans']
            
    test('3depict')



