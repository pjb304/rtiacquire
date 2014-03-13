#!/usr/bin/python

"""A widget for displaying a live preview image.

Preview -- a gtk.Image displaying a live camera preview
Author: J.Cupitt
Created as part of the AHRC RTI project in 2011
GNU LESSER GENERAL PUBLIC LICENSE
"""

import logging

import pygtk
pygtk.require('2.0')
import gtk
import glib

import decompress 
import rect 

# inter-frame delay, in milliseconds
# 50 gives around 20 fps and doesn't overload the machine too badly
frame_timeout = 50

# width of selection box border
select_width = 2

# size of corner resize boxes
select_corner = 15

# we have a small state machine for manipulating the select box
def enum(**enums):
    return type('Enum', (), enums)
SelectState = enum(WAIT = 1, DRAG = 2, RESIZE = 3)

# For each edge direction, the corresponding cursor we select
resize_cursor_shape = {
    rect.Edge.NW:   gtk.gdk.Cursor(gtk.gdk.TOP_LEFT_CORNER),
    rect.Edge.NE:   gtk.gdk.Cursor(gtk.gdk.TOP_RIGHT_CORNER),
    rect.Edge.SW:   gtk.gdk.Cursor(gtk.gdk.BOTTOM_LEFT_CORNER),
    rect.Edge.SE:   gtk.gdk.Cursor(gtk.gdk.BOTTOM_RIGHT_CORNER),
    rect.Edge.N:    gtk.gdk.Cursor(gtk.gdk.TOP_SIDE),
    rect.Edge.S:    gtk.gdk.Cursor(gtk.gdk.BOTTOM_SIDE),
    rect.Edge.E:    gtk.gdk.Cursor(gtk.gdk.RIGHT_SIDE),
    rect.Edge.W:    gtk.gdk.Cursor(gtk.gdk.LEFT_SIDE)
}

# another cursor for grag
drag_cursor_shape = gtk.gdk.Cursor(gtk.gdk.FLEUR)

# clip a number to a range
def clip(lower, value, upper):
    return max(min(value, upper), lower)

