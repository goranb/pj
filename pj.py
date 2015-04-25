#!/usr/bin/env python

"""PJ Software"""

import gobject
gobject.threads_init()
import gst
import pygtk
pygtk.require("2.0")
import gtk
gtk.gdk.threads_init()
import sys
import os

class PJException(Exception):
    """Base exception class for errors which occur during demos"""

    def __init__(self, reason):
        self.reason = reason

class PJ:
    """PJ main class"""

    __name__ = "PJ"
    __usage__ = "python pj.py -- starts the PJ"
    __def_win_size__ = (960, 540)

    def destroy(self, widget, data=None):
        gtk.main_quit()

    def create_decodebin(self):
        try:
            return gst.element_factory_make("decodebin2")
        except:
            return gst.element_factory_make("decodebin")

    # def magic(self, pipeline, sink, args):
    #     """This is where the magic happens"""
    #     src = gst.element_factory_make("videotestsrc", "src")
    #     pipeline.add(src)
    #     src.link(sink)

    def magic(self, pipeline, sink, args):

        def onPad(obj, pad, target):
            sinkpad = target.get_compatible_pad(pad, pad.get_caps())
            if sinkpad:
                pad.link(sinkpad)
            return True

        assert len(sys.argv) == 3
        assert os.path.exists(sys.argv[1])
        assert os.path.exists(sys.argv[2])

        srcA = gst.element_factory_make("filesrc")
        srcA.set_property("location", sys.argv[1])

        srcAdecode = self.create_decodebin()
        srcAconvert = gst.element_factory_make("ffmpegcolorspace")
        srcAalpha = gst.element_factory_make("alpha")
        srcAalpha.set_property("alpha", 1.0)

        srcB = gst.element_factory_make("filesrc")
        srcB.set_property("location", sys.argv[2])

        srcBdecode = self.create_decodebin()
        srcBconvert = gst.element_factory_make("ffmpegcolorspace")
        srcBalpha = gst.element_factory_make("alpha")
        srcBalpha.set_property("alpha", 0.5)

        mixer = gst.element_factory_make("videomixer")
        mixer.set_property("background", "black")

        pipeline.add(mixer)

        pipeline.add(srcA, srcAdecode, srcAconvert, srcAalpha)
        srcA.link(srcAdecode)
        srcAdecode.connect("pad-added", onPad, srcAconvert)
        srcAconvert.link(srcAalpha)
        srcAalpha.link(mixer)

        pipeline.add(srcB, srcBdecode, srcBconvert, srcBalpha)
        srcB.link(srcBdecode)
        srcBdecode.connect("pad-added", onPad, srcBconvert)
        srcBconvert.link(srcBalpha)
        srcBalpha.link(mixer)

        mixer.link(sink)

        # remember the alpha elements
        self.srcBalpha = srcBalpha

    def createPipeline(self, w):
        """Given a window, creates a pipeline and connects it to the window"""

        # code will make the ximagesink output in the specified window
        def set_xid(window):
            gtk.gdk.threads_enter()
            sink.set_xwindow_id(window.window.xid)
            sink.expose()
            gtk.gdk.threads_leave()

        # this code receives the messages from the pipeline. if we
        # need to set X11 id, then we call set_xid
        def bus_handler(unused_bus, message):
            if message.type == gst.MESSAGE_ELEMENT:
                if message.structure.get_name() == 'prepare-xwindow-id':
                    set_xid(w)
            return gst.BUS_PASS

        # create our pipeline, and connect our bus_handler
        self.pipeline = gst.Pipeline()
        bus = self.pipeline.get_bus()
        bus.set_sync_handler(bus_handler)

        sink = gst.element_factory_make("ximagesink", "sink")
        sink.set_property("force-aspect-ratio", True)
        sink.set_property("handle-expose", True)
        scale = gst.element_factory_make("videoscale", "scale")
        cspace = gst.element_factory_make("ffmpegcolorspace", "cspace")

        # our pipeline looks like this: ... ! cspace ! scale ! sink
        self.pipeline.add(cspace, scale, sink)
        scale.link(sink)
        cspace.link(scale)
        return (self.pipeline, cspace)

    # subclasses can override this method to provide custom controls
    def customWidgets(self):
        return gtk.HBox()

    def createWindow(self):
        """Creates a top-level window"""

        # create window, set basic attributes
        w = gtk.Window()
        w.set_size_request(*self.__def_win_size__)
        w.set_title(self.__name__)
        w.connect("destroy", gtk.main_quit)

        # declare buttons and their associated handlers
        controls = (
            ("play_button", gtk.ToolButton(gtk.STOCK_MEDIA_PLAY), self.onPlay),
            ("stop_button", gtk.ToolButton(gtk.STOCK_MEDIA_STOP), self.onStop),
            ("quit_button", gtk.ToolButton(gtk.STOCK_QUIT), gtk.main_quit)
        )

        # as well as the container in which to put them
        box = gtk.HButtonBox()

        # for every widget, connect to its clicked signal and add it
        # to the enclosing box
        for name, widget, handler in controls:
            widget.connect("clicked", handler)
            box.pack_start(widget, True)
            setattr(self, name, widget)

        viewer = gtk.DrawingArea()
        viewer.modify_bg(gtk.STATE_NORMAL, viewer.style.black)

        # we will need this later
        self.xid = None

        # now finally do the top-level layout for the window
        layout = gtk.VBox(False)
        layout.pack_start(viewer)

        # subclasses can override childWidgets() to supply
        # custom controls
        layout.pack_start(self.customWidgets(), False, False)
        layout.pack_end(box, False, False)
        w.add(layout)
        w.show_all()

        # we want to return only the portion of the window which will
        # be used to display the video, not the whole top-level
        # window. a DrawingArea widget is, in fact, an X11 window.
        return viewer

    def onPlay(self, unused_button):
        self.pipeline.set_state(gst.STATE_PLAYING)

    def onStop(self, unused_button):
        self.pipeline.set_state(gst.STATE_READY)

    def run(self):
        w = self.createWindow()
        w.connect("destroy", self.destroy)
        p, s = self.createPipeline(w)
        try:
            self.magic(p, s, sys.argv[1:])
            self.pipeline.set_state(gst.STATE_PLAYING)
            gtk.main()
        except PJException, e:
            print e.reason
            print self.__usage__
            sys.exit(-1)

# if this file is being run directly, create the demo and run it
if __name__ == '__main__':
    PJ().run()



#import gobject
#import pygame
#import time
#import signal
#import sys
#import pygst

# ability to quit
# def signal_handler(signal, frame):
#     print 'Received Signal: {}'.format(signal)
#     print '...quitting...'
#     pygame.quit()
#     sys.exit(0)

# signal.signal(signal.SIGTERM, signal_handler)
# signal.signal(signal.SIGINT, signal_handler)

# initiate graphic environment
# pygame.init()
# size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
# black = 0, 0, 0
# screen = pygame.display.set_mode(size, pygame.FULLSCREEN & pygame.OPENGL)
#pygame.mouse.set_visible(0)
# initial logo

# time.sleep(3)