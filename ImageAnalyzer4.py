# 
# Program to analize digital images
#
# usefule for:
#  - read the coordinates of idividual points
#  - measure distances
# - digitize plots (log and lin scale)
#
# version 4
# this version can also measure distances

from PyQt5 import QtWidgets, QtCore, QtGui
import sys
#import wx
import os

import LT.box as B

#import pdb

# begin wxGlade: extracode
# end wxGlade

import matplotlib.pyplot as plt
#import matplotlib.patches as mpatches

from matplotlib.figure import Figure
from matplotlib.font_manager import FontManager

import numpy as np

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT

#----------------------------------------------------------------------
# helper functions
#----------------------------------------------------------------------

def angle(sint, cost):
    # calculate the angle 0 < theta < 2 pi if sin and cos are given
    ang = 0.
    # check data boundaries
    if cost > 1.: 
        cost = 1.
    if cost < -1. : 
        cost = -1.
    if sint > 1.:
        sint = 1.
    if sint < -1.:
        sint= - 1.
    arg1=np.arccos(cost)
# 
# find the quadrant
# 
    q1 = (sint >= 0.) and (cost >= 0.)
    q2 = (sint >= 0.) and (cost < 0.)
    q3 = (sint < 0.) and (cost < 0.)
    q4 = (sint < 0.) and (cost >= 0.)
    if (q1 or q2):
        ang=arg1
    if (q3 or q4):
        ang=2.*np.pi-arg1 
    return ang

def find_duplicates(a):
    # find duplicates in an array and return a list of uniqe values
    # and a list of indices where they ocur in the original one
    r = []
    ind = []
    # fund duplicates
    for i,l in enumerate(a):
        if l in r:
            continue
        else:
            r.append(l)
    # find locations
    for l in r:
        ia = []
        for i,q in enumerate(a):
            if ( q == l ):
                ia.append(i)
        ind.append(ia)
    return r, ind

#----------------------------------------------------------------------
# find a specific menu action
#----------------------------------------------------------------------
def action_dict(m):
    # m is a menubar or a menu
    # name is the menu name
    actions = [(A.text(),A) for A in m.actions()]
    menu_dict = dict(actions)            
    return menu_dict    


#----------------------------------------------------------------------
class NumberDialog(QtWidgets.QDialog):
    def __init__(self, data, parent = None, title = 'Enter parameters', labels=['First Label','Second Label'],
                  keys=['first','second'], about_txt = 'about_txt'):
          self.parent=parent
          self.keys=keys
          self.data=data
          QtWidgets.QDialog.__init__(self, parent)
          self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
          self.setWindowTitle(title)
          self.layout=QtWidgets.QGridLayout(self)
          about = QtWidgets.QLabel(about_txt, self)
          ok=QtWidgets.QPushButton('Ok', self)
          ok.setDefault(True)
          cancel=QtWidgets.QPushButton('Cancel', self)
          ok.clicked.connect(self.OnOk)
          cancel.clicked.connect(self.OnCancel)
          sepline=QtWidgets.QFrame()
          sepline.setFrameShape(QtWidgets.QFrame.HLine)
          sepline.setFrameShadow(QtWidgets.QFrame.Sunken)
          # setup layout
          self.layout.addWidget(about, 0, 0)
          self.layout.addWidget(sepline, 1, 0, 1, 2)
          # loop over keys to add controls and validators
          nrow = len(keys)+1
          #qle - qlinedit dictionary to retrieve data later
          self.qle={}
          for i, key in enumerate(keys):
               Val_l  = QtWidgets.QLabel(labels[i], self)
               Val_t  = QtWidgets.QLineEdit(self)
               Val_t.setValidator(QtGui.QDoubleValidator(self))
               #
               Val_t.textChanged.connect(self.check_state)
               Val_t.setText(data.get(key))
               self.layout.addWidget(Val_l, i+2, 0)
               self.layout.addWidget(Val_t, i+2, 1)
               self.qle[key]=Val_t
          # add the OK widget
          self.layout.addWidget(ok, nrow+2, 0)
          self.layout.addWidget(cancel, nrow+2, 1)
          
    def check_state(self, *args, **kwargs):
         
        sender = self.sender()
        validator = sender.validator()
        state = validator.validate(sender.text(), 0)[0]
        if state == QtGui.QValidator.Acceptable:
            color = '#c4df9b' # green
        elif state == QtGui.QValidator.Intermediate:
            color = '#fff79a' # yellow
        else:
            color = '#f6989d' # red
        sender.setStyleSheet('QLineEdit { background-color: %s }' % color)
        
    def OnOk(self):
         for i, key in enumerate(self.keys):
             try:
                 self.data[key]=self.qle[key].text()
             except:
                 mb=QtWidgets.QMessageBox(self)
                 mb.setWindowTitle('Entry error')
                 mb.setText("Please enter the missing parameter")
                 mb.exec_()
                 self.qle[key].setFocus()
                 return
         self.close()
     
    def OnCancel(self):
         self.destroy()



#----------------------------------------------------------------------
# main frame
#----------------------------------------------------------------------

class IAFrame(QtWidgets.QMainWindow):
    def __init__(self, parent, callback = None, **kwargs):
        super(IAFrame, self).__init__()
        # begin wxGlade: IAFrame.__init__
        self.setWindowTitle('Image Analyzer 4')
        self.setGeometry(150,150,700,600)
        
        # Menu Bar
        self.IAFrame_menubar = self.menuBar()
        self.createMenubar()
# data directories
        self.image_dir = ''
        self.output_dir = ''
        
# setup figure
        self.figure = Figure(figsize=(10,6))
        self.axes = self.figure.add_subplot(111)
        
        self.figure_canvas = FigureCanvas(self.figure)
        self.canvas =  self.figure_canvas
        self.font_size = FontManager.get_default_size()
        
# setup callback function for MPL API event interface
        self.figure_canvas.mpl_connect('button_press_event', self.button_press_callback)
        self.figure_canvas.mpl_connect('button_release_event', self.button_release_callback)
        self.figure_canvas.mpl_connect('motion_notify_event', self.UpdateStatusBar)
        self.figure_canvas.mpl_connect('motion_notify_event', self.motion_notify_callback)
        self.figure_canvas.mpl_connect('figure_enter_event', self.ChangeCursor)
        self.setCentralWidget(self.figure_canvas)
        
# add ToolBar
        self.toolbar = NavigationToolbar2QT(self.figure_canvas, self, coordinates=False)
        self.addToolBar(self.toolbar)
        