class Preview(gtk.EventBox):

    """A widget displaying a live preview.

    get_live -- return True if the preview is currently live
    set_live -- turn the live preview on and off
    get_selection -- get the currently selected rect.Rect (if any)
    """

    def draw_rect(self, gc, rect, margin):
        window = self.image.get_window()

        window.draw_rectangle(gc, True,
                              rect.left - margin, 
                              rect.top - margin, 
                              rect.width + margin * 2, 
                              margin * 2)
        window.draw_rectangle(gc, True,
                              rect.right() - margin, 
                              rect.top + margin, 
                              margin * 2,
                              max(0, rect.height - margin * 2))
        window.draw_rectangle(gc, True,
                              rect.left - margin, 
                              rect.bottom() - margin, 
                              rect.width + margin * 2, 
                              margin * 2)
        window.draw_rectangle(gc, True,
                              rect.left - margin, 
                              rect.top + margin, 
                              margin * 2,
                              max(0, rect.height - margin * 2))

    # expose on our gtk.Image
    def expose_event(self, widget, event):
        if self.select_visible:
            self.draw_rect(widget.get_style().white_gc, 
                           self.select_area, select_width)
            self.draw_rect(widget.get_style().black_gc, 
                           self.select_area, select_width - 1)

        return False

    def button_press_event(self, widget, event):
        x = int(event.x)
        y = int(event.y)
        direction = self.select_area.which_corner(select_corner, x, y)

        if self.select_state == SelectState.WAIT and \
            self.select_visible and \
            direction != rect.Edge.NONE:
            self.select_state = SelectState.RESIZE
            self.resize_direction = direction
            corner = self.select_area.corner(direction)
            (cx, cy) = corner.centre()
            self.drag_x = x - cx
            self.drag_y = y - cy
            self.queue_draw()

        elif self.select_state == SelectState.WAIT and \
            self.select_visible and \
            self.select_area.includes_point(x, y):
            self.select_state = SelectState.DRAG
            self.drag_x = x - self.select_area.left
            self.drag_y = y - self.select_area.top
            self.queue_draw()

        elif self.select_state == SelectState.WAIT and \
            self.select_visible:
            self.select_visible = False
            self.queue_draw()

        elif self.select_state == SelectState.WAIT and \
            not self.select_visible:
            self.select_visible = True
            self.select_area.left = x
            self.select_area.top = y
            self.select_area.width = 1
            self.select_area.height = 1
            self.select_state = SelectState.RESIZE
            self.resize_direction = rect.Edge.SE
            self.drag_x = 1
            self.drag_y = 1
            self.queue_draw()

    def motion_notify_event(self, widget, event):
        x = int(event.x)
        y = int(event.y)
        image_width = self.image.get_allocation().width
        image_height = self.image.get_allocation().height

        if self.select_state == SelectState.DRAG:
            self.select_area.left = clip(0, 
                                         x - self.drag_x, 
                                         image_width - self.select_area.width)
            self.select_area.top = clip(0,
                                        y - self.drag_y,
                                        image_height - self.select_area.height)
            self.queue_draw()
        elif self.select_state == SelectState.RESIZE:
            if self.resize_direction in [rect.Edge.SE, rect.Edge.E,
                                         rect.Edge.NE]:
                right = x - self.drag_x
                self.select_area.width = right - self.select_area.left

            if self.resize_direction in [rect.Edge.SW, rect.Edge.S,
                                         rect.Edge.SE]:
                bottom = y - self.drag_y
                self.select_area.height = bottom - self.select_area.top

            if self.resize_direction in [rect.Edge.SW, rect.Edge.W,
                                         rect.Edge.NW]:
                left = x - self.drag_x
                self.select_area.width = self.select_area.right() - left
                self.select_area.left = left

            if self.resize_direction in [rect.Edge.NW, rect.Edge.N,
                                         rect.Edge.NE]:
                top = y - self.drag_y
                self.select_area.height = self.select_area.bottom() - top
                self.select_area.top = top
            
            self.select_area.normalise()
            image = rect.Rect(0, 0, image_width, image_height)
            self.select_area = self.select_area.intersection(image)
            self.queue_draw()

        elif self.select_state == SelectState.WAIT:
            window = self.image.get_window()
            direction = self.select_area.which_corner(select_corner, x, y)

            if self.select_visible and \
                direction != rect.Edge.NONE:
                window.set_cursor(resize_cursor_shape[direction])

            elif self.select_visible and \
                self.select_area.includes_point(x, y):
                window.set_cursor(drag_cursor_shape)

            else:
                window.set_cursor(None)

    def button_release_event(self, widget, event):
        self.select_state = SelectState.WAIT

    def __init__(self, camera):
        """
        Startup.

        camera -- the camera to display, see camera.py

        The preview starts at 640x426 pixels, this may change if the camera
        turns out to have a different size for its preview image.
        """

        gtk.EventBox.__init__(self)

        self.image = gtk.Image()
        self.add(self.image)
        self.image.show()

        # start with a blank 640x426 image, we overwrite this with jpg from
        # the camera during live preview
        self.pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, 
                                     False, 8, 640, 426)
        self.image.set_from_pixbuf(self.pixbuf)
        self.image.set_app_paintable(True)

        self.preview_timeout = 0
        self.camera = camera
        self.frame = 0
        self.select_visible = False
        self.select_area = rect.Rect(10, 10, 100, 100)
        self.select_state = SelectState.WAIT
        self.resize_direction = rect.Edge.N
        self.drag_x = 0
        self.drag_y = 0

        self.image.connect_after('expose-event', self.expose_event)
        self.add_events(gtk.gdk.POINTER_MOTION_MASK)
        self.connect('button-press-event', self.button_press_event)
        self.connect('motion-notify-event', self.motion_notify_event)
        self.connect('button-release-event', self.button_release_event)

    def grab_frame(self):
        logging.debug('grabbing frame ..')
        frame = self.camera.preview()
        if frame == None:
            return
        (data, length) = frame
        if length.value == 0:
            return

        pixbuf = decompress.bufjpeg2pixbuf(data, length)
        if pixbuf != None:
            self.pixbuf = pixbuf
            self.image.set_from_pixbuf(pixbuf)
            self.frame += 1

    def get_live(self):
        """Return True if the display is currently live."""
        return self.preview_timeout != 0

    def get_selection(self):
        """Return a rect.Rect for the selection, or None if no selection
        is active.
        """
        if not self.select_visible:
            return None

        image_width = self.image.get_allocation().width
        image_height = self.image.get_allocation().height
        return rect.Rect(1000 * self.select_area.left / image_width,
                         1000 * self.select_area.top / image_height,
                         1000 * self.select_area.width / image_width,
                         1000 * self.select_area.height / image_height)

    def live_cb(self):
        self.grab_frame()
        return True

    def fps_cb(self):
        logging.debug('fps = %d', self.frame)
        self.frame = 0
        return True

    def set_live(self, live):
        """Turn the live preview on and off.

        live -- True means start the live preview display
        """
        if live and self.preview_timeout == 0:
            logging.debug('starting timeout ..')
            self.preview_timeout = glib.timeout_add(frame_timeout, 
                            self.live_cb)
            self.fps_timeout = glib.timeout_add(1000, self.fps_cb)

        elif not live and self.preview_timeout != 0:
            glib.source_remove(self.preview_timeout)
            self.preview_timeout = 0
            glib.source_remove(self.fps_timeout)
            self.fps_timeout = 0

        if live:
            # grab a frame immediately so we can get an exception, if there
            # are any
            self.grab_frame()

