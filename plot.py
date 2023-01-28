import os
import numpy as np
import matplotlib as mp
import matplotlib.pyplot as plt 
from matplotlib import patches, transforms, bezier

import ui
           
class Plot(object):
    def __init__(self, yaxis=1, size=(6.4, 6.4)):
        mp.use('TkAgg')
        fig, ax = plt.subplots(figsize=size)
        w, h = size
        fig.patch.set_visible(False)  
        self.dpi = fig.dpi  
        self.size = size
        self.yaxis = yaxis        
        if self.yaxis == 1:            
            ax.invert_yaxis()     
        ax.set_aspect('equal')  
        ax.grid()
        ax.set_axisbelow(True)
        self.plt = plt
        self.fig = fig
        self.ax = ax
        self.arrays = None
        ax.get_grad = self.get_grad
        
    def init_arrays(self):
        self.arrays = {}
        d = 1
        x = np.linspace(-d, d, 256)
        y = np.linspace(-d, d, 256)
        x, y = np.meshgrid(x, y)    
        self.arrays['r'] = np.sqrt(x**2+y**2)
        gx = np.linspace(0, 1, 256)
        self.arrays['l'] = np.tile(gx, [256,1])
        
    def get_grad(self, mode):
        if self.arrays == None:
            self.init_arrays()
        return self.arrays.get(mode[0].lower())
        
    def hide_grid(self):
        ax = self.ax
        ax.axis('off')  
        ax.grid('off')
        ax.axes.set_aspect('equal')
        self.fig.patch.set_visible(False)        
        
    def show(self, ax=None):
        if ax == None:
           ax = self.ax
        if self.yaxis == 1 and ax.yaxis_inverted() == False:
           ax.invert_yaxis()
        ax.plot()    
        plt.show() 
        
    def show_image(self, filename):    
        filename = os.path.realpath(filename)    
        img = ui.ImageObj(filename)
        w, h = img.size
        m = max(w, h)
        w, h = int(w * 300/m), int(h * 300/m)
        img = ui.ImageObj(filename, size=(w, h))    
        img = img.get_array()
        self.fig.set_figwidth(10)        
        dpi = self.fig.dpi
        self.fig.figimage(img, xo=5, yo=50)
        self.ax.set_position((0.3, 0, 0.68, 1))
        
    def draw_bkg(self, box):  
        self.ax.axis('off')
        self.ax.grid('off')
        w1 = box.width/20
        h1 = box.height/20             
        w, h = int(w1*2)+1, int(h1*2)+1 
        a = np.full((20, 20), 0.95)
        a[10:,0:10] = 0.75
        a[0:10, 10:] = 0.75  
        b = np.tile(a, (h, w)) 
        x0, x1, y0, y1 = box.x0, box.x1, box.y0, box.y1
        box1 = x0-w1, x1+w1, y0-h1, y1+h1        
        self.ax.imshow(b, cmap='gray', vmin=0, vmax=1, extent=box1, zorder=-1) 
            
    def patch_to_rgba(self, patch, **kw):
        fig = self.fig
        self.ax.set_visible(False)
        fig_canvas = fig.canvas
        figure_canvas = FigureCanvasAgg(fig)
        fig.patch.set_visible(False)
        ax = fig.add_subplot(121)
        ax.axis('off')    
        ax.set_aspect('equal')  
        ax.add_patch(patch, **kw)    
        ax.plot()
        canvas = fig.canvas    
        canvas.draw()
        rgba = np.asarray(canvas.buffer_rgba())
        fig.delaxes(ax)
        fig.canvas = fig_canvas
        self.ax.set_visible(True)
        return rgba       
    
    def scatter(self, p, *data):   
        x, y = p
        self.ax.scatter(x, y)
        text = ''
        for s in data:            
            text += str(s) + '  '   
        if text == '':
            text = str((round(x), round(y)))
        self.ax.annotate(text, xy=(x, y),  xycoords='data',  xytext=(x, y))
        
    def line(self, p0, p1, text=False, **kwargs):
        ax = self.ax
        ax.axline(p0, p1, **kwargs)
        if text == True:
           self.scatter(p0, 'p0', strp(p0))
           self.scatter(p1, 'p1', strp(p1))  
        else:
           self.scatter(p0, '')
           self.scatter(p1, '')    
        
    def rect(self, w, h):    
        x = [0, w, w, 0, 0]
        y = [0, 0, h, h, 0]
        self.ax.plot(x, y)    
        
    def get_cmap(self, name, colors=None):
        if colors == None:
            return plt.get_cmap(name)
        cmap = mp.colors.LinearSegmentedColormap.from_list(name, colors)     
        return cmap
          
    def get_transed_path(self, path):
        return transforms.TransformedPath(path, self.ax.transData)  
        
    def verts(self, verts, **kw):
        x, y = np.transpose(np.array(verts))
        self.ax.plot(x, y, **kw)  
        
    def path(self, path, **kw):     
        patch = patches.PathPatch(path, **kw) 
        self.ax.add_patch(patch)  
        
    def points(self, verts, index=False):
        if index == True:
            for i, p in enumerate(verts):
                self.scatter(p, i)        
        else:
            for p in verts:
                self.scatter(p)     
                
    def add_plot(self, n, i):
        self.hide_grid()
        ax1 = self.fig.add_subplot(1, n, i)
        return ax1
        
    def images(self, images):
        #self.hide_grid()
        n = len(images)
        i = 0
        for img in images:
            self.fig.add_subplot(1, n, i+1)
            plt.imshow(img)   
            i += 1
    
    def plot(self, x, y, **kw):       
        self.ax.plot(x, y, **kw)  
            

def get_style():
    style = ['Solarize_Light2', '_classic_test_patch', 'bmh', 'classic', 'dark_background', 'fast', 'fivethirtyeight', 'ggplot', 'grayscale', 'seaborn', 'seaborn-bright', 'seaborn-colorblind', 'seaborn-dark', 'seaborn-dark-palette', 'seaborn-darkgrid', 'seaborn-deep', 'seaborn-muted', 'seaborn-notebook', 'seaborn-paper', 'seaborn-pastel', 'seaborn-poster', 'seaborn-talk', 'seaborn-ticks', 'seaborn-white', 'seaborn-whitegrid', 'tableau-colorblind10']
    return style
    
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
            patch = p.path.get_patch(fc=fill)
            ax.add_patch(patch)           
        plot.show()
    if 1:     
       test([d])
    else:
       from svgpath import test_svg
       #plt.style.use('dark_background')
       test_svg(filename='sc')