# create status bar
        self.stBar1 = QtWidgets.QLabel('No file open')
        self.stBar1.setFrameStyle(2)
        self.stBar1.setFrameShadow(48)
        self.stBar2 = QtWidgets.QLabel('Pos:')
        self.stBar2.setFrameStyle(2)
        self.stBar2.setFrameShadow(48)
        self.stBar3 = QtWidgets.QLabel('Status: idle')
        self.stBar3.setFrameStyle(2)
        self.stBar3.setFrameShadow(48)
          
        self.statusBar().addWidget(self.stBar1, 1)
        self.statusBar().addWidget(self.stBar2, 1)
        self.statusBar().addWidget(self.stBar3, 1)
       # initialize parameters
        self.init_parameters()
        self.show()
        
    def init_parameters(self):
        self.image = None
        self.npoints = 0
        # array with the picked points
        self.points = []
        self.data_source = []   # array with filenames for the points, used when combining data from several files 
        self.error_bars_sym= []
        self.error_bars_ul = []
        self.error_bars_ll = []
        # positions
        self.start_pos = [0.,0.]
        self.world_start_pos = [0.,0.]
        self.world_end_pos = [1.,1.]
        # array of calibration distances
        self.dx = []
        self.dy = []
        self.distance = []
        self.pix_distance = []
        self.cal_dx = []
        self.cal_dy = []
        self.xw_off = []
        self.yw_off = []
        self.xw_off_av = 0.
        self.yw_off_av = 0.
        # conversion pix to user (cal.) values
        self.convx = []
        self.convy = []
        # averaged conversion values
        self.convx_av = 1.
        self.convy_av = 1.
        self.enter_positions = False
        self.calibrate_xy = False
        self.calibrate_x = False
        self.calibrate_y = False
        self.log10x = False
        self.log10y = False
        self.calibrate_y = False
        self.measure = False
        self.filename=""
        self.origin_pos = 'upper'
        self.use_lower_origin = True
        self.use_upper_origin = False
        self.points_filename="points.data"
        self.center_values = True
        self.sym_error_bar = False
        self.low_error_bar = False
        self.up_error_bar = False
        self.asym_error_bar = False
        self.combine_files = False
        
        self.button_release = False
        self.dlx = 0.02 #fractional offsets
        self.dly = 0.02
        self.dtx = 0.01
        self.dty = 0.01
#        # create a line for calibrated drawing later:
        self.lines = [] 
        self.leaders = []
        self.texts = []
        # setup background
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)
        # cursor
        self.cursor_init = False
        self.cross_hair = False
        self.key_pressed = False
        self.key_released = False   
        self.line_color = 'b'
        self.text_color = 'r'
        self.marker_color = 'r'
        self.cursor_color = 'g'


    def closeEvent(self, event):
        close = QtWidgets.QMessageBox()
        close.setText("Are you sure?")
        close.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)
        close = close.exec()
        if close == QtWidgets.QMessageBox.Yes:
            event.accept()
            QtWidgets.QApplication.quit()
        else:
            event.ignore()

    
    #menu bar data
    def menuData(self): # data for the menu setup
          return(
                 ("File","normal",                                        # menu label
                 ("Open", "Open an image file to analyze", self.onOpen),  # menu items consisting of: label, text, handler
                 ("Save", "Save positions", self.onSave),  
                 ("Save as", "Save positions as", self.onSaveAs),                  
                 ("Quit", "Quit", self.onQuit), 
                 ), # label, status and handler
                #
                 ("&Analyze","normal",
                 ("&Pick points", "", self.onEnterPositions),
                 ("&Measure", "", self.onMeasure),
                 ("&Clear", "", self.onClear),
                 ),
                 #
                 ("&Calibration","normal",
                 ("&Calibrate XY", "Pick calibration points in XY", self.onCalibrateXY), 
                 ("&Calibrate X", "Pick calibration points in X", self.onCalibrateX), 
                 ("&Calibrate Y", "Pick calibration pointsin Y", self.onCalibrateY), 
                 ("&Load Calibration", "Get calibration information from file", self.onLoadCal), 
                 ("&Enter Calibration", "Enter calibration parameters", self.onEnterCal), 
                 ("&Show", "Display calibration parameters", self.onShowCal),
                 ("&Clear", "Clear calibration", self.onClearCal)
                 ),
                 # checkable menus use the form
                 # name, hint, group, action, default value
                 ("&Scale Options","checkable",
                 ("Use Lower Origin", "Set Origin at lower y-Position", "X", self.onLowerOrigin, False ),
                 ("Use Upper Origin", "Set Origin at upper y-Position", "X", self.onUpperOrigin, True ),
                 ("log X", "X scale log", None, self.onLogX, False ), 
                 ("log Y", "Y scale log", None, self.onLogY, False)
                 ),
#                         
                 ("&Data Options","checkable",
                 ("combine files", "Combine data from several files" , None, self.onCombineFiles, False),
                 ("center value", "Pick Value" , "X", self.onCenterValue, True),
                 ("sym. error bar", "Pick Symmetric Error Bar", "X", self.onSymErrorBar, False),
                 ("lower error bar", "Pick Lower Error Bar" , "X", self.onLowErrorBar, False),
                 ("upper error bar", "Pick Upper Error Bar", "X", self.onUpErrorBar, False)
                 ), 
#                 
                 ("&Settings","normal",
                 ("Marker Color", "Select marker color" , self.onSelectColor),                  
                 ("Text Color", "Select text color" , self.onSelectColor),
                 ("Line Color", "Select line color", self.onSelectColor),
                 ("Cursor Color", "Select cursor color" , self.onSelectColor)
                 )                 
                 )                        
                  
    def createMenubar(self):
        # for normal and chackable menu items
        # exclusive menu items are grouped in an action group, ungrouped should 
        # enter None in that field: currently fiel 2
        # dictionary that contains the entire menu information
        self.menu_dict = {}
        for eachMenuData in self.menuData(): 
             menuLabel = eachMenuData[0]
             menuType = eachMenuData[1]
             menuItems = eachMenuData[2:]
               
             if (menuType == "normal"):
                 menu = QtWidgets.QMenu(menuLabel, self)
                 for eachItem in menuItems:
                      subMenuLabel = eachItem[0]
                      subMenuAction = eachItem[2]
                      subMenu=QtWidgets.QAction(subMenuLabel,self) 
                      subMenu.triggered.connect(subMenuAction)
                      menu.addAction(subMenu)                  
                 self.IAFrame_menubar.addMenu(menu)
                 self.menu_dict[menuLabel] = menu
             elif (menuType == "checkable"):
                 menu = QtWidgets.QMenu(menuLabel, self)
                 # find group items
                 gk = [eachItem[2] for eachItem in menuItems]
                 groups, loc = find_duplicates(gk)
                 # prepare groups and normals checkable menus
                 for i,g in enumerate(groups):
                     if g is None:
                         # normal checkable menu item
                         for j in loc[i]:
                             eachItem = menuItems[j]
                             subMenuLabel = eachItem[0]
                             subMenuAction = eachItem[3]
                             check_status = eachItem[-1]
                             subMenu=QtWidgets.QAction(subMenuLabel,self, checkable = True) 
                             subMenu.triggered.connect(subMenuAction)
                             subMenu.setChecked(check_status)
                             menu.addAction(subMenu)                               
                     else:
                         # put menus in a menyActionGroup
                         menuActionGroup = QtWidgets.QActionGroup(self)
                         menuActionGroup.setExclusive(True)
                         for j in loc[i]:
                             eachItem = menuItems[j]
                             subMenuLabel = eachItem[0]
                             subMenuAction = eachItem[3]
                             check_status = eachItem[-1]                             
                             subMenu=QtWidgets.QAction(subMenuLabel,self, checkable = True) 
                             subMenu.triggered.connect(subMenuAction)
                             subMenu.setChecked(check_status)  
                             menu.addAction(subMenu)
                             menuActionGroup.addAction(subMenu)
                 self.IAFrame_menubar.addMenu(menu)
                 self.menu_dict[menuLabel] = menu
        
    def get_file_info(self, filename):
        dir, fname = os.path.split(filename)
        name, ext = os.path.splitext(fname)
        return dir, name, ext
        # that's it

    def update_graph(self):
        self.axes.clear()
        if not (self.image is None):
            self.axes.imshow(self.image, interpolation = None, origin = self.origin_pos)
        self.figure.canvas.draw()
        # necessary to make a hard copy
        self.axes.set_autoscale_on(False)
        
    def set_defaults(self):
        # initialize parameters
        self.init_parameters()
        # set initial values of checkable menus to default values
        D = action_dict(self.menu_dict["&Scale Options"])
        D["Use Lower Origin"].setChecked(False)
        D["Use Upper Origin"].setChecked(True)
        D["log X"].setChecked(False)
        D["log Y"].setChecked(False)
        D = action_dict(self.menu_dict["&Data Options"])
        D["center value"].setChecked(True)        
        D["sym. error bar"].setChecked(False)     
        D["lower error bar"].setChecked(False)     
        D["upper error bar"].setChecked(False)             
        
        # print("onOpen :", [A.text() for A in ScaleActions]  )        
    def onOpen(self):  # wxGlade: IAFrame.<event_handler>
        # initialize parameters
        if not self.combine_files:
            # dot not initialize data parameters
            self.init_parameters()
            self.set_defaults()
        else:
            # save currently open figure, the previous one
            if self.filename != "":
                self.save_current_fig()
        if self.image_dir == '':
            self.image_dir = os.getcwd()
        # get a filenmae
        filename = QtWidgets.QFileDialog.getOpenFileName(self, 'Select a file', self.image_dir)
        # read the image
        try:
            self.image = plt.imread(filename[0])
        except:
            if filename[0] == '':
                return
            else:
                print("cannot open: ", filename[0])
            
        self.filename = filename[0]
        dir_name, name, ext = self.get_file_info(self.filename)
        self.image_dir = dir_name
        self.dir = dir_name+'//'
        self.name = name
        self.ext = ext
        # show current fil name
        self.stBar1.setText(self.name+self.ext)
        self.calibrate = False
        self.measure = False
        self.enter_positions = False
        self.update_status("idle")
        # show the image
        self.update_graph()

    def onLoadCal(self, event):  # wxGlade: IAFrame.<event_handler>
        # get the filename containing the calibration
        filename = QtWidgets.QFileDialog.getOpenFileName(self, 'Select calibration file', os.getcwd())
        # open file
        try:
            cal = B.get_file(filename[0])
