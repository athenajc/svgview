import re
import numpy as np
from matplotlib import patches, transforms
from object import *
from mathxy import *

    
class PathObj(object):
    def __init__(self, e=None, dtype=None): 
        self.tagobj = e
        if dtype == None:
            dtype = e.get('tag')
        self.dtype = dtype
        self.arcs = []        
        self.verts = []
        self.codes = []     
        self.error = False 
        self.path = None  
        self.stroke = None        
        self.lw = e.get_item_value('stroke-width', 1) 
        if e.get('stroke') == 'none':
            self.lw = 0
        self.linestyle = e.get_linestyle()
        acts = {'rect':self.rect, 'circle':self.circle, 'ellipse':self.ellipse,
                'path':self.read_path, 'polygon':self.polygon, 'line':self.line}         
        path_act = acts.get(dtype)
        if path_act == None:
            return
        path_act(e)           
        if self.path == None:
            return
        if self.stroke == None:
           self.stroke = self.get_outline(self.lw, self.linestyle)     
        self.verts = self.path.vertices
        self.codes = self.path.codes               
        
    def transformed(self, t):    
        if t == None:              
            return   
        self.path = self.path.transformed(t)
        if self.stroke != None:
           self.stroke = self.stroke.transformed(t) 
    
    def get_path_z(self, cmd, a, v0):        
        return [v0], [CLOSEPOLY]
        
    def get_path_m(self, cmd, a, v0):
        if cmd.islower():
           a[0] += v0
        return [a[0]], [MOVETO] 
             
    def get_path_l(self, cmd, a, v0):
        if cmd.islower():
           a[0] += v0  
        return [a[0]], [LINETO]   
         
    def get_path_h(self, cmd, a, v0):
        x0, y0 = v0
        x1 = a[0]
        if cmd.islower():
           x1 += x0
        return [(x1, y0)], [LINETO]   
        
    def get_path_v(self, cmd, a, v0):
        x0, y0 = v0
        y1 = a[0]
        if cmd.islower():
           y1 += y0  
        return [(x0, y1)], [LINETO]   
        
    def get_path_cl(self, cmd, a, v0):        
        n = a.shape[0]       
        verts = []        
        for i in range(0, n, 3):            
            verts += [a[i]+v0, a[i+1]+v0, a[i+2]+v0]
            v0 = verts[-1]
        codes = [CURVE4] * n 
        return verts, codes
        
    def get_path_curve(self, cmd, a, v0):        
        va = list(a)
        va.insert(0, v0)
        verts = curve(va) 
        return verts, [LINETO] * (len(verts))
        
    def get_path_c(self, cmd, a, v0):
        n = a.shape[0]       
        if cmd.islower():       
            if n > 3:
                return self.get_path_cl(cmd, a, v0)
            a += v0   
        return a, [CURVE4] * n 
                   
    def get_path_q(self, cmd, a, vert0):
        if cmd.isupper():
           v0 = (0, 0)
        else:
           v0 = vert0
        return [vert0, a[0] + v0, a[1] + v0], [CURVE4, CURVE4, CURVE4]  
               
    def get_path_a(self, cmd, a, v0):
        rx, ry, rotate, large, sweep, x1, y1 = a
        if rx == 0 or ry == 0:         
            self.error = True
            return [], []
        if cmd.islower():
            x0, y0 = v0
            x1 += x0
            y1 += y0
        path = Ellipse().get_arc_path((v0, (x1, y1), (rx, ry), rotate, large, sweep))       
        return path.vertices[1:], path.codes[1:]    
        
    def read_d(self, d):
        lst = []
        for m in re.finditer('(?P<c>[a-zA-Z])\s*(?P<p>[\d\s\.e\-\,]*)', d):                 
            c = m.group('c')
            alst = re.findall('[\d\.\-e]+', m.group('p').strip())
            a = np.array(alst).astype(float)
            n = len(alst)
            if n % 2 == 0:
                a = a.reshape((n//2, 2)) 
            lst.append((c, a))
        return lst
        
    def read_path(self, e):
        d = e.get('d')
        if d == None or d == '':
            return
        verts, codes = [], []
        v0 = (0, 0) 
        error = False
        for c, a in self.read_d(d):
            c1 = c.lower()
            if not c1 in 'aclmqzhv':
                print(c, a, d)
                continue
            action = eval('self.get_path_' + c1)
            if action != None:    
                va, ca = action(c, a, v0)
                if va == []:
                    error = True                
                    return 
                verts += list(va)
                codes += list(ca)
                v0 = verts[-1]             
        self.path = mpPath(verts, codes)
        if self.lw == 0:
            return
        if codes[-1] == 79:            
            self.stroke = self.path.get_stroke(self.lw)
        
    def round_rect(self, e):
        x, y, rx, ry, w, h = e.get_values(['x', 'y', 'rx', 'ry', 'width', 'height'], 0) 
        self.path = mpPath().round_rect(x, y, w, h, rx)   
        self.stroke = mpPath(self.path).get_stroke(self.lw)        
            
    def rect(self, e):
        rx, ry = e.get_values(['rx', 'ry'])                
        if rx != None and rx != 0:
            return self.round_rect(e)
        x, y, w, h = e.get_values(['x', 'y', 'width', 'height'], 0) 
        self.path = mpPath().rect(x, y, w, h)
        self.stroke = mpPath().rect_stroke(x, y, w, h, self.lw)        
        
    def circle(self, e):
        cx, cy, r = e.get_values(['cx', 'cy', 'r'], 0)
        verts, codes = Ellipse((cx, cy), (r, r)).get_vc()
        self.path = mpPath(verts, codes)
        self.stroke = self.path.get_stroke(self.lw)        
        
    def ellipse(self, e):
        cx, cy, rx, ry, rotate = e.get_values(['cx', 'cy', 'rx', 'ry', 'rotate'], 0)
        verts, codes = Ellipse((cx, cy), (rx, ry), rotate=rotate).get_vc()   
        self.path = mpPath(verts, codes)
        self.stroke = self.path.get_stroke(self.lw)    
        
    def polygon(self, e):
        s = e.get('points')
        a = np.array(re.findall('[\d\.\-]+', s)).astype(float)
        verts = list(a.reshape((a.size//2, 2))) 
        n = len(verts)        
        codes = [MOVETO] + [LINETO] * (n-1) + [CLOSEPOLY]        
        self.path = mpPath(verts + [(0, 0)], codes)            
        v, c = Line(verts + [verts[0]]).get_outline(self.lw, self.linestyle)
        self.stroke = mpPath(v, c)  
        
    def line(self, e):
        x1, y1, x2, y2 = e.get_values(['x1', 'y1', 'x2', 'y2'], 0)  
        p0 = x1, y1
        p1 = x2, y2
        verts, codes = [p0, p1], [MOVETO, LINETO]
        self.path = mpPath(verts, codes)                
        v, c = Line(verts).get_outline(self.lw, self.linestyle)
        self.stroke = mpPath(v, c)          
        
    def get_bbox(self, path, clip_path=None):        
        path = mpPath(path.vertices[:-1])    
        box = path.get_extents()        
        if clip_path != None:
            box1 = clip_path.get_extents()
            box = transforms.Bbox.intersection(box, box1)
            if box == None:
                return None
        return box
        
    def split_path(self, path):          
        a = np.argwhere(path.codes == 1).flatten()
        n = a.size
        if n == 0:
            return []
        if n == 1:
            return [path]
        print(n, a)
        lst = []
        i0 = 0
        verts = path.vertices
        for i in a:
            i = int(i)
            lst.append(mpPath(verts[i0:i], path.codes[i0:i]))
            i0 = i
        lst.append(mpPath(verts[i0:], path.codes[i0:]))
        return lst
        
    def get_outline(self, lw, style):       
        if self.stroke != None:
            return self.stroke                    
        if self.path == None or len(self.path.vertices) < 2:
            return 
        
        lst = self.split_path(self.path)
        if lst == []:
            return           
        verts = []
        codes = []        
        for path in lst:
            poly = PolyObj().from_path(path)                    
            v, c = poly.get_outline(lw, style)
            verts += v
            codes += c
        if verts == []:
            return    
        path1 = mpPath(verts, codes)
        return path1
                
    def iter_path(self):
        if self.path == None:
            return []
        verts = []
        for a, c in self.path.iter_segments(): 
            if c == 1:
                verts.append(a)
            elif c == 2:
                p0 = verts[-1]
                p1 = (a[0], a[1])
                x, y = get_line(p0, p1)
                verts += list(zip(x, y))
            elif c == 4 or c == 3:
                verts += get_curve(a, c, verts[-1])   
        return verts
                
    def get_fill_path(self, path0, path1): 
        poly0 = PolyObj().from_path(path0)
        poly1 = PolyObj().from_path(path1)        
        verts = poly0.clip_with(poly1) 
        if verts == []:
            return  
        return mpPath(verts)
                 
    def test_path(self, ax, **kw):  
        patch = self.get_patch(**kw)     
        n = len(self.verts)
        for i in range(n-1):
            p = self.verts[i]
            scatter(ax, p, i)
        ax.add_patch(patch)           

def load_path(filename=None, d=None):
    if d != None:
        e = {'d': d, 'tag':'path'}
        p = PathObj(e) 
        return p
        
    import fileio, re
    text = fileio.fread(filename)
    lst = []
    for s in re.findall('d\=[\"][^\"]+', text):                    
        e = {'d': s[3:], 'tag':'path'}
        p = PathObj(e)   
        lst.append(p)
    return lst
    
if __name__ == '__main__':      
    from tagobj import TagObj           
    d0 = "M80 80   A 45 45, 0, 0, 0, 125 125  L 125 80 Z"
    d="M 42.845769,30.83851 C 38.552717,32.180081 30.842647,33.809943 26.941861,38.694283"
    
    transform=(1.100743,0,0,1.2424615,69.38712,-71.251202)
    def test_path(plot, p, fill=None):
        v,c = p.get_stroke(1)        
        path1 = mpPath(v, c)
        plot.add_path(path1, fc='none', ec='black', lw=1)
               
    def test(filename):
        plot = Plot()
        fill = 'none'
        lst = load_path(filename)
        for p in lst[0:1]:            
            test_path(plot, p, fill)            
        plot.show()   
        
    def testd():   
        plot = Plot()
        d="M1,5 a2,2 0,0,0 2,-3 a3,3 0 0 1 2,3.5"
        dct = {'d':d, 'tag':'path'}    
        e = TagObj('path', dct) 
        p = PathObj(e)            
        plot.path(p.path) 
        plot.show()
    
    def test_file(s):    
        from svgpath import test_svg        
        plot.plt.style.use('seaborn-dark')
        filename = 'svg/%s.svg' %s
        test_svg(filename=filename, img=True) 
    testd()
    test_file('poly')
    if 0:
        for fn in ['path', 'sc', 'poly', 'circle']:
           test_file(fn)
    
    




