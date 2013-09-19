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
plotColors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
# The recommended way to use wx with mpl is with the WXAgg
# backend. 
#
import matplotlib
matplotlib.use('WXAgg')
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar
import numpy as np
import pylab
import datetime as dt
from dateutil import rrule
#Data comes from here
from SAS_TM_Parser import SAS_TM_Parser as DataGen

class DataBoundControlBox(wx.Panel):
    """ A static box with a couple of radio buttons and a text
        box. Allows to switch between an automatic mode and a 
        manual mode with an associated value.
    """
    def __init__(self, parent, ID, label, initMin, initMax):
        wx.Panel.__init__(self, parent, ID)
        
        self.minValue = initMin
        self.maxValue = initMax
        
        box = wx.StaticBox(self, -1, label)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        self.radio_auto = wx.RadioButton(self, -1, 
            label="Auto", style=wx.RB_GROUP)
        self.radio_manual = wx.RadioButton(self, -1,
            label="Manual")
        self.min_text = wx.TextCtrl(self, -1, 
            size=(35,-1),
            value=str(initMin),
            style=wx.TE_PROCESS_ENTER)
        self.max_text = wx.TextCtrl(self, -1, 
            size=(35,-1),
            value=str(initMax),
            style=wx.TE_PROCESS_ENTER)
        
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_manual_text, self.min_text)
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_manual_text, self.max_text)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter, self.min_text)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter, self.max_text)
        
        radio_box = wx.BoxSizer(wx.HORIZONTAL)
        radio_box.Add(self.radio_auto, flag=wx.HORIZONTAL)
        radio_box.Add(self.radio_manual, flag=wx.HORIZONTAL)

        text_box = wx.BoxSizer(wx.HORIZONTAL)
        text_box.Add(self.min_text, flag=wx.HORIZONTAL)
        text_box.AddSpacer(12)
        text_box.Add(self.max_text, flag=wx.HORIZONTAL)
        
        sizer.Add(radio_box, 0, wx.ALL, 10)
        sizer.Add(text_box, 0, wx.ALL, 10)
        
        self.SetSizer(sizer)
        sizer.Fit(self)
    
    def on_update_manual_text(self, event):
        self.min_text.Enable(self.radio_manual.GetValue())
        self.max_text.Enable(self.radio_manual.GetValue())
    
    def on_text_enter(self, event):
        self.minValue = self.min_text.GetValue()
        self.maxValue = self.max_text.GetValue()
    
    def is_auto(self):
        return self.radio_auto.GetValue()
        
    def min_value(self):
        return self.minValue

    def max_value(self):
        return self.maxValue


