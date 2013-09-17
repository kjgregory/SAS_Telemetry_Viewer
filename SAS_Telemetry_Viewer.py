"""
GP:
Changed datasource, title, and refresh interval to use
as a poor man's Arduino oscilliscope.

This demo demonstrates how to draw a dynamic mpl (matplotlib) 
plot in a wxPython application.

It allows "live" plotting as well as manual zooming to specific
regions.

Both X and Y axes allow "auto" or "manual" settings. For Y, auto
mode sets the scaling of the graph to see all the data points.
For X, auto mode makes the graph "follow" the data. Set it X min
to manual 0 to always see the whole data from the beginning.

Note: press Enter in the 'manual' text box to make a new value 
affect the plot.

Eli Bendersky (eliben@gmail.com)
License: this code is in the public domain
Last modified: 31.07.2008
"""
import os
#import pprint
#import random
import sys
import wx

REFRESH_INTERVAL_MS = 500
RECORD_LENGTH_MAX = 100000

# The recommended way to use wx with mpl is with the WXAgg
# backend. 
#
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar
import numpy as np
import pylab
#Data comes from here
from SAS_TM_Parser import SAS_TM_Parser as DataGen


class BoundControlBox(wx.Panel):
    """ A static box with a couple of radio buttons and a text
        box. Allows to switch between an automatic mode and a 
        manual mode with an associated value.
    """
    def __init__(self, parent, ID, label, initval):
        wx.Panel.__init__(self, parent, ID)
        
        self.value = initval
        
        box = wx.StaticBox(self, -1, label)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        self.radio_auto = wx.RadioButton(self, -1, 
            label="Auto", style=wx.RB_GROUP)
        self.radio_manual = wx.RadioButton(self, -1,
            label="Manual")
        self.manual_text = wx.TextCtrl(self, -1, 
            size=(35,-1),
            value=str(initval),
            style=wx.TE_PROCESS_ENTER)
        
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_manual_text, self.manual_text)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter, self.manual_text)
        
        manual_box = wx.BoxSizer(wx.HORIZONTAL)
        manual_box.Add(self.radio_manual, flag=wx.ALIGN_CENTER_VERTICAL)
        manual_box.Add(self.manual_text, flag=wx.ALIGN_CENTER_VERTICAL)
        
        sizer.Add(self.radio_auto, 0, wx.ALL, 10)
        sizer.Add(manual_box, 0, wx.ALL, 10)
        
        self.SetSizer(sizer)
        sizer.Fit(self)
    
    def on_update_manual_text(self, event):
        self.manual_text.Enable(self.radio_manual.GetValue())
    
    def on_text_enter(self, event):
        self.value = self.manual_text.GetValue()
    
    def is_auto(self):
        return self.radio_auto.GetValue()
        
    def manual_value(self):
        return self.value