#            xx = cal.par.get_value( 'convx_av')
        except:
            dlg = QtWidgets.QMessageBox(self)
            dlg.setText("Cannot find calibration information !")
            dlg.setWindowTitle("Calibration Problem")
            dlg.setIcon(2)
            dlg.exec_()
            return
        # get first calibration
        self.convx_av = cal.par.get_value( 'convx_av')
        self.convy_av = cal.par.get_value( 'convy_av')

    def onEnterCal(self):
        # enter calibration parameters
        # parameter keys
        pkeys=['conversion factor:']
        # current data to be shown in the dialog
        data = {pkeys[0]:"%f"%(self.convx_av), \
                }
        pdlg = NumberDialog(data, title="X-axis Calibration ", \
                            labels = pkeys, \
                            keys = pkeys, \
                            about_txt = "Enter the conversion factor")
        
        # now set the new parameters
        pdlg.exec_()
        self.convx_av = float(data[ pkeys[0] ])
        pdlg.destroy()
        # scale the y-axis
        # check if the same scale is to be used for y-axis
        dlg = QtWidgets.QMessageBox(self)
        dlg.setText("use the same as for X-axis ?")
        dlg.setWindowTitle("Y-axis scale")
        dlg.setStandardButtons(QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No)
        same_as_x = dlg.exec_() == QtWidgets.QMessageBox.Yes

        if same_as_x:
            self.convy_av = self.convx_av 
        else:
            # current data to be shown in the dialog
            data = {pkeys[0]:"%d"%(self.convy_av), \
                    }
            pdlg = NumberDialog(data, title="Y-axis Calibration ", \
                                labels = pkeys, \
                                keys = pkeys, \
                                about_txt = "Enter the conversion factor")
            
            pdlg.exec_()
            # now set the new parameters
            self.convy_av = float(data[ pkeys[0] ])
            pdlg.destroy()
        # done manually entering conversion factors
        
    def onShowCal(self, event):
        # show calibration parameters
        message = "convx_av = {0:10.3e}/ convy_av = {1:10.3e}".format(self.convx_av, self.convy_av)
        dlg = QtWidgets.QMessageBox(self)
        dlg.setText(message)
        dlg.setWindowTitle("Current conversion factors")
        dlg.exec_()

    def onClearCal(self):
        # clear the calibration point arrays and parameter arrays
        self.dx = []
        self.dy = []
        self.distance = []
        self.pix_distance = []
        self.cal_dx = []
        self.cal_dy = []
        # conversion pix to user (cal.) values
        self.convx = []
        self.convy = []
        # averaged conversion values
        self.convx_av = 1.
        self.convy_av = 1.

    def save_all(self):
        self.save_points(self.points_filename)
        self.save_current_fig()
        
    def save_current_fig(self):
        out_dir, name, ext = self.get_file_info(self.filename)
        self.set_animated(False)
        self.figure.savefig(self.filename + "_annot.png")
        self.set_animated(True)
        

    def onSave(self):  # wxGlade: IAFrame.<event_handler>
        self.save_all()
        #event.Skip()
 

    def onSaveAs(self):  # wxGlade: IAFrame.<event_handler>
        if self.output_dir == "":
            self.output_dir = os.getcwd() # set output_dir to current directory if not set
        file_dlg = QtWidgets.QFileDialog.getSaveFileName(self, "Save points as ...",
                            self.output_dir,"*.data")
        print ('output file = ', file_dlg )
        if file_dlg[0] != '':
            dir_name, name, ext = self.get_file_info(file_dlg[0])
            filename = file_dlg[0]
            self.points_filename = filename   # save the current output directory name for future use
            self.output_dir = dir_name
            self.save_all()

    def onQuit(self):  # wxGlade: IAFrame.<event_handler>
        self.close()
        

    def calibrate_off(self):
        self.calibrate_xy = False
        self.calibrate_x = False
        self.calibrate_y = False

    def onCalibrateXY(self, event):  # wxGlade: IAFrame.<event_handler>
        if self.enter_positions:
            if self.warning( "You are still entering positions!","stop and calibrate ?"):
                self.calibrate_xy = True
                self.measure = False
                self.enter_positions = False
                self.update_status("calibrate XY")
            else:
                return
        self.calibrate_xy = True
        self.measure = False
        self.enter_positions = False
        self.update_status("calibrate XY")

    def onCalibrateX(self, event):  # wxGlade: IAFrame.<event_handler>
        if self.enter_positions:
            if self.warning( "You are still entering positions!","stop and calibrate ?"):
                self.calibrate_x = True
                self.measure = False
                self.enter_positions = False
                self.update_status("calibrate X")
            else:
                return
        self.calibrate_x = True
        self.measure = False
        self.enter_positions = False
        self.update_status("calibrate X")

    def onCalibrateY(self, event):  # wxGlade: IAFrame.<event_handler>
        if self.enter_positions:
            if self.warning( "You are still entering positions!","stop and calibrate ?"):
                self.calibrate_y = True
                self.measure = False
                self.enter_positions = False
                self.update_status("calibrate Y")
            else:
                return
        self.calibrate_y = True
        self.measure = False
        self.enter_positions = False
        self.update_status("calibrate Y")

    def onEnterPositions(self):  # wxGlade: IAFrame.<event_handler>
        self.enter_positions = True
        self.measure = False
        self.calibrate = False
        if self.center_values:
            self.update_status("enter center positions")
        elif self.sym_error_bar:
            self.update_status("enter sym. errorbars")
        elif self.low_error_bar:
            self.update_status("enter lower errorbars")
        elif self.up_error_bar:
            self.update_status("enter upper errorbars")

    def onMeasure(self):
        if self.enter_positions:
            if self.warning( "You are still entering positions!","stop and measure                                ?"):
                self.measure = True
                self.enter_positions = False
                self.calibrate = False
                self.update_status("measure")
            else:
                return
        self.measure = True
        self.calibrate = False
        self.enter_positions = False
        self.update_status("measure")

