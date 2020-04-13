import Tkinter as tk
import tkFont
import tkMessageBox as tkMsgBox
import numpy as np
from matplotlib import pyplot as plt

class DataCanvas(tk.Canvas):
    " Canvas staging elements of a time sequence. Supports scrolling by dragging,\
    zooming by use of the mouse wheel, element highlighting and tooltips."
    
    __default = {\
               'background':CHANNELFRAME_BG_COLOR,\
               'highlightthickness':0,\
               'xscrollincrement':1,\
               'stepsperpixel':CHANNELFRAME_STEPSPERPIXEL,\
               'origin':1.0,\
               'scalefactor':1.0,\
               'padleft':0.0,\
               'padright':0.0,\
               'linewidth':1,\
               'closeenough':2.0,\
               'ttfontsize':8,\
               '_allow_dynamic_view':True,\
               '_enable_scrolling':True,\
               '_enable_zooming':True,\
               '_enable_tooltips':True,\
               'time':None,\
               'root':None,\
               'frame':None\
               }  
    
    def __init__(self,master,**kwargs):
        " Create instance of TimeCanvas inside master. Argument 'root' refers to the \
        root application that this TimeCanvas will be part of. Not assigning 'root' may \
        limit functionality. "
        # initialize a generic canvas and link parent
        tk.Canvas.__init__(self,master)
        # get valid configuration keywords for the tk.Frame
        config_kws = self.config()
        # separate tk.Frame configuration kwargs from others
        addtl_kwargs = {}
        for kw in self.__default:
            if kw not in kwargs:
                kwargs[kw] = self.__default[kw]
        for kw in kwargs:
            if kw not in config_kws:
                addtl_kwargs[kw] = kwargs[kw]
        for kw in addtl_kwargs: kwargs.pop(kw)
        # configure canvas object
        self.config(kwargs)
        # set other attributes
        for kw in addtl_kwargs:
            setattr(self,kw,addtl_kwargs[kw])
        # register with PetsFrame if one was given
        if self.frame != None:
            assert isinstance(self.frame,PetsFrame),\
                   "'.frame' has to be instance of PetsFrame!"
            self.frame.register_widget(self)
        # know your size
        self.size = (int(self['height']),int(self['width']))
        # initialize some flags and attributes
        self.dragged = False
        self.selection = None
        self.tooltipped = None
        self._contents = []
        # Coordinates: When initialized, a tk.Canvas widget's left edge has x-coordinate 0.
        #     This canvas is not intended to be scrolled directly, but rather through movement
        #     of the (dynamic) items on it. The effective view is fully set by .origin, 
        #     .stepsperpixel, and .scalefactor.
        self.__bind_events()
        
    def get_content(self,*args):
        " Returns the content matching the specification in 'args', e.g. an item_id. "
        if len(args) == 0:
            return list(self._contents)
        elif len(args) == 1:
            item_ids = self.find_withtag(args[0])
        else:
            item_ids = self.find_withtag(tuple(args))
        return list([content for content in self._contents if content.item_id in item_ids])
    
    # TimeEngine based coordinate conversion    
    def x_pixel(self,s):
        " Returns the canvas pixel x-coordinate corresponding to the timestep s, given its \
        current '.origin', '.scalefactor', and '.stepsperpixel'. The origin is the canvas \
        position of the start of the current time partition. "
        if type(s) is list: return [self.xPixel(si) for si in s]
        else:
            # step relative to start of partition
            # scaled by scalefactor/stepsperpixel
            # offset by the origin
            return (s-self.time.to_step(0.0))*self.scalefactor/self.stepsperpixel + self.origin
    def s_step(self,x):
        " Returns the timestep corresponding to the canvas pixel x-coordinate x, given its \
        current '.origin', '.scalefactor', and '.stepsperpixel'. The origin is the canvas \
        position of the start of the current time partition. "
        if type(x) is list: return [self.sStep(xi) for xi in x]
        else:
            # position relative to origin
            # scaled by stepsperpixel/scalefactor
            # offset by the start of the partition
            return (x - self.origin)/self.scalefactor*self.stepsperpixel + self.time.to_step(0.0)
        
    # Horizontal scaling (zoom) and scrolling
    def _x_scale_contents(self,x,sf):
        " If part of a PetsFrame, scale all other registered widgets with this one. "
        if self.frame != None: self.frame.x_scale_contents(x,sf)
        else: self.x_scale_contents(x,sf)
    def x_scale_contents(self,x,sf):
        " Scales all dynamic items in the x-direction around center point x with scalefactor 'sf'. "
        # find all dynamic items and scale them one by one
        if not self._allow_dynamic_view: return
        [self._x_scale_item(item_id,x,sf) for item_id in self.find_withtag('dynamic')]
        self.origin = (self.origin - x) * sf + x
        self.scalefactor *= sf
    def _x_scale_item(self,item_id,x,sf):
        " Scales a single item with 'item_id' in the x-direction around center point x\
        with scalefactor 'sf'. "
        # fill in scaling definition for the y-direction
        sf = (sf , 1)
        ctr = (x , 0)        
        # get coordinates of the item
        coords = self.coords(item_id)
        # update coordinates
        self.coords(item_id,tuple([(coords[i] - ctr[i%2]) * sf[i%2] + ctr[i%2] \
                                   for i in range(0,len(coords))]))
    def _x_shift_contents(self,dx):
        " If part of a PetsFrame, shift all other registered widgets with this one. "
        if self.frame != None: self.frame.x_shift_contents(dx)
        else: self.x_shift_contents(dx)
    def x_shift_contents(self,dx):
        " Shifts all dynamic items ('marker','highlight',...) in the x-direction by dx "
        if not self._allow_dynamic_view: return
        [self._x_shift_item(item_id,dx) for item_id in self.find_withtag('dynamic')]
        self.origin += dx
    def _x_shift_item(self,item_id,dx):
        " Scales a single item with 'item_id' in the x-direction by dx. "
        # fill in shift definition for the y-direction
        d = (dx , 0)        
        # get coordinates of the item
        coords = self.coords(item_id)
        # update coordinates
        self.coords(item_id,tuple([(coords[i] + d[i%2]) for i in range(0,len(coords))]))
    def set_view(self,origin=None,scalefactor=None):
        " Sets the view of this TimeCanvas instance based on the keyword arguments 'origin' \
        and 'scalefactor'. This is done, by redrawing all dynamic items with the new parameters. "
        if origin:
            self.x_shift_contents(origin-self.origin)
            self.origin = origin
        if scalefactor: 
            self.x_scale_contents(self.origin,float(scalefactor)/float(self.scalefactor))
            self.scalefactor = scalefactor
        
    # adding contents-management to .delete and .create_* functions
    def _canvas_create(self,mode,*args,**kw):
        if 'tooltip' in kw: tooltip = kw.pop('tooltip')
        else: tooltip = None
        if mode == 'arc': item_id = tk.Canvas.create_arc(self,*args,**kw)
        elif mode == 'bitmap': item_id = tk.Canvas.create_bitmap(self,*args,**kw)
        elif mode == 'image': item_id = tk.Canvas.create_image(self,*args,**kw)
        elif mode == 'line': item_id = tk.Canvas.create_line(self,*args,**kw)
        elif mode == 'oval': item_id = tk.Canvas.create_oval(self,*args,**kw)
        elif mode == 'polygon': item_id = tk.Canvas.create_polygon(self,*args,**kw)
        elif mode == 'rectangle': item_id = tk.Canvas.create_rectangle(self,*args,**kw)
        elif mode == 'text': item_id = tk.Canvas.create_text(self,*args,**kw)
        elif mode == 'window': item_id = tk.Canvas.create_window(self,*args,**kw)
        else: raise NotImplementedError
        self._contents.append(PetsCanvasObject(self,item_id,None,tt=tooltip))
        return item_id        
    def create_arc(self,*args,**kw): return self._canvas_create('arc',*args,**kw) 
    def create_bitmap(self,*args,**kw): return self._canvas_create('bitmap',*args,**kw) 
    def create_image(self,*args,**kw): return self._canvas_create('image',*args,**kw)        
    def create_line(self,*args,**kw): return self._canvas_create('line',*args,**kw)
    def create_oval(self,*args,**kw): return self._canvas_create('oval',*args,**kw)
    def create_polygon(self,*args,**kw): return self._canvas_create('polygon',*args,**kw)
    def create_rectangle(self,*args,**kw): return self._canvas_create('rectangle',*args,**kw)
    def create_text(self,*args,**kw): return self._canvas_create('text',*args,**kw)
    def create_window(self,*args,**kw): return self._canvas_create('window',*args,**kw)
    def delete(self,*args):
        item_ids = tk.Canvas.find_withtag(self,args)
        if len(item_ids) == 0: return
        j = len(self._contents)
        while (j > 0):
            j -= 1
            if self._contents[j].item_id in item_ids: self._contents.pop(j).delete()   
            
    # Additional .create_ functions for time markers
    def create_marker(self,marker,**kwargs):
        assert isinstance(marker,TimeMarker),\
               "{} is not a TimeMarker!".format(marker)
        # pull kw input for tags
        if 'tags' in kwargs: 
            tags = kwargs.pop('tags')
            if type(tags) is str: tags = [tags]
            elif type(tags) is tuple: tags = list(tags)
        else: tags = []
        if 'dynamic' not in tags: tags.append('dynamic')
        if 'marker' not in tags: tags.append('marker')
        # pull kw input for width
        if 'width' in kwargs: linewidth = kwargs.pop('width')
        else: linewidth = self.linewidth    
        # pull kw input for fill
        if 'fill' in kwargs: 
            linecolor = kwargs.pop('fill')
        else:
            linecolor = CHANNELFRAME_MARKER_COLOR
        # override line color if marker is start or end marker
        if self._is_start_marker(marker):
            linecolor = CHANNELFRAME_START_MARKER_COLOR
            tags.append('start')
        elif self._is_end_marker(marker):
            linecolor = CHANNELFRAME_END_MARKER_COLOR
            tags.append('end')
        # pull kw input for bleach
        if 'bleach' in kwargs:
            bleach = kwargs.pop('bleach')
            if linecolor != None:
                linecolor = bleach_color(linecolor,bleach)    
        # create line and add to contents
        tags = tuple(tags)
        item_id = tk.Canvas.create_line(self,\
                                        [self.x_pixel(marker.s),0,\
                                         self.x_pixel(marker.s),self.size[0]],\
                                         fill=linecolor,\
                                         width=linewidth,\
                                         tags=tags,\
                                         **kwargs)
        self._contents.append(PetsCanvasObject(self,item_id,marker,tt=str(marker)))
        return item_id

    # Additional create function for sequence items.
    def create_sequence_item(self,seqitem,**kwargs):
        assert isinstance(seqitem,SequenceItem),\
               "{} is not a SequenceItem!".format(seqitem)
        # pull kw input for tags
        if 'tags' in kwargs: 
            tags = kwargs.pop('tags')
            if type(tags) is str: tags = [tags]
            elif type(tags) is tuple: tags = list(tags)
        else: tags = []
        if seqitem.item_type not in tags: tags.append(seqitem.item_type)
        if 'seqitem' not in tags: tags.append('seqitem')
        if 'dynamic' not in tags: tags.append('dynamic')
        # pull kw input for width
        if 'width' in kwargs: linewidth = kwargs.pop('width')
        else: linewidth = self.linewidth    
        # pull kw input for fill
        if 'fill' in kwargs: 
            fillcolor = kwargs.pop('fill')
        else:
            fillcolor = seqitem.color
        # pull kw input for outline
        if 'outline' in kwargs:
            outlinecolor = kwargs.pop('outline')
        else:
            outlinecolor = CHANNELCANVAS_NOSEL_COLOR
        # pull kw input for bleach
        if 'bleach' in kwargs:
            bleach = kwargs.pop('bleach')
            if fillcolor != None:
                fillcolor = bleach_color(fillcolor,bleach)
            if outlinecolor != None:
                outlinecolor = bleach_color(outlinecolor,bleach)
        # bleach further if not in current part
        if not self._is_in_part(seqitem):
            fillcolor = bleach_color(fillcolor,(self['bg'],0.25))
            outlinecolor = bleach_color(outlinecolor,(self['bg'],0.25))
            if 'outside' not in tags: tags.append('outside')
        # create object and store in ._contents
        tags = tuple(tags)
        if seqitem.item_type in ('set'):
            item_id = tk.Canvas.create_line(self,[self.x_pixel(seqitem.s),2,\
                                             self.x_pixel(seqitem.s),self.size[0]-2],\
                                            fill=fillcolor,\
                                            width=linewidth,\
                                            tags=tags)
            tooltip = "to {}".format(seqitem.y)
        elif seqitem.item_type in ('ramp','pulse'):
            item_id = tk.Canvas.create_rectangle(self,[self.x_pixel(seqitem.s),\
                                                       0.75*self.size[0]-2,\
                                                       self.x_pixel(seqitem.s+seqitem.ds),\
                                                       0.25*self.size[0]],\
                                                 fill=fillcolor,outline=outlinecolor,\
                                                 width=linewidth,\
                                                 tags=tags)
            if seqitem.item_type == 'pulse':
                tooltip = "to {}".format(seqitem.y)
            else:
                tooltip = "{} to {}".format(seqitem.ramp,seqitem.y)
        self._contents.append(PetsCanvasObject(self,item_id,seqitem,tt=tooltip))
        return item_id
    
    # Additional create function for tooltips
    def create_tooltip(self,item_id,**kwargs):
        assert (type(item_id) is int),"Invalid item id!"
        obj = self._contents[self._contents.index(item_id)]
        if obj.instance == None: return
        # restricting tooltips to TimeMarker and SequenceItem
        if not(isinstance(obj.instance,TimeMarker) or\
               isinstance(obj.instance,SequenceItem)): return
        # pull kw input for anchor
        if 'anchor' in kwargs:
            text_anchor = kwargs.pop('anchor')
        else:
            if isinstance(obj.instance,TimeMarker):
                text_anchor = text_anchor = 'nauto'
            elif isinstance(obj.instance,SequenceItem):
                text_anchor = text_anchor = 'auto'
        # deal with anchoring            
        assert (type(text_anchor) is str \
                and text_anchor.lower() in (tk.N,tk.NE,tk.E,tk.SE,tk.S,\
                                            tk.SW,tk.W,tk.NW,tk.CENTER,\
                                            'auto','nauto','sauto')),\
                "Invalid vertical position!"        
        # 'automatic' positioning
        if text_anchor.lower() in ('auto','nauto','sauto'):
            text_anchor = {'auto':'','nauto':'n','sauto':'s'}[text_anchor.lower()]
            if self.x_pixel(obj.instance.s) > self.size[1]/2: 
                text_anchor += tk.E
            else: text_anchor += tk.W
        # vertical position
        if text_anchor.lower() == tk.CENTER: text_anchor = ''
        if tk.S.lower() in text_anchor: ypos = self.size[0]-2
        elif tk.N.lower() in text_anchor: ypos = 3
        else: ypos = self.size[0]/2-2
        text_anchor = text_anchor.lower()
        # horizontal positioning & color
        if isinstance(obj.instance,TimeMarker):
            xpos = self.x_pixel(obj.instance.s)
            if self._is_start_marker(obj.instance):
                textcolor = CHANNELFRAME_START_MARKER_COLOR
            elif self._is_end_marker(obj.instance):
                textcolor = CHANNELFRAME_END_MARKER_COLOR
            else:
                textcolor = CHANNELFRAME_MARKER_COLOR         
        elif isinstance(obj.instance,SequenceItem):
            textcolor = CHANNELCANVAS_NOSEL_COLOR
            if obj.instance.item_type in ('pulse','ramp'):
                xpos = self.x_pixel(obj.instance.s + obj.instance.s/2.0)
                text_anchor = text_anchor.replace(tk.E.lower(),'').replace(tk.W.lower(),'')
            elif obj.instance.item_type == 'set':
                xpos = self.x_pixel(obj.instance.s)
        if text_anchor == '': text_anchor = tk.CENTER  
        # place tooltip
        item_id = self.create_text(xpos,ypos,text=" "+str(obj)+" ",\
                                   anchor=text_anchor,\
                                   fill=textcolor,\
                                   font=tkFont.Font(size=self.ttfontsize),\
                                   tags=('tooltip','dynamic'))
        return item_id
    
    # Some private ._is*() functions
    def _is_start_marker(self,marker):
        return marker == 'Start' or \
               marker == self.time.get_part(marker).start_marker
    def _is_end_marker(self,marker):
        return marker == self.time.get_part(marker).end_marker
    def _is_in_part(self,marker_or_item):
        return self.time.isinpart(marker_or_item,self.time.curpart)
    
    # Finding nearest timing objects
    def find_closest_marker(self,x,y,earlier=False,halo=None):
        " Returns a list of all time markers associated with this TimeCanvas, sorted by their\
        distance to x. Similar to .find_closest(), but does not operate on all canvas items. "        
        markers = self.time.get_all_markers(part=self.time.curpart)
        if len(markers) == 0: return None
        s0 = self.s_step(x)
        if halo == None:
            found =  sorted([[abs(marker.s-s0),marker] \
                             for marker in markers \
                             if (earlier==False or marker.s <= s0)])
        else:
            found =  sorted([[abs(marker.s-s0),marker] \
                             for marker in markers \
                             if ((earlier==False or marker.s <= s0) and\
                                 abs(self.x_pixel(marker.s)-x) <= halo)])
        if len(found) == 0:
            return None
        else:
            return found[0][1]    
    
    # Binding mouse events according to settings
    def __bind_events(self):
        # mouse control
        self.bind('<Enter>',self.__mouse_enters)
        if self._enable_scrolling:
            self.bind('<B1-Motion>',self.__mouse_drag) # left-button mouse drag
            self.bind('<ButtonRelease-1>',self.__mouse_release) # left-button mouse drag
        if self._enable_zooming:
            self.bind('<Button-4>',self.__mouse_scale) # mouse wheel (mac) // at least track pads have small .delta
            self.bind('<Button-5>',self.__mouse_scale) # mouse wheel (mac) // at least track pads have small .delta
            self.bind('<MouseWheel>',self.__mouse_scale) # mouse wheel (windows, unix)
        if self._enable_tooltips:
            self.bind('<Motion>',self.__mouse_move)
            self.bind('<Leave>',self.__mouse_leave)
        self.bind('<Configure>',self.__changing)   
    def enable_scrolling(self):
        " Enables 'scrolling' by mouse drag. "
        if self._enable_scrolling == False: 
            self._enable_scrolling = True
            self.bind('<B1-Motion>',self._mouse_drag)
            self.bind('<ButtonRelease-1>',self._mouse_release)
    def disable_scrolling(self):
        " Disables 'scrolling' by mouse drag. "
        if self._enable_scrolling == True: 
            self._enable_scrolling = False
            self.unbind('<B1-Motion>')
            self.unbind('<ButtonRelease-1>')
    def enable_zooming(self):
        " Enables 'zooming' by mouse scroll wheel action. "
        if self._enable_zooming == False: 
            self._enable_zooming = True
            self.bind('<Button-4>',self._mouse_scale)
            self.bind('<Button-5>',self._mouse_scale)
            self.bind('<MouseWheel>',self._mouse_scale)
    def disable_zooming(self):
        " Disables 'zooming' by mouse scroll wheel action. "
        if self._enable_zooming == True: 
            self._enable_zooming = False
            self.unbind('<Button-4>')
            self.unbind('<Button-5>')
            self.unbind('<MouseWheel>')
    def enable_tooltips(self):
        " Enables 'zooming' by mouse scroll wheel action. "
        if self._enable_tooltips == False: 
            self._enable_tooltips = True
            self.bind('<Motion>',self._mouse_move)
    def disable_tooltips(self):
        " Disables 'zooming' by mouse scroll wheel action. "
        if self._enable_tooltips == True: 
            self._enable_tooltips = False
            self.unbind('<Motion>')
    def __changing(self,conf_event):
        " Updates .size when the size of he canvas is changed (e.g. due to sticky packing) "
        self.size = (conf_event.height,conf_event.width)
        if 'draw_all' in dir(self): self.draw_all()
    def __mouse_move(self,event):
        " Labels the closest marker. "
        if self.frame != None: self.frame.in_all_delete('tooltip')
        else: self.delete('tooltip')
        item_id = self.find_closest(self.canvasx(event.x),\
                                    self.canvasy(event.y))
        if len(item_id) == 0: return
        item_id = item_id[0]
        if item_id not in (self.selection, self.tooltipped): 
            self.create_tooltip(item_id)
    def __mouse_leave(self,event):
        " Remove all tooltips when leaving. "
        self.delete('tooltip')
    def __mouse_drag(self,event):
        " (Fake) scrolling with mouse drag. "
        # using click&drag to scroll left/right
        # not too happy with the extra .dragged and .drag_origin ... better solution?
        if self.dragged == False:
            self.dragged = True
            self.drag_origin = self.canvasx(event.x)
        else:
            # can coarse grain here, if things become sluggish
            if abs(self.drag_origin - self.canvasx(event.x))>1:
                self._x_shift_contents(self.canvasx(event.x) - self.drag_origin)
                self.drag_origin = self.canvasx(event.x)            
    def __mouse_release(self,event):
        # release the dragged attribute (effectively releases drag origin)
        if self.dragged == True: self.dragged = False
    def __mouse_scale(self,event):
        " Scaling with the mouse wheel. "
        sf = min(2.0,max(0.5,1 + MOUSE_ZOOM_SPEED*event.delta))
        self._x_scale_contents(self.canvasx(event.x),sf)
    def __mouse_enters(self,event):
        # set focus to listen to mouse wheel event
        self.focus_set() 