class GraphFrame(wx.Frame):
    """ The main frame of the application
    """
    title = 'Demo: dynamic matplotlib graph'
    
    def __init__(self):
        wx.Frame.__init__(self, None, -1, self.title)
        
        self.datagen = DataGen()
        data = self.datagen.next()
        if isinstance(data, np.ndarray):
            self.data = [data]
        else: 
            self.data = [100]

        #self.data = [self.datagen.next()]
        self.paused = False
        
        self.create_menu()
        self.create_status_bar()
        self.create_main_panel()
        
        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)        
        self.redraw_timer.Start(REFRESH_INTERVAL_MS)

    def create_menu(self):
        self.menubar = wx.MenuBar()
        
        menu_file = wx.Menu()
        m_expt = menu_file.Append(-1, "&Save plot\tCtrl-S", "Save plot to file")
        self.Bind(wx.EVT_MENU, self.on_save_plot, m_expt)
        menu_file.AppendSeparator()
        m_exit = menu_file.Append(-1, "E&xit\tCtrl-X", "Exit")
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)
                
        self.menubar.Append(menu_file, "&File")
        self.SetMenuBar(self.menubar)

    def create_main_panel(self):
        self.panel = wx.Panel(self)

        self.init_plot()
        self.canvas = FigCanvas(self.panel, -1, self.fig)

        self.xmin_control = BoundControlBox(self.panel, -1, "X min", 0)
        self.xmax_control = BoundControlBox(self.panel, -1, "X max", 50)
        self.ymin_control = BoundControlBox(self.panel, -1, "Y min", 0)
        self.ymax_control = BoundControlBox(self.panel, -1, "Y max", 100)
        self.plot_choice_control = BoundControlBox(self.panel, -1, "Sensor", 0)
        self.alarm_control = BoundControlBox(self.panel, -1, "Alarm", -30)

        self.pause_button = wx.Button(self.panel, -1, "Pause")
        self.Bind(wx.EVT_BUTTON, self.on_pause_button, self.pause_button)
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_pause_button, self.pause_button)
        
        self.cb_grid = wx.CheckBox(self.panel, -1, 
            "Show Grid",
            style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_grid, self.cb_grid)
        self.cb_grid.SetValue(True)
        
        self.cb_xlab = wx.CheckBox(self.panel, -1, 
            "Show X labels",
            style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_xlab, self.cb_xlab)        
        self.cb_xlab.SetValue(True)
        
        self.hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox1.Add(self.pause_button, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        self.hbox1.AddSpacer(20)
        self.hbox1.Add(self.cb_grid, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        self.hbox1.AddSpacer(10)
        self.hbox1.Add(self.cb_xlab, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        
        self.hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox2.Add(self.xmin_control, border=5, flag=wx.ALL)
        self.hbox2.Add(self.xmax_control, border=5, flag=wx.ALL)
        self.hbox2.AddSpacer(24)
        self.hbox2.Add(self.ymin_control, border=5, flag=wx.ALL)
        self.hbox2.Add(self.ymax_control, border=5, flag=wx.ALL)
        self.hbox2.AddSpacer(24)
        self.hbox2.Add(self.plot_choice_control, border=5, flag=wx.ALL)
        self.hbox2.Add(self.alarm_control, border=5, flag=wx.ALL)

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, flag=wx.LEFT | wx.TOP | wx.GROW)        
        self.vbox.Add(self.hbox1, 0, flag=wx.ALIGN_LEFT | wx.TOP)
        self.vbox.Add(self.hbox2, 0, flag=wx.ALIGN_LEFT | wx.TOP)
        
        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)
    
    def create_status_bar(self):
        self.statusbar = self.CreateStatusBar()

    def init_plot(self):
        self.dpi = 100
        self.fig = Figure((3.0, 3.0), dpi=self.dpi)
        self.axes = []
        for n in range(len(self.data)):
            self.axes.append(self.fig.add_subplot(1,len(self.data),n))
            self.axes[n].set_title('SAS Temperature Data', size=12)
            pylab.setp(self.axes[n].get_xticklabels(), fontsize=8)
            pylab.setp(self.axes[n].get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference 
        # to the plotted line series
        #
        self.plot_data = []
        labels = self.datagen.labels
        for n in range(len(self.data)):        
            for i in range(len(self.data[n])):
                self.plot_data.append(self.axes[n].plot(np.arange(10),
                                                     linewidth=1,
                                                     label=labels[n][i],
                                                     #color=(1, 1, 0),  #let it auto-select colors
                                                     )[0])
            self.axes[n].legend(loc='best',fontsize=6,ncol=6)
        self.plot_index = 0

    def draw_plot(self):
        """ Redraws the plot
        """
        # when xmin is on auto, it "follows" xmax to produce a 
        # sliding window effect. therefore, xmin is assigned after
        # xmax.
        #
        for n in range(len(self.axes)):
            if self.xmax_control.is_auto():
                xmax[n] = len(self.data[n]) if len(self.data[n]) > 50 else 50
            else:
                xmax[n] = int(self.xmax_control.manual_value())
                
            if self.xmin_control.is_auto():            
                xmin[n] = xmax[n] - 100
            else:
                xmin[n] = int(self.xmin_control.manual_value())
    
            # for ymin and ymax, find the minimal and maximal values
            # in the data set and add a mininal margin.
            # 
            # note that it's easy to change this scheme to the 
            # minimal/maximal value in the current display, and not
            # the whole data set.
            # 
            if self.ymin_control.is_auto():
                ymins[n] = np.zeros(min(len(self.data[n]),(xmax[m]-max(xmin[n],0))),float)
                for i in range(min(len(self.data[n]),xmax[n]-max(xmin[n],0))):
                    ymins[n][i] = min(self.data[n][i+max(xmin[n],0)])
                ymin[n] = min(ymins[n]) - 1
            else:
                ymin[n] = int(self.ymin_control.manual_value())
            
            if self.ymax_control.is_auto():
                ymaxs[n] = np.zeros(min(len(self.data[n]),(xmax[n]-max(xmin[n],0))),float)
                for i in range(min(len(self.data[n]),xmax[n]-max(xmin[n],0))):
                    ymaxs[n][i] = max(self.data[n][i+max(xmin[n],0)])
                ymax[n] = max(ymaxs[n]) + 1
            else:
                ymax[n] = int(self.ymax_control.manual_value())
    
            if self.plot_choice_control.is_auto():
                if len(self.data[n]) > 1: 
                    self.plot_index = (self.plot_index+1) % len(self.data[n][0,:]);
                    self.axes[n].set_title('SAS Temperature Data', size=12)
            else:
                self.plot_index = int(self.plot_choice_control.manual_value())
                self.axes[n].set_title('SAS Temperature Data ' + str(self.plot_index), size=12)
            
    
            self.axes[n].set_xbound(lower=xmin[n], upper=xmax[n])
            self.axes[n].set_ybound(lower=ymin[n], upper=ymax[n])
            
            # anecdote: axes.grid assumes b=True if any other flag is
            # given even if b is set to False.
            # so just passing the flag into the first statement won't
            # work.
            #
            if self.cb_grid.IsChecked():
                self.axes[n].grid(True, color='gray')
            else:
                self.axes[n].grid(False)
    
            # Using setp here is convenient, because get_xticklabels
            # returns a list over which one needs to explicitly 
            # iterate, and setp already handles this.
            #  
            pylab.setp(self.axes[n].get_xticklabels(), 
                visible=self.cb_xlab.IsChecked())
            
            for i in range(np.size(self.data[n],1)):        
                self.plot_data[n][i].set_xdata(np.arange(len(self.data[n])))
            if isinstance(self.data[n], np.ndarray) and len(self.data[n]) > 1:
                for i in range(np.size(self.data,1)):
                    #self.plot_data.set_ydata(self.data[:,self.plot_index])
                    self.plot_data[n][i].set_ydata(self.data[n][:,i]);
            else: 
                for i in range(np.size(self.data,1)):
                    self.plot_data[n][i].set_ydata(np.ones(len(self.data[n])))
        
        self.canvas.draw()
    
    def on_pause_button(self, event):
        self.paused = not self.paused
    
    def on_update_pause_button(self, event):
        label = "Resume" if self.paused else "Pause"
        self.pause_button.SetLabel(label)
    
    def on_cb_grid(self, event):
        self.draw_plot()
    
    def on_cb_xlab(self, event):
        self.draw_plot()
    
    def on_save_plot(self, event):
        file_choices = "PNG (*.png)|*.png"
        
        dlg = wx.FileDialog(
            self, 
            message="Save plot as...",
            defaultDir=os.getcwd(),
            defaultFile="plot.png",
            wildcard=file_choices,
            style=wx.SAVE)
        
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.canvas.print_figure(path, dpi=self.dpi)
            self.flash_status_message("Saved to %s" % path)
    
    def on_redraw_timer(self, event):
        # if paused do not add data, but still redraw the plot
        # (to respond to scale modifications, grid change, etc.)
        #
        if self.alarm_control.is_auto():
        	alarm_temp = -30
        else:
            alarm_temp = int(self.alarm_control.manual_value())
        if not self.paused:
            data = self.datagen.next()
            if isinstance(data, np.ndarray) and not isinstance(self.data, np.ndarray):
                self.data = data
            if isinstance(data, np.ndarray) and isinstance(self.data, np.ndarray):
                for n in range(len(self.axes)):                
                    if (len(self.data[n]) < RECORD_LENGTH_MAX):
                        self.data = np.vstack((self.data[n], data[n]))
                    else:
                        self.data = np.vstack((self.data[n][1:(RECORD_LENGTH_MAX)],data[n]))
                        if np.any(data < alarm_temp):
                            sys.stdout.write('\a')
                            sys.stdout.flush()
        self.draw_plot()
    
    def on_exit(self, event):
        self.Destroy()
    
    def flash_status_message(self, msg, flash_len_ms=1500):
        self.statusbar.SetStatusText(msg)
        self.timeroff = wx.Timer(self)
        self.Bind(
            wx.EVT_TIMER, 
            self.on_flash_status_off, 
            self.timeroff)
        self.timeroff.Start(flash_len_ms, oneShot=True)
    
    def on_flash_status_off(self, event):
        self.statusbar.SetStatusText('')


if __name__ == '__main__':
    app = wx.PySimpleApp()
    app.frame = GraphFrame()
    app.frame.Show()
    app.MainLoop()