#    def onRedraw(self):  # wxGlade: IAFrame.<event_handler>
#        self.redraw()

    def onLowerOrigin(self, event):
        sender = self.sender()
        print("Lower Origing : ",sender.isChecked())
        if sender.isChecked():
            self.origin_pos = 'lower'
            self.use_lower_origin = True
            self.use_upper_origin = False
        else:
            print("Lower Origin, do nothing")

    def onUpperOrigin(self, event):
        sender = self.sender()
        print("Upper Origing : ",sender.isChecked())
        if sender.isChecked():
            self.origin_pos = 'upper'
            self.use_lower_origin = False
            self.use_upper_origin = True
        else:
            print("Lower Origin, do nothing")

    def onLogX(self, event):
        self.log10x = self.sender().isChecked()
        print("log10x = ", self.log10x)

    def onLogY(self, event):
        self.log10y = self.sender().isChecked()
        print("log10y = ", self.log10y)

    def onCombineFiles(self, event):
        sender = self.sender()
        self.combine_files = not self.combine_files
        sender.setChecked(self.combine_files)
        print("combine_files value = ", self.combine_files)


    def onCenterValue(self, event):
        self.center_values = self.sender().isChecked()
        if self.center_values:
            self.sym_error_bar = False
            self.low_error_bar = False
            self.up_error_bar = False
        print("central value = ", self.center_values)
 
    def onSymErrorBar(self, event):
        sender = self.sender()
        if self.points == []:
            self.warning("no central values picked","cannot pick errors" )
            # reset the checked menu
            # make a dictionary of actions and menu items 
            AG = sender.actionGroup()
            menu_actions = [(A.text(),A) for A in AG.actions()]
            menu_dict = dict(menu_actions)            
            sender.setChecked(False)
            menu_dict["center value"].setChecked(True)
            return
        self.sym_error_bar = sender.isChecked()
        if self.sym_error_bar:
            self.center_values = False
            self.low_error_bar = False
            self.up_error_bar = False        
        print("sym. error bars = ", self.sym_error_bar)
        self.npoints = 0
 
    def onLowErrorBar(self, event):
        sender = self.sender()        
        if self.points == []:
            self.warning("no central values picked","cannot pick errors" )
            # reset the checked menu
            # make a dictionary of actions and menu items 
            AG = sender.actionGroup()
            menu_actions = [(A.text(),A) for A in AG.actions()]
            menu_dict = dict(menu_actions)            
            sender.setChecked(False)
            menu_dict["center value"].setChecked(True)
            return        
        self.low_error_bar = sender.isChecked()
        if self.low_error_bar:
            self.sym_error_bar = False
            self.center_values = False
            self.up_error_bar = False        
        print("low. error bar = ", self.low_error_bar)
        self.asym_error_bar = True
        self.npoints = 0
        
    def onUpErrorBar(self, event):
        sender = self.sender()        
        if self.points == []:
            self.warning("no central values picked","cannot pick errors" )
            # reset the checked menu
            # make a dictionary of actions and menu items 
            AG = sender.actionGroup()
            menu_actions = [(A.text(),A) for A in AG.actions()]
            menu_dict = dict(menu_actions)            
            sender.setChecked(False)
            menu_dict["center value"].setChecked(True)
            return
        self.up_error_bar = sender.isChecked()
        if self.up_error_bar:
            self.sym_error_bar = False
            self.low_error_bar = False
            self.center_values = False        
        print("up_error_bar = ", self.up_error_bar)
        self.asym_error_bar = True
        self.npoints = 0     

    def onSelectColor(self, event):
        sender = self.sender()
        color = QtWidgets .QColorDialog.getColor()
        if color.isValid():
            a_name = sender.text()
            if a_name == "Text Color":
                # set text color
                self.text_color = color.name()
            elif a_name == "Line Color":
                # set line color
                self.line_color = color.name()
            elif a_name == "Marker Color":
                # set marker color
                self.marker_color = color.name()
            elif a_name == "Cursor Color":
                # set marker color
                self.cursor_color = color.name()
            else:
                print("do not know what this color is for !")
        else:
            print("Bad color selection !")
        
    def onClear(self):
        # reset markers
        self.npoints = 0
        # picked points
        self.points = []
        self.data_source = []
        self.clear()
        self.error_bars_sym= []
        self.error_bars_ul = []
        self.error_bars_ll = []


    def warning(self, title, message):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setText(message)
        dlg.setWindowTitle(title)
        dlg.setStandardButtons(QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel)
        ret = dlg.exec_() == QtWidgets.QMessageBox.Ok
        
        return ret

    def update_status(self, status):
        self.stBar3.setText("Status: " + status)

    def save_points(self, filename):
        # check error bar consistency
        if self.sym_error_bar:
            if len(self.points) != len(self.error_bars_sym):
                print("array lengths:", len(self.points) , len(self.error_bars_sym))
                self.warning('Wrong number of error bars','cannot save them !')
                self.sym_error_bar = False
        elif self.asym_error_bar:
            if len(self.points) != len(self.error_bars_ll):
                self.warning('Wrong number of error bars for lower limit','cannot save them !')
                self.asym_error_bar = False
        elif self.asym_error_bar:
            if len(self.points) != len(self.error_bars_ul):
                self.warning('Wrong number of error bars for upper limit','cannot save them !')
                self.asym_error_bar = False
        f = open(filename,'w')
        # write header
        f.write("# data points from file : " +self.filename+'\n')
        f.write("# xpw and ypw are positions in calibrated user units (e.g mm) \n")
        f.write("#\n")
        f.write("# Calibration information \n")
        f.write("#\\ convx_av = {0:11.4e}\n".format(self.convx_av))
        f.write("#\\ convy_av = {0:11.4e}\n".format(self.convy_av))
        f.write("# offsets \n")
        f.write("#\\ xoff = {0:11.4e}\n".format(self.start_pos[0]))
        f.write("#\\ yoff = {0:11.4e}\n".format(self.start_pos[1]))
        f.write("#\\ world_xs = {0:11.4e}\n".format(self.world_start_pos[0]))
        f.write("#\\ world_ys = {0:11.4e}\n".format(self.world_start_pos[1]))
        f.write("#\\ xw_xoff = {0:11.4e}\n".format(self.xw_off_av))
        f.write("#\\ yw_yoff = {0:11.4e}\n".format(self.yw_off_av))
        if self.sym_error_bar:
            headerline = "#! n[i,0]/ xp[f,1]/ yp[f,2]/ xpw[f,3]/ ypw[f,4]/ dypw[f,5]/"
            if self.combine_files:
                headerline += " filename[s,6]/"
        elif self.asym_error_bar:
            headerline = "#! n[i,0]/ xp[f,1]/ yp[f,2]/ xpw[f,3]/ ypw[f,4]/ ypw_ll[f,5]/ ypw_ul[f,6]/"
            if self.combine_files:
                headerline += " filename[s,7]/"
        else:
            headerline = "#! n[i,0]/ xp[f,1]/ yp[f,2]/ xpw[f,3]/ ypw[f,4]/"
            if self.combine_files:
                headerline += " filename[s,5]/"
        f.write(headerline + "\n")    
        for i,p in enumerate(self.points):
            xp = p[0]
            yp = p[1]
            xwp = p[0]*self.convx_av + self.xw_off_av
            ywp = p[1]*self.convy_av + self.yw_off_av
            if self.log10x :
                xwp = 10.**(xwp)
            if self.log10y:
                ywp = 10.**(ywp)
            if self.sym_error_bar:
                yep = self.error_bars_sym[i][1]
                ywp_up = yep*self.convy_av + self.yw_off_av
                if self.log10y:
                    ywp_up = 10.**(ywp_up)                
                dywp = np.abs(ywp_up - ywp)
                if self.combine_files:
                    o_s = f"{i:d} {xp:11.4e} {yp:11.4e} {xwp:11.4e} {ywp:11.4e} {dywp:11.4e} {self.data_source[i]:s} \n"
                else:
                    o_s = f"{i:d} {xp:11.4e} {yp:11.4e} {xwp:11.4e} {ywp:11.4e} {dywp:11.4e}\n"               
            elif self.asym_error_bar:
                ll = self.error_bars_ll[i][1]
                ul = self.error_bars_ul[i][1]
                ywp_ll = ll*self.convy_av + self.yw_off_av
                ywp_ul = ul*self.convy_av + self.yw_off_av
                if self.log10y:
                    ywp_ll = 10.**(ywp_ll)
                    ywp_ul = 10.**(ywp_ul)
                if self.combine_files:
                    o_s = f"{i:d} {xp:11.4e} {yp:11.4e} {xwp:11.4e} {ywp:11.4e} {ywp_ll:11.4e} {ywp_ul:11.4e} {self.data_source[i]:s} \n"
                else:
                    o_s = f"{i:d} {xp:11.4e} {yp:11.4e} {xwp:11.4e} {ywp:11.4e} {ywp_ll:11.4e} {ywp_ul:11.4e}\n"
            else:
                if self.combine_files:
                    o_s = f"{i:d} {xp:11.4e} {yp:11.4e} {xwp:11.4e} {ywp:11.4e} {self.data_source[i]:s}\n"
                else:
                   o_s = f"{i:d} {xp:11.4e} {yp:11.4e} {xwp:11.4e} {ywp:11.4e} \n"
            f.write( o_s)
        f.close()
        dir, name, ext = self.get_file_info(filename)
        self.update_status("saved to:  " + name+ext)        

        

