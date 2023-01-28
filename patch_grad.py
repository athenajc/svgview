import numpy as np
from mathxy import *      
from matplotlib.collections import PatchCollection
import matplotlib.patches

plot, ax = new_plot()           
cmap = plot.get_cmap('t', [(0, "#f00"), (1, '#ff0')]) 
sqrt2 = np.hypot

class PatchGrad(object):
    def __init__(self, ax, path, data, cmap, spread='pad'):  
        self.ax = ax
        self.path = path
        self.data01 = data
        box = path.get_extents()
        self.bbox = box
        w, h = box.width, box.height
        cx, cy, r, fx, fy = data        
        x0, y0 = box.x0, box.y0
        self.data = x0+cx*w, y0+cy*h, r*(w+h)/2, x0+fx*w, y0+fy*h
        self.size = w, h
        self.cmap = cmap  
        self.spread = spread
        
        self.clst = []
        self.plst = []
        if spread == 'pad':
            self.pad_grad()
        else:
            self.patch_grad()
        self.set_collection()
                
    def set_collection(self):
        clst = self.get_colors(self.clst)  
        self.patch = PatchCollection(self.plst, ec='none', fc=clst)
        self.set_clip_path(self.path)
        self.ax.add_collection(self.patch)          
        
    def set_clip_path(self, path):
        clip = path.get_patch(fc='none', ec='none', lw=0)
        self.ax.add_patch(clip)
        self.patch.set_clip_path(clip)
        
    def set_extents(self, box):
        x0, x1, y0, y1 = box.x0, box.x1, box.y0, box.y1
        w, h = box.width, box.height
        t = Transform().scale(w, h).translate(x0, y0)
        self.trans = t
        self.patch.set_transform(t + self.ax.transData)
        
    def get_dxyr(self):
        w, h = self.size
        cx, cy, r, fx, fy = self.data
        e = Ellipse((cx, cy), (r, r))
        a = e.get_angle((fx, fy))
        x1, y1 = e.get_point(a)
        dx1, dy1 = x1-fx, y1-fy 
        d1 = np.hypot(dx1, dy1)        
        d2 = np.hypot(w, h) 
        d3 = d2/2-r
        n = int(d3 / d1)
        dr = r*0.75
        t = np.deg2rad(a) 
        dx = -(dr*math.cos(t) - dx1)
        dy = -(dr*math.sin(t) - dy1)
        return dx, dy, dr, n+1
        
    def get_colors(self, lst):
        lst1 = []
        for c in lst:
            lst1.append(self.cmap(c))
        return lst1
        
    def add_path(self, p, cv):
        p = p.clip_to_bbox(self.bbox)    
        self.plst.append(p.get_patch())
        self.clst.append(cv)
               
    def circle_range(self, c0, c1, lw=2):
        box = self.bbox
        if c0[3] > c1[3]:
            c0, c1 = c1, c0
        cx0, cy0, r0, v0 = c0
        cx1, cy1, r1, v1 = c1    
        n = int(abs(r0-r1)/lw) 
        a = np.transpose(np.array([c0, c1]))
        dx, dy, dr, dv = np.diff(a)/n
        cx, cy, cr, cv = c0
        box_points = box.get_points()
        for i in range(n):        
            e = Ellipse((cx, cy), (cr, cr))
            out = e.contains_points(box_points)
            if out == 2:
                return True
            e = e.get_stroke(lw+2)        
            self.add_path(e, cv)
            cx, cy, cr, cv = cx+dx, cy+dy, cr+dr, cv+dv    
        return False        
    
    def pad_grad(self):
        cx, cy, r, fx, fy = self.data
        w, h = self.size
        x0, y0 = self.bbox.x0, self.bbox.y0
        rect = mpPath().rect(x0, y0, w, h)
        self.add_path(rect, 255)
        lw = (w+h)/100
        if lw > 1:
            lw = 1
        self.circle_range((fx, fy, 0, 0), (cx, cy, r+2, 1), lw)   
           
    def patch_grad(self):   
        cx, cy, r, fx, fy = self.data
        w, h = self.size
        self.circle_range((fx, fy, 0, 0), (cx, cy, r+2, 1), 1)  
        v0, v1 = 0, 1    
        cx0, cy0, cr0 = cx, cy, r   
        dx, dy, dr, n = self.get_dxyr()  
        lw = (w+h)/100
        if lw > 2:
            lw = 2
        for i in range(n):      
            if self.spread == 'reflect':
                v0, v1 = v1, v0
            cx1, cy1, cr1 = cx0+dx, cy0+dy, cr0+dr   
            over = self.circle_range((cx0, cy0, cr0, v0), (cx1, cy1, cr1, v1), lw)
            if over == True:
                break
            cx0, cy0, cr0 = cx1, cy1, cr1    

if __name__ == '__main__':       
    
    def get_path():
        d="M1,5 a2,2 0,0,0 2,-3 a3,3 0 0 1 2,3.5"
        dct = {'d':d, 'tag':'path'}    
        e = get_tagobj(dct)           
        return e.path
        
    def test_grad():       
        #data = .5, .5, .4, .75, .75
        data = 0.5, 0.5, 0.45, 0.2, 0.2
        #data = 0.5, 0.5, 0.3, 0.35, 0.35        
    
        t = tlog()
        cmap = plot.get_cmap('t', [(0, "#f00"), (1, '#ff0')]) 
        
        path1 = mpPath().ellipse((35, 35), (100, 100))
        path2 = get_path()
        t.log()
        gobj = PatchGrad(ax, path1, data, cmap, spread='repeat')
        t.log()
        plot.show()    
        t.puts()
           
            
    test_grad()




