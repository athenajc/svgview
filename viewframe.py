import tkinter as tk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import gi
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf
from treeview import TestFrame
from svgpath import SvgPath
from aui import TwoFrame, ImageObj
from fileio import fread
     
class ViewFrame(tk.Canvas):
    def __init__(self, master, **kw):
        tk.Canvas.__init__(self, master, **kw) 
        self.draw_bkg1(800, 800)
        self.init_fig()
        
    def draw_bkg(self, box):
        pass
            
    def draw_bkg1(self, w, h):       
        a = np.full((20, 20), 0.75, dtype=float)
        a[10:,0:10] = 0.7
        a[0:10, 10:] = 0.7  
        b = np.tile(a, (h//20, w//20)) 
        bkg = ImageObj(size=(w, h))
        img = bkg.array2image(b)
        bkg.set_image(img)
        self.bkg = bkg
        self.tkimage1 = bkg.get_tkimage()
        self.create_image(0, 0, image=self.tkimage1, anchor='nw', tag='tkimage1') 
        
    def load_preview(self, filename, size=None):
        self.delete('tkimage')
        if filename == None:
            return
        imageobj = ImageObj(filename=filename) 
        w, h = imageobj.size
        s = max(w, h)
        if s < 200:
           m = int(200 / s)
           w, h = w * m, h * m
           imageobj = ImageObj(filename, size=(w, h)) 
           
        self.tkimage = imageobj.get_tkimage()
        self.create_image(850, 100, image=self.tkimage, anchor='nw', tag='tkimage')          
        
    def init_fig(self):
        self.delete('figure')
        fig = plt.figure(figsize=(7, 5), dpi=100)                  
        ax = fig.add_axes((0.05, 0.05, 0.9, 0.9))
        ax.axis('off')  
        ax.axes.set_aspect('equal')
        fig.patch.set_visible(False)
        figure_canvas = FigureCanvasTkAgg(fig, self)
        tkphoto = figure_canvas._tkphoto     
        self.create_image(0, 0, image=tkphoto, anchor='nw', tag='figure')                      
        ax.plot()
        figure_canvas.draw()
        self.ax = ax
        self.fig = fig
        
    def set_text(self, text):     
        ax = self.ax
        ax.clear()  
        ax.axis('off')  
        ax.axes.set_aspect('equal')                 
        svg = SvgPath(self, text=text)
        w, h = svg.w, svg.h
        ax.plot()           
        if ax.yaxis_inverted() == False:
           ax.invert_yaxis()
        self.fig.canvas.draw()     
        
class TestFrame1(tk.Frame):
    def __init__(self, master, select_act=None):       
        tk.Frame.__init__(self, master)        
        frame = TwoFrame(self, sep = 0.3, type='h')
        frame.pack(fill='both', expand=True)
        frame1 = TestFrame(frame.left, self.test_svg)
        frame1.pack(fill='both', expand=True)    
        frame1.set_path('/home/athena/src/images/svg/')
        self.svgview = ViewFrame(frame.right)
        self.svgview.pack(fill='both', expand=True)
        
    def test_svg(self, filename=None):
        print('test_svg', filename)
        text = fread(filename)        
        if text != None:
           text = text.strip() 
           if text[0] != '<':
              return        
        if filename != None:
            self.svgview.load_preview(filename) 
        self.svgview.set_text(text)
        
if __name__ == '__main__':             
    def main():
        root = tk.Tk()
        root.title('SVG Viewer')
        root.geometry('1700x900') 
        frame = TestFrame1(root)
        frame.pack(fill='both', expand=True)
        root.mainloop()  
    
    main()