###############################################################################
    
#from draw pannel class

###############################################################################

    def UpdateStatusBar(self, event):
        if event.inaxes:
            x, y = event.xdata, event.ydata
            text="Pos: {0:.2f}, {1:.2f}".format(x,y)
            self.stBar2.setText(text)

    def motion_notify_callback(self, event):
        #self.background = self.canvas.copy_from_bbox(self.axes.bbox)
        button_not_pressed = (event.button != 1)
        if event.inaxes is None: return # do nothing if not in axis
        if button_not_pressed and not self.enter_positions : 
            return   # do nothing if the button is not pressed
        if not self.cursor_init:
            self.init_cursor(0., 0.)
        self.set_cursor(event.xdata, event.ydata)
        if self.calibrate_xy and (not self.button_release):
            self.end_pos = event.xdata, event.ydata
            self.sc_end_pos = event.x, event.y
            self.canvas.restore_region(self.background)
            # data for get_line
            #x = [self.start_pos[0], self.end_pos[0]]
            #y = [self.start_pos[1], self.end_pos[1]]
            # data fot get_step_line
            x = [self.start_pos[0], self.end_pos[0], self.end_pos[0]]
            y = [self.start_pos[1], self.start_pos[1], self.end_pos[1]]
            self.current_line.set_data( (x,y))
            self.canvas.restore_region(self.background)
            self.draw_cursor()
            self.axes.draw_artist(self.current_line)
            self.canvas.blit(self.axes.bbox)
        elif self.calibrate_x and (not self.button_release):
            self.end_pos = event.xdata, event.ydata
            self.sc_end_pos = event.x, event.y
            self.canvas.restore_region(self.background)
            # data for get_line
            x = [self.start_pos[0], self.end_pos[0]]
            y = [self.start_pos[1], self.end_pos[1]]
            self.current_line.set_data( (x,y))
            self.canvas.restore_region(self.background)
            self.draw_cursor()
            self.axes.draw_artist(self.current_line)
            self.canvas.blit(self.axes.bbox)
        elif self.calibrate_y and (not self.button_release):
            self.end_pos = event.xdata, event.ydata
            self.sc_end_pos = event.x, event.y
            self.canvas.restore_region(self.background)
            # data for get_line
            x = [self.start_pos[0], self.end_pos[0]]
            y = [self.start_pos[1], self.end_pos[1]]
            self.current_line.set_data( (x,y))
            self.canvas.restore_region(self.background)
            self.draw_cursor()
            self.axes.draw_artist(self.current_line)
            self.canvas.blit(self.axes.bbox)
        elif self.measure and (not self.button_release):
            self.end_pos = event.xdata, event.ydata
            self.sc_end_pos = event.x, event.y
            # data for get_line
            x = [self.start_pos[0], self.end_pos[0]]
            y = [self.start_pos[1], self.end_pos[1]]
            self.canvas.restore_region(self.background)
            self.current_line.set_data( (x,y))            
            self.draw_cursor()
            self.axes.draw_artist(self.current_line)
            self.canvas.blit(self.axes.bbox)
        #elif self.enter_positions and (not self.button_release):
        elif self.enter_positions:
            self.end_pos = event.xdata, event.ydata
            #self.canvas.restore_region(self.background)
            #self.draw_cursor()
            #self.canvas.blit(self.axes.bbox)
            if (not self.cross_hair):
                return
            else:
                # self.set_cursor(x,y)
                self.canvas.restore_region(self.background)
                self.draw_cursor()
                self.canvas.blit(self.axes.bbox)
        else:
            if (not self.cross_hair):
                return
            else:
                # self.set_cursor(x,y)
                self.canvas.restore_region(self.background)
                self.draw_cursor()
                self.canvas.blit(self.axes.bbox)
            

    def ChangeCursor(self, event):
          self.figure_canvas.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
    
        
    def button_press_callback(self,event):
        # event.button : which button
        # event.x : screen x-position
        # event.y : screen y-position
        # event.xdata : x-position in axis units (None if outside)
        # event.ydata : y-position in axis units (None if outside)
        # event.inaxis: Axes in which the mouse currently is (None if outside)
        self.button_release = False
        if event.inaxes == None:
            return
        if event.button > 1:
            if self.enter_positions:
                self.enter_positions = False
                self.update_status("idle")
                return
        pos = (event.xdata, event.ydata)
        if not self.cursor_init:
            self.init_cursor(pos[0], pos[1])
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)
        if self.enter_positions:
            # enter positions
            # draw marker at the location
            self.npoints += 1
        elif self.calibrate_xy:
            self.start_pos = event.xdata, event.ydata
            self.end_pos = event.xdata, event.ydata
            self.sc_start_pos = event.x, event.y
            self.sc_end_pos = event.x, event.y
            # self.current_line = self.get_line()
            self.current_line = self.get_step_line()
            self.lines.append(self.current_line)
        elif self.calibrate_x:
            self.start_pos = event.xdata, event.ydata
            self.end_pos = event.xdata, event.ydata
            self.sc_start_pos = event.x, event.y
            self.sc_end_pos = event.x, event.y
            self.current_line = self.get_line()
            self.lines.append(self.current_line)
        elif self.calibrate_y:
            self.start_pos = event.xdata, event.ydata
            self.end_pos = event.xdata, event.ydata
            self.sc_start_pos = event.x, event.y
            self.sc_end_pos = event.x, event.y
            self.current_line = self.get_line()
            self.lines.append(self.current_line)
        elif self.measure:
            self.start_pos = event.xdata, event.ydata
            self.end_pos = event.xdata, event.ydata
            self.sc_start_pos = event.x, event.y
            self.sc_end_pos = event.x, event.y
            # self.current_line = self.get_line()
            self.current_line = self.get_line()
            self.lines.append(self.current_line)
        #self.update_graph()

    def process_positions(self):
        print("Process : ", self.npoints)
        self.data_source.append(self.filename)
        if self.center_values:
                self.points.append(self.end_pos )
                
        elif self.sym_error_bar:
            if self.npoints > len(self.points):
                self.warning("Too many error bars", "More errors than data points")
                return
            else:
                self.error_bars_sym.append( self.end_pos )
        elif self.low_error_bar:
            if self.npoints > len(self.points):
                self.warning("Too many error bars", "More errors than data points")
                return
            else:            
                self.error_bars_ll.append( self.end_pos )
        elif self.up_error_bar:
            if self.npoints > len(self.points):
                self.warning("Too many error bars", "More errors than data points")
                return
            else:            
                self.error_bars_ul.append( self.end_pos )            
        self.draw_marker(self.end_pos, self.npoints )        

    def button_release_callback(self,event):
        # here we need a text control to enter the real distance for calibration
        # set this flag true to freeze the current mouse positions
        # necessary for  WINDOWS running as ShowModal does not completely work
        self.button_release = True
        if self.calibrate_xy:
            self.process_xy_calibration()
        if self.calibrate_x:
            self.process_x_calibration()
        if self.calibrate_y:
            self.process_y_calibration()
        if self.measure:
            self.process_measure()
        if self.enter_positions:
            self.process_positions()            

    def set_animated(self, value):
        # change the status on animated, used value = False for hard copies
        for l in self.leaders:
            l.set_animated(value)
        for t in self.texts:
            t.set_animated(value)
        for L in self.lines:
            L.set_animated(value)
    
