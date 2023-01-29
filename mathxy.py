import os
import re
import math    
import numpy as np
import matplotlib as mp
from matplotlib import patches, transforms, bezier
from shapely.geometry import polygon, linestring
from scipy.special import comb
from scipy import ndimage
import plot
from aui import Tlog
       
MOVETO, LINETO, CURVE3, CURVE4, CLOSEPOLY = 1, 2, 3, 4, 79    
   
def get_line(p0, p1, n=None, dtype=float):
    x0, y0 = p0
    x1, y1 = p1     
    if n == None:
        dx = round(x1 - x0)
        dy = round(y1 - y0)
        n = max(abs(dx), abs(dy))+1
    elif n <= 2:
        return [x0, x1], [y0, y1]
    x = np.linspace(x0, x1, n, endpoint=True, dtype=dtype)
    y = np.linspace(y0, y1, n, endpoint=True, dtype=dtype)    
    return x, y    
   
def get_dist(p0, p1):
    x0, y0 = p0
    x1, y1 = p1  
    return np.sqrt((x0-x1)**2 + (y0-y1)**2)
    
def get_dists(verts):
    a = np.array(verts)
    d = np.diff(a, axis=0)
    x, y = np.transpose(d)
    return np.sqrt(x**2 + y**2).round(4)      
    
def get_angles(verts, diff=False):
    va = np.array(verts)
    df = np.diff(va, axis=0)
    dx, dy = np.transpose(df)
    a = np.arctan2(dy, dx) * 180 / np.pi 
    if diff != False:
        a = np.diff(a)
    return a.round(4)
        
def get_dxy_angle(dx, dy):
    a = math.atan2(dy, dx) * 180 / math.pi   
    if dy < 0:
       a += 360
    return a 
        
def get_rotate_matrix(a):
    theta = np.radians(a)
    c, s = np.cos(theta), np.sin(theta)
    R = np.array(((c, -s), (s, c)))
    return R
    
def get_center(verts):
    x, y = np.transpose(np.array(verts)) 
    cx = np.average(x)
    cy = np.average(y)         
    return cx, cy    
    
def curve(a, steps=0.02):
    t_points = np.arange(0, 1+ steps, steps)    
    bz = bezier.BezierSegment(a)   
    verts = bz.point_at_t(t_points)    
    return verts
        
