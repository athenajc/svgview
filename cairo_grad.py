import numpy as np
import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk
import cairo
import math
from mathxy import *      
from object import Object
from aui import ImageObj, tkwin
import tkinter as tk

class CairoSurface():       
    def __init__(self, size):
        w, h = size    
        if w % 8 != 0:
            w += 8 - (w%8)
            size = w, h
        self.size = size
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)    
        self.context = cairo.Context(self.surface)          
        
    def get_image(self):        
        w, h = self.size
        surface = self.surface
        if 0: 
            imgobj = ImageObj.from_surface(surface)
        else:
            pb = Gdk.pixbuf_get_from_surface(surface, 0, 0, w, h)
            imgobj = ImageObj.from_pixbuf(pb)
        return imgobj  
 
        
class CairoGradient():       
    def __init__(self, size):
        w, h = size    
        if w % 8 != 0:
            w += 8 - (w%8)
            size = w, h
        self.size = size
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)    
        self.context = cairo.Context(self.surface)          
        
    def get_image(self):        
        w, h = self.size
        surface = self.surface
        if 0: 
            imgobj = ImageObj.from_surface(surface)
        else:
            pb = Gdk.pixbuf_get_from_surface(surface, 0, 0, w, h)
            imgobj = ImageObj.from_pixbuf(pb)
        return imgobj  
 
    def get_colors(self, stops):
        self.colors = [] 
        self.offsets = []
        for p in stops:
            offset, rgba = p
            r, g, b, a = rgba            
            self.offsets.append(offset)
            self.colors.append((r, g, b, a))     
        
    def set_grad_stops(self, grad):
        for offset, rgba in zip(self.offsets, self.colors): 
            r, g, b, a = rgba
            grad.add_color_stop_rgba(offset, r, g, b, a)
            
    def add_grad_stops(self, grad, v0, v1, n, spread):
        dv = (v1 - v0)/n
        i = v0
        offsets = self.offsets.copy()
        colors = self.colors.copy()
        while i < 1:            
            for offset, rgba in zip(offsets, colors): 
                r, g, b, a = rgba
                grad.add_color_stop_rgba(i + offset/n, r, g, b, a)
            if spread == 'reflect':
                colors.reverse()
            i += dv
            
    def get_rgrad(self, data, size):
        w, h = size
        cx, cy, r, fx, fy = data
        grad = cairo.RadialGradient(fx*w, fy*h, 0, cx*w, cy*h, r*w)   
        self.set_grad_stops(grad)
        return grad                        
    
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
                
    def get_rgrad_pad(self, data, size, spread):
        w, h = size
        cx, cy, cr, fx, fy = data
        cx, cy, cr, fx, fy = cx*w, cy*h, cr*w, fx*w, fy*h   
        dx, dy, dr, n = self.get_dxyr((cx, cy, cr, fx, fy), size)    
        grad1 = cairo.RadialGradient(fx, fy, 0, cx, cy, cr)       
        self.set_grad_stops(grad1)                    
        grad = cairo.RadialGradient(cx, cy, cr, cx+dx*n, cy+dy*n, cr+dr*n)    
        if spread == 'reflect':   
           self.colors.reverse()
        self.add_grad_stops(grad, 0, 1, n, spread)               
        return grad1, grad 
        
    def rgrad(self, data, stops, spread):
        size = self.size
        w, h = size
        cx, cy, r, fx, fy = data
        self.get_colors(stops)        
        cxt = self.context     
        if spread != 'pad':
            grad1, grad = self.get_rgrad_pad(data, size, spread) 
        else:
            grad = self.get_rgrad(data, size)   
            grad1 = None
        cxt.set_source(grad)
        cxt.rectangle(0, 0, w, h)
        cxt.fill()             
        if grad1 != None:
            cxt.set_source(grad1)
            cxt.arc(cx*w, cy*h, r*w, 0, 2*math.pi)
            cxt.fill() 
        return self.get_image()    
            
    def get_lgrad(self, data, size): 
        #print('get_lgrad', size, data)       
        x1, x2, y1, y2 = data
        if x1 == None:
            x1, x2, y1, y2 = 0, 1, 0, 0
            data = x1, x2, y1, y2
        if max(data) <= 1:
            w, h = size
            x1, y1, x2, y2 = x1*w, y1*h, x2*w, y2*h
        grad = cairo.LinearGradient(x1, y1, x2, y2)   
        self.set_grad_stops(grad)
        return grad 
        
    def get_lgrad_pad(self, data, size, spread):
        w, h = size        
        n = 1/np.ptp(data)   
        data = np.array(data)
        for i in range(4):
            v = data[i]
            if v > 0 and v < 1:
                data[i] = 1
        x1, x2, y1, y2 = data  
        grad = cairo.LinearGradient(x1*w, y1*h, x2*w, y2*h)             
        self.add_grad_stops(grad, 0, 1, n, spread)
        return grad  
        
    def lgrad(self, data, stops, spread):        
        size = self.size
        w, h = size       
        x1, x2, y1, y2 = data        
        stops = self.get_colors(stops)        
        cxt = self.context  
        if spread != 'pad':
            grad = self.get_lgrad_pad(data, size, spread)            
        else:
            grad = self.get_lgrad(data, size)   
        cxt.set_source(grad)
        cxt.rectangle(0, 0, w, h)
        cxt.fill()                     
        return self.get_image()
        
if __name__ == '__main__':    
    def test_lgrad(win):
        data = 0, 0, 0, .3
        stops = [(0, (0, 0.6, 0.9, 1)), (1, (1, 1, 1, 0))]
        t = tlog()
        img0 = CairoGradient((256, 256)).lgrad(data, stops, spread='pad')
        img1 = CairoGradient((256, 256)).lgrad(data, stops, spread='reflect')
        img2 = CairoGradient((256, 256)).lgrad(data, stops, spread='repeat')     
        t.puts()        
        win.add_images([img0, img1, img2])
        
    def test_rgrad(win):
        #data = .5, .5, .4, .75, .75
        data = 0.5, 0.5, 0.45, 0.2, 0.2
        #data = 0.5, 0.5, 0.3, 0.35, 0.35          
        stops = [(0, (1, 1, 0, 1)), (1, (1, 0, 0, 1))]
        t = tlog()
        img0 = CairoGradient((256, 256)).rgrad(data, stops, spread='pad')
        img1 = CairoGradient((256, 256)).rgrad(data, stops, spread='reflect')
        img2 = CairoGradient((256, 256)).rgrad(data, stops, spread='repeat')     
        t.puts()        
        win.add_images([img0, img1, img2])
        
    def test1(item):
        win = tkwin()    
  
        test_lgrad(win)    
        test_rgrad(win)
        win.show()

    test1('1')
    