#    def redraw(self):
#        self.set_animated(False)
#        self.background = self.canvas.copy_from_bbox(self.axes.bbox)
#        self.set_animated(True)
#        self.canvas.restore_region(self.background)

    def clear(self):
        # reset all arrays
        self.lines = []
        self.texts = []
        self.leaders = []
        self.update_graph()
            
    def init_cursor(self, x, y):
        # create a crosshair cursor
        self.cursor_init = True
        self.cx_data = ((x,x), self.axes.get_ylim())
        self.cy_data = (self.axes.get_xlim(), (y,y))
        self.cx, = self.axes.plot(self.cx_data[0], self.cx_data[1], color = self.cursor_color, animated = True)
        self.cy, = self.axes.plot(self.cy_data[0], self.cy_data[1], color = self.cursor_color, animated = True)

    def set_cursor(self, x, y):
        self.cx_data =  ((x, x), self.axes.get_ylim())
        self.cy_data =  (self.axes.get_xlim(), (y,y))
        self.cx.set_data(self.cx_data)
        self.cy.set_data(self.cy_data)

    def draw_cursor(self):
        # draw the cursor
        self.axes.draw_artist(self.cx)
        self.axes.draw_artist(self.cy)
        
    def get_line(self):
        # to draw animated lines
        x = [0.,1.]
        y = [0.,1.]
        line, = self.axes.plot(x,y, color = self.line_color, marker='x', animated=True) # do not show the line now !
        return line

    def get_step_line(self):
        # to draw amimated step line
        # three points
        x = [0.,1.,1.]
        y = [0.,0.,1.]
        line, = self.axes.plot(x,y, color = self.line_color, marker='x', animated=True) # do not show the line now !
        return line

    def get_text(self):
        text = self.axes.text(0,0, "", color = self.text_color, animated = True )
        return text
    
    def get_marker(self):
        # to draw animated markers
        x = [0.,1.]
        y = [0.,1.]
        leader, = self.axes.plot(x,y, color = self.marker_color, animated = True)
        text = self.axes.text(0,0, "", color = self.marker_color, animated = True )
        return (leader, text)
        


    def process_xy_calibration(self):
        # get offsets in real world values
        start_pos = np.array(self.start_pos)
        end_pos = np.array(self.end_pos)
        sc_start_pos = np.array(self.sc_start_pos)
        sc_end_pos = np.array(self.sc_end_pos)
        r = end_pos - start_pos
        rs = sc_end_pos - sc_start_pos
        d = np.sqrt( np.sum(r*r) )
        dx = r[0]
        dy = r[1]
        self.distance.append(d)
        # same end point as starting point, give warning
        if d == 0.:
            self.warning( "Calibration Problem : Distance = 0.", \
                                 "You need to keep the mouse button pressed while dragging !")
            self.button_release = False
            return
        # use parameter
        self.dx.append(r[0])
        self.dy.append(r[1])
        ds = np.sqrt( np.sum(rs*rs) )
        self.pix_distance.append(ds)
        #
        # choice for calibrating
        choices = ["X-axis", "Y-axis", "X/Y independent"]
        selection = choices[0]
        dlg = QtWidgets.QInputDialog(self)
        dlg.setWindowTitle("Calibration Method " )
        dlg.setLabelText("Select axis to be used") 
        dlg.setComboBoxItems(choices)
        dlg.setOption(dlg.UseListViewForComboBoxItems)
        ok = dlg.exec_() == 1
        item = dlg.textValue()
        dlg.destroy()
        if ok and item!='':
            selection = item
        # scale the x-axis
        # use a NumberDialog to get calibration data
        # parameter keys
        pkeys=['Real (world units) displacement:']
        # current data to be shown in the dialog
        data = {pkeys[0]:"%d"%(r[0]), \
                }
        cdx = 1.
        cdy = 1.
        if (selection != choices[1]):
            pdlg = NumberDialog(data, title="X-axis Calibration ", \
                                labels = pkeys, \
                                keys = pkeys, \
                                about_txt = "Enter the measured displacement in world units")
            pdlg.exec_()
            pdlg.destroy()
            # now set the new parameters
            cdx = float(data[ pkeys[0] ])
        if (selection != choices[0]):
            # scale the y-axis
            # current data to be shown in the dialog
            data = {pkeys[0]:"%d"%(r[1]), \
                    }
            pdlg = NumberDialog(data, title="Y-axis Calibration ", \
                                labels = pkeys, \
                                keys = pkeys, \
                                about_txt = "Enter the measured displacement in world units")
            pdlg.exec_()
            pdlg.destroy()
            # now set the new parameters
            cdy = float(data[ pkeys[0] ])
        if selection == choices[0]:
            cdy = cdx/dx*dy
        if selection == choices[1]:
            cdx = cdy/dy*dx
        # update calibration factor
        self.convx.append( cdx/dx)
        self.convy.append( cdy/dy)
        # calcula averaged calibration
        self.convx_av = ( np.array(self.convx) ).mean()
        self.convy_av = ( np.array(self.convy) ).mean()
        # 
        self.cal_dx.append( cdx  )
        self.cal_dy.append( cdy  )