class GraphFrame(wx.Frame):
    """ The main frame of the application
    """
    title = 'Demo: dynamic matplotlib graph'
    
    def __init__(self):
        wx.Frame.__init__(self, None, -1, self.title)
        
        self.datagen = DataGen()
        self.data = []
        self.time = []
        data, time = self.datagen.next()
        for n in range(len(data)):
            newData = (np.array(data[n], ndmin=2)).transpose()
            newTime = (np.array(time[n], ndmin=2)).transpose()
            self.data.append(newData)
            self.time.append(newTime)
        
        self.numplots = len(self.datagen.labels)
        self.plotTitles = self.datagen.titles
        
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

        self.xbound_control = DataBoundControlBox(self.panel, -1, "X Bounds", 0, 50)

        self.ybound_control = []
        for n in range(self.numplots):
            self.ybound_control.append(DataBoundControlBox(self.panel, -1, self.plotTitles[n] + " Y Bounds", 0, 100))

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
        self.hbox2.Add(self.xbound_control, border=5, flag=wx.ALL)
        # self.hbox2.Add(self.xmax_control, border=5, flag=wx.ALL)
        self.hbox2.AddSpacer(24)
        for n in range(self.numplots):
            self.hbox2.Add(self.ybound_control[n], border=5, flag=wx.ALL)
            self.hbox2.AddSpacer(6)
        # self.hbox2.Add(self.ymax_control, border=5, flag=wx.ALL)

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
        self.fig = Figure(dpi=self.dpi)
        self.axes = []
        
        for n in range(self.numplots):
            self.axes.append(self.fig.add_subplot(1,self.numplots,n+1))
            self.axes[n].set_title('SAS Temperature Data ' + str(n), size=12)
            pylab.setp(self.axes[n].get_xticklabels(), fontsize=8)
            pylab.setp(self.axes[n].get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference 
        # to the plotted line series
        #
        self.plot_data = []
        labels = self.datagen.labels
        for n in range(len(self.data)):
            self.plot_data.append([])
            faketime = list(rrule.rrule(rrule.DAILY,count=10,dtstart=dt.datetime.utcnow()))
            for i in range(self.data[n].shape[0]):
                self.plot_data[n].append(self.axes[n].plot_date(faketime,
                                                                np.arange(10),
                                                                linewidth=1,
                                                                label=labels[n][i],
                                                                color=plotColors[i],
                                                                marker='',
                                                                linestyle='-',
                                                                )[0])
            self.axes[n].legend(loc='best',fontsize=6,ncol=3,)
            # self.axes[n].xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y'))
            # self.axes[n].xaxis.set_major_locator(mdates.MinuteLocator())
            # self.axes[n].xaxis.set_minor_formatter(mdates.DateFormatter('%H:%M:%S'))
            # self.axes[n].xaxis.set_minor_locator(mdates.SecondLocator(interval=10))
        self.plot_index = 0

    def draw_plot(self):
        """ Redraws the plot
        """

        xmax = []
        xmin = []
        ymin = []
        ymax = []
        
        for n in range(self.numplots):

            xmaxs = []
            xmins = []
            ymins = []
            ymaxs = []

            self.axes[n].set_title(self.plotTitles[n], size=12)

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
 
            xdata = []
            for i in range(self.time[n].shape[0]):
                if isinstance(self.time[n], np.ndarray) and self.time[n].shape[1] > 1:
                    xdata.append( self.time[n][i][:] )
                else:
                    xdata.append( (self.time[n].shape[1]) )
                xmins.append(min(xdata[i]))
                xmaxs.append(max(xdata[i]))

            # Generate xmin and xmax        
            if self.xbound_control.is_auto():
                xmax.append(max(xmaxs))
                xmin.append(min(xmins))
            else:
                xmax.append(int(self.xbound_control.min_value()))
                xmin.append(self.xbound_control.max_value())


            # Set bounds on x axis

            self.axes[n].set_xbound(lower=dt.datetime.fromtimestamp(xmin[n]), 
                                    upper=dt.datetime.fromtimestamp(xmax[n]))

            # Determine the indicies being displayed
            idxMin = []
            idxMax = []
            for i in range(self.data[n].shape[0]):
                idxMin.append( np.searchsorted(xdata[i], xmin[n]) )
                idxMax.append( np.searchsorted(xdata[i], xmax[n]) )
                # print i, idxMin, idxMax, len(xdata[i])
                # print xdata[i]
                # print xdata[i][idxMin:idxMax]
                self.plot_data[n][i].set_xdata(np.array([dt.datetime.fromtimestamp(x) for x in xdata[i][idxMin[i]:idxMax[i]]]))

            # Generate ydata
            for i in range(self.data[n].shape[0]):
                if isinstance(self.data[n], np.ndarray) and self.data[n].shape[1] > 1:
                    ydata = self.data[n][i][idxMin[i]:idxMax[i]]
                else:
                    ydata = np.ones(idxMax[i]-idxMin[i])
                ymins.append(min(ydata))
                ymaxs.append(max(ydata))
                self.plot_data[n][i].set_ydata(ydata)
                

    
            # for ymin and ymax, find the minimal and maximal values
            # in the data set and add a mininal margin.
            # 
            # note that it's easy to change this scheme to the 
            # minimal/maximal value in the current display, and not
            # the whole data set.
            # 
            
            if self.ybound_control[n].is_auto():
                ymin.append(min(ymins) - 5)
                ymax.append(max(ymaxs) + 5)
            else:
                ymin.append(int(self.ybound_control[n].min_value()))
                ymax.append(int(self.ybound_control[n].max_value())) 



            # Set x and y bounds for each plot
            self.axes[n].set_ybound(lower=ymin[n], upper=ymax[n])



        self.fig.autofmt_xdate()
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
        if not self.paused:
            data, time = self.datagen.next()
            for n in range(self.numplots):
                newData = (np.array(data[n], ndmin=2)).transpose()
                newTime = (np.array(time[n], ndmin=2)).transpose()
                if (len(self.data[n]) < RECORD_LENGTH_MAX):
                    self.data[n] = np.hstack((self.data[n], newData))
                    self.time[n] = np.hstack((self.time[n], newTime))
                else:
                    self.data[n] = np.hstack((self.data[n][1:(RECORD_LENGTH_MAX)], newData))
                    self.time[n] = np.hstack((self.time[n][1:(RECORD_LENGTH_MAX)], newTime))
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
