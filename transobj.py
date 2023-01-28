import re
import numpy as np
from scipy import ndimage
import math
from object import Object
from mathxy import Transform

class Matrix():
   def set_matrix(self, mat):          
       self.matrix = mat
       if type(mat) == tuple:
           a, b, c, d, e, f = mat
       else:
           a, b, c, d, e, f = mat.flatten()[0:6]
       delta = a * d - b * c    
       self.translate = [e, f]
       self.rotate = 0
       self.scale = [0, 0]
       self.skew = [0, 0] 
       # Apply the QR-like decomposition.
       if (a != 0 or b != 0):
           r = math.sqrt(a * a + b * b)
           if b > 0:
               self.rotate = math.acos(a / r) 
           else:
               self.rotate = -math.acos(a / r)
           self.scale = [r, delta / r]
           self.skew = [math.atan((a * c + b * d) / (r * r)), 0]
       elif (c != 0 or d != 0):
           s = math.sqrt(c * c + d * d)
           if d > 0:
               self.rotate = math.PI / 2 - math.acos(-c / s) 
           else:
               self.rotate = math.PI / 2 - math.acos(c / s)
           self.scale = [delta / s, s]
           self.skew = [0, math.atan((a * c + b * d) / (s * s))]   

    
class TransObj(Object, Matrix):
    def __init__(self, text=''):        
        self.items = [] 
        self.trans = None
        self.scale = None
        self.text = text
        if text != '' and text != None:
            self.from_text(text)
        else:
            self.text = ''
                
    def _get_rotate_(self, name, value):  
        if type(value) == tuple:
            a, cx, cy = value
            theta = np.deg2rad(a)
            return 'rotate_around', (cx, cy, theta)            
        else:
            a = value
            theta = np.deg2rad(a)
            return 'rotate', theta            
        
    def from_text(self, text):                           
        text = text.strip()
        if text == '':
            return self.items     
        
        for m in re.finditer('(\w+)\(([^\)]+)\)', text):            
            name = m.group(1)            
            values = self.get_value(m.group(2))  
            s1 = name[-1]
            if s1 == 'X':
                values = (values, 0)
                name = name[:-1]
            elif s1 == 'Y':
                values = (0, values)
                name = name[:-1]
            if 'skew' in name:
                n, v = 'skew_deg', values
            elif name == 'matrix':
                n, v = 'from_values', values
            elif 'rotate' in name:      
                n, v = self._get_rotate_(name, values) 
            else:
                n, v = name, values
            self.items.insert(0, (n, v))
            
        s = 'Transform()'    
        for n, v in self.items:
            s1 = str(v)
            if not '(' in s1:
                s1 = '(%s)' % s1     
            s += '.' + n + s1
        self.trans = eval(s)     
        
    def add_trans(self, trans):
        if trans == None:
            return 
        if self.trans == None:
            self.trans = trans
        else:
            self.trans = trans + self.trans
        
    def get_trans(self):        
        return self.trans 
        
    def get_rotate(self):        
        if self.trans == None:
            return 0
        self.set_matrix(self.trans.get_matrix())
        return self.rotate        
        
    def get_skew(self):
        for name, value in self.items:
            if 'skew' in name:    
                x, y = value
                return x, y
        return 0, 0 
                
    def get_fill_trans(self):        
        if self.trans == None:
            return 'none'     
        m = self.trans.get_matrix()  
        m[0, 2] = 0
        m[1, 2] = 0
        self.set_matrix(m)
        return self
        
    def get_matrix(self):
        if self.trans == None:
            return 'none'
        return self.trans.get_matrix()
        
    def trans_array(self, a, t1=None):
        if len(self.items) == 1 and self.text[0] == 't':
            return a        
        if self.trans == None:
            return a     
        m = self.trans.get_matrix()               
        if len(a.shape) == 3:
            for i in range(a.shape[2]):
                a[:,:,i] = ndimage.affine_transform(a[:,:,i], m, mode='nearest')
        else:
            a = ndimage.affine_transform(a, m, mode='nearest')
        return a        

if __name__ == '__main__':         
    from svgpath import test_svg
    def test(i):
        lst = ['gradtrans', 'stroke_grad', 'g_trans', 'g_trans1',  'g_trans2']    
        lstl = ['g_spread', 'anki', 'stroke_grad', '3depict', 'gradient', 'anjuta']
        lstg = ['g_trans', 'g_trans1',  'g_trans2', 'grad2', 'grad3', 'grad4']
        lst1 = ['g_trans1']
        
        dct = {'t':lst, 'L':lstl, '1':lst1, 'G':lstg, 'a':lst+lstl+lstg}
        for fn in dct.get(i, []):        
            test_svg(filename='svg/%s.svg'%fn, img=True) 
    test('1') 
        