#        cd = np.sqrt(cdx**2 + cdy**2 )
        # create the text labels
        textx = self.get_text()
        texty = self.get_text()
        text_posx = start_pos + 0.5*np.array([dx, -0.1*dy])
        text_posy = end_pos - 0.5*np.array([0., dy])
        textx.set_position(text_posx )
        texty.set_position(text_posy )
        #text.set_rotation(text_angle)
        textx.set_ha('center')
        texty.set_ha('right')
        textx.set_rotation_mode('anchor')
        texty.set_rotation_mode('anchor')
        textx.set_text("dx {0:6.1f}/{1:10.3e}".format(r[0],cdx) )
        texty.set_text("dy {0:6.1f}/{1:10.3e}".format(r[1],cdy) )
        # draw the text
        self.axes.draw_artist(textx)
        self.axes.draw_artist(texty)
        self.texts.append(textx)
        self.texts.append(texty)
        self.canvas.blit(self.axes.bbox)
        # reset the calibration
        self.calibrate_xy = False
        self.update_status("idle")
        # store last image
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)
        self.button_release = False

    def process_x_calibration(self):
        # get offsets in real world values
        start_pos = np.array(self.start_pos)
        start_pos_world = np.zeros_like(start_pos)
        end_pos = np.array(self.end_pos)
        end_pos_world = np.zeros_like(end_pos)
        sc_start_pos = np.array(self.sc_start_pos)
        sc_end_pos = np.array(self.sc_end_pos)
        r = end_pos - start_pos
        rs = sc_end_pos - sc_start_pos
        d = np.sqrt( np.sum(r*r) )
        dx = r[0]
        self.distance.append(d)
        # same end point as starting point, give warning
        if d == 0.:
            self.warning( "Calibration Problem : Distance = 0.", \
                                 "You need to keep the mouse button pressed while dragging !")
            self.button_release = True
            return
        # use parameter
        self.dx.append(r[0])
        ds = np.sqrt( np.sum(rs*rs) )
        self.pix_distance.append(ds)
        # scale the x-axis
        # use a NumberDialog to get calibration data
        # parameter keys
        pkeys=['Real (world units) x1:','Real (world units) x2:' ]
        # current data to be shown in the dialog
        data = {pkeys[0]:"%d"%(self.start_pos[0]), \
                pkeys[1]:"%d"%(self.end_pos[0]), \
                }
        pdlg = NumberDialog(data, title="X-axis Calibration ", \
                            labels = pkeys, \
                            keys = pkeys, \
                            about_txt = "Enter the measured x-positions in world units")
        pdlg.exec_()
        pdlg.destroy()
        # now set the new parameters
        start_pos_world[0] = float(data[ pkeys[0] ])
        end_pos_world[0] = float(data[ pkeys[1] ])
        if self.log10x:
            start_pos_world[0] = np.log10(start_pos_world[0])
            end_pos_world[0] = np.log10(end_pos_world[0])
        cdx = end_pos_world[0] - start_pos_world[0]
        self.world_start_pos[0] = start_pos_world[0]
        self.world_end_pos[0] = end_pos_world[0]        
        # update calibration factor
        self.convx.append( cdx/dx)
        # calculate averaged calibration
        self.convx_av = ( np.array(self.convx) ).mean()
        # 
        self.cal_dx.append( cdx  )
        #
        # calculate real world  start and end positions
        # calculate offsets for the calibration
        xw_off =  (end_pos[0]*start_pos_world[0] - start_pos[0]*end_pos_world[0])/dx 
        self.xw_off.append(xw_off)
        self.xw_off_av = ( np.array(self.xw_off) ).mean()
        # create the text labels
        textx = self.get_text()
        text_posx = start_pos + 0.5*np.array([dx, 0.])
        textx.set_position(text_posx )
        #text.set_rotation(text_angle)
        textx.set_ha('center')
        textx.set_rotation_mode('anchor')
        textx.set_text("dx {0:6.1f}/{1:10.3e}".format(r[0],cdx) )
        # draw the text
        textx.set_animated(False)
        self.axes.draw_artist(textx)
        self.texts.append(textx)
        self.current_line.set_animated(False)
        self.canvas.blit(self.axes.bbox)
        # reset the calibration
        self.figure.canvas.draw()
        self.calibrate_off()
        self.update_status("idle")
        # store last image
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)
        self.button_release = True

    def process_y_calibration(self):
        # get offsets in real world values
        start_pos = np.array(self.start_pos)
        start_pos_world = np.zeros_like(start_pos)
        end_pos = np.array(self.end_pos)
        end_pos_world = np.zeros_like(end_pos)
        sc_start_pos = np.array(self.sc_start_pos)
        sc_end_pos = np.array(self.sc_end_pos)
        r = end_pos - start_pos
        rs = sc_end_pos - sc_start_pos
        d = np.sqrt( np.sum(r*r) )
        dy = r[1]
        self.distance.append(d)
        # same end point as starting point, give warning
        if d == 0.:
            self.warning( "Calibration Problem : Distance = 0.", \
                                 "You need to keep the mouse button pressed while dragging !")
            self.button_release = True
            return
        # use parameter
        self.dx.append(r[0])
        self.dy.append(r[1])
        ds = np.sqrt( np.sum(rs*rs) )
        self.pix_distance.append(ds)
        # scale the y-axis
        # current data to be shown in the dialog
        pkeys=['Real (world units) y1:','Real (world units) y2:' ]
        # current data to be shown in the dialog
        data = {pkeys[0]:"%d"%(self.start_pos[1]), \
            pkeys[1]:"%d"%(self.end_pos[1]), \
            }
        pdlg = NumberDialog(data, title="Y-axis Calibration ", \
                            labels = pkeys, \
                            keys = pkeys, \
                            about_txt = "Enter the measured y-positions in world units")
        pdlg.exec_()
        pdlg.destroy()
        # now set the new parameters
        start_pos_world[1] = float(data[ pkeys[0] ])
        end_pos_world[1] = float(data[ pkeys[1] ])
        if self.log10y:
            # take logarithm of distances
            start_pos_world[1] = np.log10(start_pos_world[1])
            end_pos_world[1] = np.log10(end_pos_world[1])
        cdy = end_pos_world[1] - start_pos_world[1]
        self.world_start_pos[1] = start_pos_world[1]
        self.world_end_pos[1] = end_pos_world[1]
        # update calibration factor
        self.convy.append( cdy/dy)
        # calculate averaged calibration
        self.convy_av = ( np.array(self.convy) ).mean()
        # 
        self.cal_dy.append( cdy  )
        # calculate offsets
        # calculate offsets for the calibration
        yw_off =  (end_pos[1]*start_pos_world[1] - start_pos[1]*end_pos_world[1])/dy 
        self.yw_off.append(yw_off)
        self.yw_off_av = ( np.array(self.yw_off) ).mean()        
        # create the text labels
        texty = self.get_text()
        text_posy = end_pos - 0.5*np.array([0., dy])
        texty.set_position(text_posy )
        #text.set_rotation(text_angle)
        texty.set_ha('right')
        texty.set_rotation_mode('anchor')
        texty.set_text("dy {0:6.1f}/{1:10.3e}".format(r[1],cdy) )
        # draw the text
        texty.set_animated(False)
        self.axes.draw_artist(texty)
        self.texts.append(texty)
        self.current_line.set_animated(False)
        self.canvas.blit(self.axes.bbox)
        # reset the calibration
        self.figure.canvas.draw()
        self.calibrate_off()
        self.update_status("idle")
        # store last image
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)
        self.button_release = True
        
    def process_measure(self):
        # get offsets in real world values
        start_pos = np.array(self.start_pos)
        end_pos = np.array(self.end_pos)
        sc_start_pos = np.array(self.sc_start_pos)
        sc_end_pos = np.array(self.sc_end_pos)
        r = end_pos - start_pos
        rs = sc_end_pos - sc_start_pos
        d = np.sqrt( np.sum(r*r) )