def get_curve(a, c, p0):
    n = a.size
    a = list(a.reshape(n//2, 2))
    a.insert(0, p0)
    verts = curve(np.array(a), steps=0.02)
    return verts      
    
def get_angle(p0, p1):
    x0, y0 = p0
    x1, y1 = p1    
    a = math.atan2(y1-y0, x1-x0) * 180 / math.pi   
    if y1 < y0:
       a += 360
    return a 
    
def flip_vc(verts, codes):
    verts = list(verts)
    codes = list(codes)
    n = len(verts)   
    v = verts.pop(-1)
    verts.reverse()
    codes.reverse()
    for i in range(n):
        c = codes[i]
        if c == 1:
            codes[i] = 79
        elif c == 79:
            codes[i] = 1         
    verts.append(v)   
    codes[0] = 1
    return verts, codes

def interp_xyz(x, y, z, size=(128, 128)):     
    from scipy.interpolate import LinearNDInterpolator   
    w, h = size
    x0, x1 = min(x), max(x)
    y0, y1 = min(y), max(y)
    X = np.linspace(x0, x1, w)
    Y = np.linspace(y0, y1, h)
    X, Y = np.meshgrid(X, Y)  # 2D grid for interpolation    
    verts = list(zip(x, y))    
    interp = LinearNDInterpolator(verts, z, fill_value=0)
    Z = interp(X, Y)
    return Z    
    
def grad_circle(a, data):   
    h, w = a.shape
    cx, cy, r, fx, fy = data
    n = int(w/2)-1
    V = np.linspace(1, 0, n)
    R = np.linspace(w*r, 0, n)
    CX = np.linspace(cx*w, fx*w, n).astype(int)
    CY = np.linspace(cy*h, fy*h, n)    
    for r, v, cx1, cy1 in zip(R, V, CX, CY):
        Y = np.arange(r)
        W = (r * np.cos(np.arcsin(Y/r))).astype(int)                
        for y, w in zip(Y, W):
            x0, x1 = cx1 - w, cx1 + w
            y0, y1 = int(cy1-y), int(cy1+y)            
            a[y0, x0:x1] = v
            a[y1, x0:x1] = v                    
    return a  
    
def get_cos_sin(steps):
    a = np.linspace(0, 360, steps)
    t = np.deg2rad(a)
    cos_t, sin_t = np.cos(t), np.sin(t)   
    return cos_t, sin_t     
    
def circle_xy(cx, cy, r):
    a = np.linspace(0, 360, 36)
    t = np.deg2rad(a)
    x, y = cx + r*np.cos(t), cy + r*np.sin(t)      
    return x, y
    
    
class Plot(plot.Plot):
    pass
    
class tlog(Tlog):
    pass
    
class Bbox(mp.transforms.Bbox):
    pass
    
class Bezier(mp.bezier.BezierSegment):
    pass
    
class Polygon(polygon.Polygon):
    pass
        

class Line(linestring.LineString):
    def get_codes(self, verts):
        if verts == []:
            return []
        return [MOVETO] + [LINETO] * (len(verts) - 1) 
        
    def get_buffer(self, lw, cap=3, join=1):
        p2 = self.buffer(lw, cap_style=cap, join_style=join) 
        return list(p2.exterior.coords)       
            
    def get_side(self, side, lw, cap, join):
        p3 = self.parallel_offset(lw, side=side, join_style=join) 
        if 'multi' in str(type(p3)):
            verts = []
            codes = []
            for p in p3.geoms:
                b = list(p.coords)
                c = self.get_codes(b)
                verts += b
                codes += c
        else:
            verts = list(p3.coords)   
            codes =  self.get_codes(verts)               
        return verts, codes
        
    def get_join(self, join):
        dct = {1:1, 2:2, 3:3, 'r':1, 'm':2, 'b':3, 'round':1, 'miter':2, 
                'bevel':3, 'miter-clip':2, 'arcs':1}
        return dct.get(join, 1)
        
    def get_cap(self, cap):
        dct = {1:1, 2:2, 3:3, 'round':1, 'r':1, 'b':2, 's':3, 'butt':2, 'square':3}
        return dct.get(cap, 2)
                
    def get_outline(self, lw, style=('','',None)):                            
        lw = lw/2
        cap, join, limit = style
        cap = self.get_cap(cap)      
        join = self.get_join(join)
        if not self.is_closed:            
            verts = self.get_buffer(lw, cap, join)
            codes = self.get_codes(verts)
            return verts, codes
        else:
            a, codes0 = self.get_side('right', lw, cap, join)
            b, codes1 = self.get_side('left', lw, cap, join)  
            return a + b, codes0 + codes1    

        
class Transform(transforms.Affine2D): 
    def _get_trans_matrix_(self, name, values):        
        a, b, c, d, e, f = values
        return self.from_values(a, b, c, d, e, f)        
        
    def _get_translate_(self, name, value):  
        #print(name, value)                      
        x, y = 0, 0 
        if name == 'translateX':
            x = value
        elif name == 'translateY':
            y = value
        elif type(value) == tuple:
            x, y = value    
        else:
            x = value
        return self.translate(x, y)
        
    def _get_scale_(self, name, value):                        
        x, y = 1, 1
        if type(value) == tuple:
           x, y = value
        else:
           x, y = value, value
        return self.scale(x, y)
        
    def _get_skew_(self, name, value):                        
        x, y = 0, 0 
        if name == 'skewX':
            x = value
        elif name == 'skewY':
            y = value
        else:
            x, y = value    
        return self.skew_deg(x, y)
        
    def _get_rotate_(self, name, value):  
        if type(value) == tuple:
            a, cx, cy = value
            theta = np.deg2rad(a)
            t = self.rotate_around(cx, cy, theta)
        else:
            a = value
            t = self.rotate_deg(a)        
        return t
        
    def from_text(self, text):                    
        text = text.strip()
        if text == '':
            return None
        trans = transforms.Affine2D()    
        for m in re.finditer('(\w+)\(([^\)]+)\)', text):            
            name = m.group(1)    
            s = m.group(2)
            if ' ' in s and not ',' in s:
                s = s.replace(' ', ',')        
            values = eval(s)             
            if 'skew' in name:
                t = self._get_skew_(name, values)                
            elif 'translate' in name:      
                t = self._get_translate_(name, values)      
            elif 'scale' in name:      
                t = self._get_scale_(name, values)     
            elif 'rotate' in name:      
                t = self._get_rotate_(name, values)           
            elif 'matrix' in name:            
                t = self._get_trans_matrix_(name, values)   
            else:
                print('undefined', name, values)
                continue             
            trans += t
        return trans
        
    def trans_array(self, text, a):
        t = self.from_text(text)
        m = t.get_matrix()
        a = ndimage.affine_transform(a, m)
        return a

class mpPath(mp.path.Path):
    def __init__(self, vertices=[(0,0)], codes=None, **kw):
        s = str(type(vertices)).lower()
        if 'path' in s:
            p = vertices
            mp.path.Path.__init__(self, p.vertices, p.codes, **kw)
        else:
            mp.path.Path.__init__(self, vertices, codes, **kw)
            
    def set_path(self, p):
        self.vertices = p.vertices
        self.codes = p.codes
        
    def from_patch(self, p):
        path = p.get_path().transformed(p.get_transform())                
        return mpPath(path)
        
    def comp_path(self, a, b):
        va = list(a.vertices)
        vb = list(b.vertices)
        vb.reverse()   
        ca = list(a.codes)
        cb = list(b.codes)
        cb.reverse()
        cb[0] = 1
        cb[-1] = 79
        path = mpPath(va + vb, ca + cb)
        return path
        
    def get_verts(self):
        return self.vertices
        
    def get_vc(self):
        return self.vertices, self.codes   
        
    def add_vc(self, v, c):    
        path1 = self.make_compound_path(self, mpPath(v, c))      
        return mpPath(path1)
        
    def get_box(self):
        box = self.get_extents()
        w, h = int(box.width), int(box.height)
        return w, h, (box.x0, box.x1, box.y0, box.y1)
               
    def ellipse(self, oxy, rxy, rotate=0):             
        x, y = oxy
        rx, ry = rxy              
        t = transforms.Affine2D().rotate(rotate).scale(rx, ry).translate(x, y)
        path = self.circle().transformed(t)  
        return mpPath(path)
        
    def ellipse_stroke(self, oxy, rxy, rotate=0, lw=1):
        if lw == 0 or lw == None:
            return 
        lw2 = lw
        lw = lw/2
        rx, ry = rxy
        path0 = mpPath().ellipse(oxy, (rx+lw2, ry+lw2))
        path1 = mpPath().ellipse(oxy, (rx-lw2, ry-lw2))
        verts = list(path1.vertices)
        verts.reverse()
        return path0.add_vc(verts, path1.codes)
        
    def unit_polygon(self, n, x, y, w, h, angle=0):        
        t = transforms.Affine2D().rotate_deg(angle).scale(w, h).translate(x, y)
        path = self.unit_regular_polygon(n).transformed(t)  
        return mpPath(path)
        
    def rect(self, x, y, w, h):
        patch = patches.Rectangle((x, y), w, h)
        path = self.from_patch(patch)
        return path
        
    def rect_stroke(self, x, y, w, h, lw):
        if lw == 0 or lw == None:
            return 
        lw2 = lw
        lw = lw/2
        path0 = mpPath().rect(x-lw, y-lw, w+lw2, h+lw2)
        path1 = mpPath().rect(x+lw, y+lw, w-lw2, h-lw2)
        verts = list(path1.vertices)
        verts.reverse()
        return path0.add_vc(verts, path1.codes)
        
    def round_rect(self, x, y, w, h, r):
        w -= r*2
        h -= r*2
        patch = patches.FancyBboxPatch((x+r, y+r), w, h, boxstyle='round,pad=%d' % r)
        path = self.from_patch(patch)
        return path
        
    def get_arc(self, oxy, rxy, a0=0, a1=360, rotate=0):  
        x, y = oxy
        rx, ry = rxy    
        flip = (a0 > a1)
        if flip:
            a0, a1 = a1, a0
        path = self.arc(a0, a1)    
        t = transforms.Affine2D().scale(rx, ry).rotate_deg(rotate).translate(x, y)
        path = path.transformed(t)        
        if flip:
            v = list(path.vertices)
            v.reverse()
            path.vertices = v
        return mpPath(path)
    
    def get_patch(self, **kw):
        return patches.PathPatch(self, **kw) 
        
    def get_cross(self, path1):
        a = Line(self.vertices)
        b = Line(path1.vertices)
        c = a.intersection(b).geoms
        lst = []
        for p in c:
            lst.append((p.x, p.y))
        return lst
        
    def get_curve(self, a, steps=100):
        t_points = np.arange(0, 1.01, 2/steps)    
        t_points[-1] = 1
        bz = bezier.BezierSegment(a)   
        verts = bz.point_at_t(t_points)                    
        return verts   
        
    def get_pixels(self, steps=None):
        p = self.vertices
        lst = []   
        i = 0
        for a, c in self.iter_segments():
            n = a.size//2            
            if c == 1:
                pass
            elif c == 2:
                x, y = get_line(p[i-1], p[i], steps)
                lst += list(zip(x, y))
            elif c == 3:
                lst += self.get_curve(p[i-1:i+2], steps) 
            elif c == 4:
                lst += self.get_curve(p[i-1:i+3], steps)
            elif c == 79:
                x, y = get_line(p[i-1], p[0], steps)
                lst += list(zip(x, y))
            i += n
            
        verts = []
        for p in lst:
            p = tuple(p)
            if not p in verts:
                verts.append(p)
        return verts
        
    def get_stroke(self, lw, linestyle = ('r', 'm', 1)):    
        if lw == 0 or lw == None:
            return 
        codes = self.codes    
        if not 3 in codes and not 4 in codes:
            verts = self.vertices
            if type(codes) != type(None) and codes[-1] == 79:
                verts[-1] = verts[0]
            v, c = Line(verts).get_outline(lw, linestyle)
            return mpPath(v, c)
        lw = lw/2
        verts = self.vertices    
        verts0 = []
        verts1 = []
        codes1 = []
        i = 0    
        for a, c in self.iter_segments():     
            if c == 1:      
                p0 = verts[i]
                p1 = verts[i+1]
                if np.array_equal(p0, p1):
                    p1 = verts[i+1]
                left, right = LineObj(p0, p1).get_side(lw)
                verts0.append(left[0])
                verts1.append(right[0])
                codes1.append(1)    
                i += 1
            elif c == 2:            
                p0 = verts[i-1]       
                p1 = verts[i]
                left, right = LineObj(p0, p1).get_side(lw) 
                verts0.append(left[1])
                verts1.append(right[1])
                codes1.append(2)
                i += 1                    
            elif c == 3:
                left, right = bezier.get_parallels(verts[i-1:i+2], lw)  
                verts0.extend(left)
                verts1.extend(right)
                codes1 += [4,4,4]
                i += 2
            elif c == 4:  
                left, right = bezier.get_parallels(verts[i:i+3], lw)  
                verts0.extend(left)
                verts1.extend(right)
                codes1 += [4,4,4]
                i += 3
            elif c == 79:
                verts0.append((0, 0))
                verts1.append((0, 0))
                codes1.append(79) 
                i += 1
            else:    
                print(c, i, v)
                i += 1
        v, c = flip_vc(verts1, codes1)
        p1 = mpPath(verts0, codes1)
        p2 = p1.add_vc(v, c)
        return p2
        
    def get_cos_sin(self, cx, cy):
        verts = self.vertices
        x, y = np.transpose(np.array(verts))
        angles = np.arctan2((y-cy), (x-cx)) * 180 / np.pi 
        t = np.deg2rad(angles)    
        return np.cos(t), np.sin(t)
            

#--------------------------------------------------------------------------------------------------           
class Box(object):
    def __init__(self, p0=None, p1=None, rect=None, xy=None):
        if xy is not None:
            self.from_xy(xy)
        elif rect is not None:
            self.left, self.right, self.top, self.bottom = rect
        elif p0 is not None and p1 is not None:
            self.from_p0_p1(p0, p1)           
        else:
            self.left, self.right, self.top, self.bottom = 0, 0, 0, 0 
               
    def __str__(self):
        return str(np.array(self.rect()).astype(int))       
                
    def from_p0_p1(self, p0, p1):
        self.p0, self.p1 = p0, p1
        x0, y0 = p0
        x1, y1 = p1 
        if x0 > x1: 
           self.left, self.right = x1, x0
        else:
           self.left, self.right = x0, x1
        if y0 > y1:
           self.top, self.bottom = y1, y0
        else:
           self.top, self.bottom = y0, y1
           
    def from_xy(self, xy):   
        if type(xy) == tuple:
            x, y = xy
        else:
            x, y = np.transpose(np.array(xy))
        self.left, self.right = np.min(x)-1, np.max(x)+1
        self.top, self.bottom = np.min(y)-1, np.max(y)+1
        
    def get_line(self):
        x0, y0 = self.p0
        x1, y1 = self.p1     
        dx = x1 - x0
        dy = y1 - y0
        n = round(max(abs(dx), abs(dy)))
        x = np.linspace(x0, x1, n, endpoint=True)
        y = np.linspace(y0, y1, n, endpoint=True)
        return x, y
        
    def is_cross(self, box):
        if self.left > box.right or self.right < box.left:
            return False
        if self.top > box.bottom or self.bottom < box.top:
            return False
        return True
        
    def get_cross(self, box):    
        if self.left > box.right or self.right < box.left:
            return None
        if self.top > box.bottom or self.bottom < box.top:
            return None
        left = max(self.left, box.left)-1
        right = min(self.right, box.right)+1
        top = max(self.top, box.top)-1
        bottom = min(self.bottom, box.bottom)+1
        if left > right or top > bottom:
            return None
        return Box(rect=(left, right, top, bottom))
        
    def get_rect(self):
        return self.left, self.right, self.top, self.bottom
        
    def get_size(self):
        return self.right - self.left, self.bottom - self.top
        
    def get_center(self):
        return (self.left+self.right)/2, (self.top + self.bottom)/2
        
    def include_box(self, b1):
        if self.include(b1.left, b1.top) and self.include(b1.right, b1.bottom):
            return True
        return False
        
    def includep(self, p):
        x, y = p
        return (x >= self.left and x <= self.right and y >= self.top and y <= self.bottom)
            
    def include(self, x, y):
        return (x >= self.left and x <= self.right and y >= self.top and y <= self.bottom)
      
    def get_include(self, X, Y):
        lst = []        
        for x, y in zip(X, Y):
            if x >= self.left and x <= self.right and y >= self.top and y <= self.bottom:
                 lst.append((x, y))            
        return lst
          
    def get_includeXY(self, X, Y, return_index=False):
        a = np.logical_and(X >= self.left, X <= self.right)
        b = np.logical_and(Y >= self.top, Y <= self.bottom)
        c = np.logical_and(a, b).nonzero()[0]      
        if return_index == True:
            return c  
        if c.size == 0:
            return np.array([]), np.array([])
        return X[c], Y[c]              

    def np_cross(self):
        x0, y0 = self.p0
        x1, y1 = self.p1     
        return np.cross([x0, y0, 1], [x1, y1, 1])  
        
    def plot(self, ax):
        x = self.left, self.right
        y = self.top, self.bottom
        ax.plot(x, y)    
        
#--------------------------------------------------------------------------------------------------    
class LineObj(object):
    def __init__(self, p0, p1):
        self.p0 = p0
        self.p1 = p1        
                 
    def get_angle(self):        
        x0, y0 = self.p0
        x1, y1 = self.p1
        return get_dxy_angle(x1-x0, y1-y0)       
            
    def rotate(self, a):
        R = get_rotate_matrix(a)
        r0 = np.dot(self.p0, R)  
        r1 = np.dot(self.p1, R)  
        return (r0, r1)
        
    def rotate_to(self, a):
        a0 = self.get_angle()
        return self.rotate(a + a0)       
            
    def get_side(self, w):
        a0 = self.get_angle()
        r0, r1 = self.rotate(a0)
        x0, y = r0
        x1, y2 = r1
        y0, y1 = y-w, y+w
        verts = np.array([[(x0, y0), (x1, y0)], [(x0, y1), (x1, y1)]])
        R = get_rotate_matrix(-a0)
        verts = np.dot(verts, R)
        return verts[0], verts[1]       
        
class Ellipse(object):
    def __init__(self, oxy=(0,0), rxy=(1,1), rotate=0, steps=60):
        self.oxy = oxy  
        self.rxy = rxy        
        self.rotate = rotate
        self.steps = steps
        rx, ry = self.rxy
        ox, oy = self.oxy     
        self.r = max(rx, ry)
        
    def get_dist(self, p):
        return get_dist(self.oxy, p)
        
    def get_angle(self, p):
        ox, oy = self.oxy
        rx, ry = self.rxy  
        t = transforms.Affine2D().translate(-ox, -oy).rotate_deg(-self.rotate).scale(1/rx, 1/ry)
        x, y = t.transform(p)
        a = math.atan2(y, x) * 180 / math.pi   
        if y < 0:
           a = (a + 360) % 360
        return a 
        
    def get_point(self, a):
        ox, oy = self.oxy
        rx, ry = self.rxy        
        t = np.deg2rad(a)
        x, y = np.cos(t), np.sin(t) 
        t = transforms.Affine2D().scale(rx, ry).rotate_deg(self.rotate).translate(ox, oy)
        x, y = t.transform((x, y)) 
        return x, y
       
    def get_edge_point(self, p):
        ox, oy = self.oxy
        rx, ry = self.rxy
        a = self.get_angle(p)
        return self.get_point(a)         
        
    def get_xy(self):   
        rx, ry = self.rxy
        cx, cy = self.oxy
        a = np.linspace(0, 360, self.steps)
        t = np.deg2rad(a)
        x, y = rx*np.cos(t), ry*np.sin(t)      
        if self.rotate == 0:
            self.xy = cx + x, cy + y
        else:
            t1 = np.deg2rad(self.rotate)
            x1 = x * np.cos(t1) - y * np.sin(t1)
            y1 = y * np.cos(t1) + x * np.sin(t1)
            self.xy = cx + x1, cy + y1
        return self.xy
        
    def get_arcXY(self, a0, a1, steps=5):    
        ox, oy = self.oxy
        rx, ry = self.rxy    
        n = int(abs(a1-a0)/steps)
        a = np.linspace(a0, a1, n, endpoint=True)        
        t = np.deg2rad(a) 
        if self.rotate == 0:                        
            x, y = ox+rx*np.cos(t), oy+ry*np.sin(t)
        else:
            x, y = rx*np.cos(t), ry*np.sin(t)
            t1 = np.deg2rad(self.rotate)
            x1 = x * np.cos(t1) - y * np.sin(t1)
            y1 = y * np.cos(t1) + x * np.sin(t1)
            x, y = ox + x1, oy + y1   
        return x, y                 
        
    def plot(self, ax):
        x, y = self.get_xy()
        ax.plot(x, y, alpha=0.5, ls='-.')
        
    def get_edge_dist(self, e1):       
        e0 = self         
        p2 = e0.get_edge_point(e1.oxy)
        p3 = e1.get_edge_point(e0.oxy)
        d1 = self.get_dist(p2)
        d2 = self.get_dist(p3)
        edge_dist = d2 - d1
        return edge_dist       
         
    def get_cross(self, obj):
        a = Line(self.get_verts())
        b = Line(obj.get_verts())
        c = a.intersection(b)
        t = str(type(c)).lower()    
        if 'linestring' in t:
            return list(c.coords)            
        if 'multipoint' in t:
            lst = []
            for p in c.geoms:
                lst.append((p.x, p.y))
            return lst
        return [(c.x, c.y)]
        
    def get_cross_line(self, p0, p1):
        a = Line(self.get_verts())
        b = Line([p0, p1])
        c = a.intersection(b)
        t = str(type(c)).lower()    
        if 'linestring' in t:
            return list(c.coords)            
        if 'multipoint' in t:
            lst = []
            for p in c.geoms:
                lst.append((p.x, p.y))
            return lst
        return [(c.x, c.y)]
        
    def get_arc(self, arc_data):        
        p0, p1, rxy, rotate, large, sweep = arc_data
        self.rotate = rotate
        if rotate == None:
            rotate = 0
        a0 = self.get_angle(p0) 
        a1 = self.get_angle(p1)  
        if sweep:
            step = 1            
        else:
            step = -1       
        arc = np.arange(a0, a1, step)
        n = arc.size
        if n == 0:      
            if step > 0:      
               arc = np.arange(a0, a1 + 359, step)      
               arc[-1] = a1 + 360
            else:
               arc = np.arange(a0 + 360, a1, step)     
               arc[-1] = a1
        else:
            arc[-1] = a1
        return arc
                
    def get_arc_center(self, e1, large):        
        lst = self.get_cross(e1)         
        n = len(lst)
        if n == 0:
            oxy = get_center([self.oxy, e1.oxy])
            return oxy
        if n == 1:
            return lst[0]
        a, b = lst[0], lst[1]               
        self.oxy = a
        e1.oxy = b
        arc0 = self.get_arc(self.arc_data)
        arc1 = e1.get_arc(self.arc_data)          
        n0, n1 = arc0.size, arc1.size
        if (large and n0 > n1) or (large==False and n0 < n1):    
           return a
        else:
           return b
           
    def get_oxy(self, arc_data):
        self.arc_data = arc_data
        p0, p1, rxy, rotate, large, sweep = arc_data
        self.__init__(p0, rxy, rotate=rotate)
        e1 = Ellipse(p1, rxy, rotate=rotate)
        self.oxy = self.get_arc_center(e1, large)  
        return self.oxy
                
    def get_arc_path(self, arc_data):   
        self.get_oxy(arc_data)
        arc = self.get_arc(arc_data)        
        a0, a1 = arc[0], arc[-1]         
        path = mpPath().get_arc(self.oxy, self.rxy, a0, a1, self.rotate)  
        return path
        
    def get_verts(self):
        x, y = self.get_xy()
        verts = list(zip(x, y))
        verts.append(verts[0])
        return verts              
        
    def get_vc(self):
        p = mpPath().ellipse(self.oxy, self.rxy, self.rotate)        
        return p.vertices, p.codes 
        
    def get_patch(self, **kw):
        verts = self.get_verts()
        path = mpPath(verts)
        patch = patches.PathPatch(path, **kw)
        return patch    
        
    def contains_points(self, points):
        n = 0
        for p in points: 
            if self.get_dist(p) < self.r:
                n += 1
        return n
        
    def get_stroke(self, lw): 
        p = mpPath().ellipse(self.oxy, self.rxy, self.rotate) 
        return p.get_stroke(lw)
        
    def fill2img(self, a, v=1):   
        rx, ry = self.rxy
        cx, cy = self.oxy
        w, h = rx*2, ry*2
        Y = np.arange(ry)
        W = (ry * np.cos(np.arcsin(Y/ry))).astype(int)        
        for y, w in zip(Y, W):        
            x0, x1 = int(cx-w), int(cx+w)
            y0, y1 = int(cy-y), int(cy+y)     
            a[y0, x0:x1] = v
            a[y1, x0:x1] = v 
        return a  
        
class PolyObj(object):
    def __init__(self, verts=[]):     
        self.box = None 
        self.path = None
        self.verts = verts        
        if verts == []:
            self.xy = [], []
            return
        else:
            self.verts = verts      
        x, y = np.transpose(np.array(self.verts))
        self.xy = x, y
        
    def from_patch(self, patch):
        self.patch = patch
        self.path = patch.get_path().transformed(patch.get_transform())  
        self.from_path(self.path)        
        return self
                
    def get_curve(self, a):
        t_points = np.arange(0, 1.01, 0.02)    
        t_points[-1] = 1
        bz = bezier.BezierSegment(a)   
        verts = bz.point_at_t(t_points)                    
        return verts   
        
    def iter_path(self, path):
        p = path.vertices
        verts = []   
        i = 0
        v0 = []
        for a, c in path.iter_segments():
            if c == 1:
                v0 = a
                verts.append(a)
            elif c == 2:
                verts.append(a)
            elif c == 3:
                verts += self.get_curve(p[i-1:i+2])    
            elif c == 4:
                verts += self.get_curve(p[i-1:i+3])
            elif c == 79:
                verts += v0
            i += int(a.size/2)
        return verts
        
    def from_path(self, path):
        self.path = path        
        self.verts = self.iter_path(path)
        return self     
        
    def get_size(self):
        path = mpPath(self.verts)
        box = path.get_extents()
        return box.width, box.height       

        
    def get_verts(self, wrap=False):
        return self.verts
        
    def get_segments(self, wrap=False):                    
        lst = []
        verts = self.verts
        for p0, p1 in zip(verts, verts[1:]):       
            lst.append((p0, p1))     
        if wrap:
            lst.append((verts[-1], verts[0]))   
        return lst 
        
    def get_xylst(self, wrap=False):
        lst = []
        verts = self.verts
        for p0, p1 in zip(verts, verts[1:]):
            lst.append(Box(p0, p1))
        if wrap == True:
           lst.append(Box(verts[-1], verts[0]))
        return lst
       
    def get_outline(self, lw, style=('','',None)):          
        verts = list(self.verts)
        if len(verts) < 2:
            return [(0, 0)], [MOVETO]  
                
        p = Line(verts)
        v, c = p.get_outline(lw, style)  
        return v, c 
            
    def get_path(self, verts=None):
        if verts == None:
            verts = self.verts
        n = len(verts)
        codes = [MOVETO] + [LINETO] * (n - 1) 
        return mpPath(verts, codes)
        
    def get_vc(self):
        n = len(self.verts)
        self.codes = [MOVETO] + [LINETO] * (n - 1) 
        return self.verts, self.codes
             
    def clip_with(self, poly):        
        p1 = polygon.Polygon(self.verts)
        p2 = polygon.Polygon(poly.verts)
        a = p1.intersection(p2)
        verts = list(a.exterior.coords)
        return verts
        
    def _zoom_(self, ratio):
        v0 = self.get_center()     
        x, y = v0   
        t = transforms.Affine2D().translate(-x, -y).scale(ratio).translate(x, y)   
        verts_zoom = t.transform(self.verts) 
        return verts_zoom
        
    def get_zoom_outline(self, lw):
        w, h = self.get_size() 
        verts0 = list(self._zoom_((w-lw)/w))
        verts1 = list(self._zoom_((w+lw)/w))   
        path = mpPath(verts0+verts1)
        return path.vertices, path.codes
        
        
def get_tagobj(dct):
    from tagobj import TagObj
    obj = TagObj(tag=dct['tag'], content=dct)
    obj.init_path()
    return obj

def new_plot():
    p = Plot(1)    
    return p, p.ax
    

    
if __name__ == '__main__':        
    from pathobj import PathObj
    from tagobj import TagObj
    d="M230 80   A 45 45, 0, 1, 0, 275 125  L 275 80 Z", 'red'
    d="M1,5 a2,2 0,0,0 2,-3 a3,3 0 0 1 2,3.5", 'blue'
    def test(lst):
        plot = Plot()
        ax = plot.ax
        for d, fill in lst:
            dct = dict(tag='path', d=d)
            e = TagObj(tag=dct['tag'], content=dct) 
            p = PathObj(e)      
            patch = p.get_patch(fc=fill)
            ax.add_patch(patch)           
        plot.show()
        
    def test1():
        plot = Plot()
        data = .5, .5, .4, .75, .75
        cx, cy, r, fx, fy = data
        n = 50
        w, h = n*2, n*2  
        path = mpPath().round_rect(0, 0, w, h, 20)
        verts = path.get_pixels(10)
        plot.verts(verts)
        plot.show()

    if 0:     
       test([d])
    elif 1:
       from svgpath import test_svg
       #plt.style.use('dark_background')
       test_svg(filename='sc')
    else:
       test1()