#        r_rot = np.array([-r[1], r[0]])
        dx = r[0]
        dy = r[1]
        # normalized distances
        dxn = dx/d
        dyn = dy/d
        #
        cdx = dx * self.convx_av 
        cdy = dy * self.convy_av
        cd = np.sqrt(cdx**2 + cdy**2)
        self.distance.append(d)
        # same end point as starting point, give warning
        if d == 0.:
            self.warning( "Distance = 0.", \
                                 "You need to keep the mouse button pressed while dragging !")
            self.button_release = False
            return
        # use parameter
        self.dx.append(r[0])
        self.dy.append(r[1])
        ds = np.sqrt( np.sum(rs*rs) )
        self.pix_distance.append(ds)
        # create the text labels
        textm = self.get_text()
        text_posm = start_pos + 0.5*np.array([dx, dy]) + 3*(self.font_size*np.array([dyn, -dxn]))
        # calculate the text angle (use pixel coords.)
        text_angle = 0.
        if ds != 0.:
            txt_sin = rs[1]/ds
            txt_cos = rs[0]/ds
            text_angle = angle(txt_sin,txt_cos)
        textm.set_position(text_posm )
        textm.set_rotation(text_angle * 180./np.pi)
        textm.set_ha('center')
        textm.set_linespacing(2.)
        textm.set_rotation_mode('anchor')
        s_string = "\nD = {0:10.3e}/{1:6.1f}".format(cd,d)
        textm.set_text( s_string)
        # draw the text
        self.axes.draw_artist(textm)
        self.texts.append(textm)
        self.canvas.blit(self.axes.bbox)
        # reset the 
        self.measure = False
        self.update_status("idle")
        # store last image
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)
        self.button_release = False
        

            
    def draw_marker(self, pos, n):
        # draw the n'th marker
        # draw a circle with a leader and the number n
        mx = pos[0]
        my = pos[1]
        # get offsets in real world values
        xmin,xmax = self.axes.get_xlim()
        ymin,ymax = self.axes.get_ylim()
        rx = xmax - xmin
        ry = ymax - ymin
        lpx = mx+self.dlx*rx
        lpy = my-self.dly*ry
        # the add text
        tpx = lpx + self.dtx*rx
        tpy = lpy - self.dty*ry
        text_string = "({0:d})".format(n)
        leader, text = self.get_marker()
        text.set_text(text_string)
        text.set_position( (tpx, tpy) )
        print("Marker:", mx, my, lpx, lpy, tpx, tpy)
        leader.set_data( [mx, lpx], [my, lpy])
        self.leaders.append(leader)
        self.texts.append(text)
        self.axes.draw_artist(leader)
        self.axes.draw_artist(text)
        self.canvas.blit(self.axes.bbox)


if __name__ == "__main__":
    app = QtCore.QCoreApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    frame = IAFrame(app)
    print("ready for work")
    # std
    sys.exit(app.exec_())

    
