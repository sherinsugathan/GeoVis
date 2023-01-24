from PyQt5 import QtWidgets as qWidget
from PyQt5 import QtGui as qGui
from PyQt5 import QtCore as qCore
from PyQt5.QtCore import pyqtSlot
from pathlib import Path

from PyQt5.QtWidgets import QFileDialog, QCheckBox, QButtonGroup, QAbstractButton, QVBoxLayout, QListWidgetItem, \
    QAbstractItemView, QSizePolicy
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QThread

qWidget.QApplication.setAttribute(qCore.Qt.AA_EnableHighDpiScaling, True)  # enable highdpi scaling
qWidget.QApplication.setAttribute(qCore.Qt.AA_UseHighDpiPixmaps, True)  # use highdpi icons

from PyQt5 import uic, Qt
from PyQt5.QtGui import QColor
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys
import vtk

vtk.vtkObject.GlobalWarningDisplayOff()
import os
import ctypes
import modules.utils as Utils
import modules.gradient as Gd
import matplotlib
#import matplotlib.colorsp


from netCDF4 import Dataset
import netCDF4 as nc
from netCDF4 import num2date, date2num, date2index
import folium
import io
import xarray as xr

# Pyinstaller exe requirements
# import pkg_resources.py2_warn
import vtkmodules
import vtkmodules.all
import vtkmodules.qt.QVTKRenderWindowInteractor
import vtkmodules.util
import vtkmodules.util.numpy_support
if os.name == 'nt':
    import cftime
    import cftime._strptime
    myappid = 'uio.geovis.netcdfvisualizer.100' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

class mainWindow(qWidget.QMainWindow):
    """Main window class."""

    def __init__(self, *args):
        """Init."""
        super(mainWindow, self).__init__(*args)
        self.path = None
        self.rawTimes = []
        self.pa = None
        self.cmaps = None
        self.currentTimeStep = None
        self.animationDirection = 1
        self.actualTimeStrings = None
        self.IsTemporalDataset = False
        self.maxTimeSteps = None
        # set app icon
        app_icon = qGui.QIcon()
        app_icon.addFile('assets/icons/icons8-92.png', qCore.QSize(92, 92))
        app_icon.addFile('assets/icons/icons8-100.png', qCore.QSize(100, 100))
        app_icon.addFile('assets/icons/icons8-200.png', qCore.QSize(200, 200))
        app_icon.addFile('assets/icons/icons8-400.png', qCore.QSize(400, 400))
        self.setWindowIcon(app_icon)
        ui = os.path.join(os.path.dirname(__file__), 'assets/ui/gui.ui')
        uic.loadUi(ui, self)

    def setupUI(self):
        print("Starting application...")
        self.initializeRenderer()
        self.pushButton_LoadDataset.clicked.connect(self.on_buttonClick)  # Attaching button click handler.
        self.pushButton_SetDimensions.clicked.connect(self.on_buttonClick)  # Attaching button click handler.
        self.pushButton_PlayReverse.clicked.connect(self.on_buttonClick)  # Attaching button click handler.
        self.pushButton_PreviousFrame.clicked.connect(self.on_buttonClick)  # Attaching button click handler.
        self.pushButton_Pause.clicked.connect(self.on_buttonClick)  # Attaching button click handler.
        self.pushButton_NextFrame.clicked.connect(self.on_buttonClick)  # Attaching button click handler.
        self.pushButton_PlayForward.clicked.connect(self.on_buttonClick)  # Attaching button click handler.
        self.comboBox_dims.currentTextChanged.connect(self.on_comboboxDims_changed)  # Changed dimensions handler.

        # View radio buttons
        self.radioButton_RawView.toggled.connect(self.changeView)
        #self.radioButton_2DView.toggled.connect(self.changeView)
        self.radioButton_3DView.toggled.connect(self.changeView)

        # Variable list double click
        self.listWidget_Variables.doubleClicked.connect(self.applyVariable)

        # time slider
        self.horizontalSlider_Main.valueChanged.connect(self.on_timeSlider_Changed)

        # Log scale
        self.checkBox_LogScale.stateChanged.connect(self.on_scaleChanged)
        self.progbar()

        self.myLongTask = TaskThread(self, isRefresh=True)  # initializing and passing data to QThread
        self.myLongTask.taskFinished.connect(self.onFinished)  # this won't be read until QThread send a signal i think
        self.myDimensionUpdateTask = TaskThread(self, isRefresh=False)  # initializing and passing data to QThread
        self.myDimensionUpdateTask.taskFinished.connect(self.onFinished)  # this won't be read until QThread send a signal i think

        self.initializeApp()


    @pyqtSlot()
    def on_scaleChanged(self):
        if(self.checkBox_LogScale.isChecked()==True):
            self.ctf.SetScaleToLog10()
        else:
            self.ctf.SetScaleToLinear()
        self.ctf.Build()
        self.mapper.SetLookupTable(self.ctf)
        self.mapper.Update()
        self.iren.Render()


    @pyqtSlot()
    def applyVariable(self):
        # scalarVariables = [item.text() for item in self.listWidget_Variables.selectedItems()]
        # print(scalarVariables)
        self.varName = self.listWidget_Variables.currentItem().text()

        self.fmt = qGui.QTextCharFormat()
        self.cursor = qGui.QTextCursor(self.plainTextEdit_netCDFDataText.document())
        self.cursor.select(qGui.QTextCursor.Document)
        self.cursor.setCharFormat(qGui.QTextCharFormat()) # Clear existing selections
        self.cursor.clearSelection()

        pattern = "Name:" + str(self.varName)
        regex = qCore.QRegExp(pattern)
        pos = 0
        index = regex.indexIn(self.plainTextEdit_netCDFDataText.document().toPlainText(), pos)
        if(index != -1):
            self.cursor.setPosition(index,qGui.QTextCursor.MoveAnchor)
            self.cursor.setPosition(index + len(pattern), qGui.QTextCursor.KeepAnchor)
            self.plainTextEdit_netCDFDataText.ensureCursorVisible()
            #cursor.movePosition(qGui.QTextCursor.End, qGui.QTextCursor.MoveAnchor, 1)
            self.cursor.setCharFormat(self.fmt)
            self.plainTextEdit_netCDFDataText.setTextCursor(self.cursor)
            self.plainTextEdit_netCDFDataText.textCursor().clearSelection()

        Utils.updateGlobeGeometry(self, self.varName)
        Utils.variableControlsSetVisible(self, True)
        Utils.statusMessage(self, "Active: " + self.varName, "success")

    @pyqtSlot()
    def changeView(self):
        rbtn = self.sender()
        if (rbtn.isChecked() == True):
            if (rbtn.text() == "Raw"):
                self.stackedWidget.setCurrentWidget(self.page_InspectData)
            ############################
            # 2D Render View
            ############################
            if (rbtn.text() == "2D"):
                self.stackedWidget.setCurrentWidget(self.page_2DMap)
                layout = QVBoxLayout()
                self.frame_2D.setLayout(layout)
                coordinate = (37.8199286, -122.4782551)
                m = folium.Map(
                    tiles='cartodbpositron',
                    zoom_start=13,
                    location=coordinate, zoom_control=False
                )
                # save map data to data object
                data = io.BytesIO()
                m.save(data, close_file=False)
                # Enable the following two lines when 2D maps are required.
                #self.webView.setHtml(data.getvalue().decode())
                #layout.addWidget(self.webView)
            ############################
            # 3D Render View
            ############################
            if (rbtn.text() == "3D"):
                self.stackedWidget.setCurrentWidget(self.page_3DMap)

    @pyqtSlot()
    def on_timeSlider_Changed(self):
        self.currentTimeStep = self.horizontalSlider_Main.value()
        if(self.IsTemporalDataset == True):
            self.textActor.SetInput(str(self.actualTimeStrings[self.currentTimeStep]))
        self.reader.GetOutputInformation(0).Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(), self.rawTimes[self.currentTimeStep - 1])
        self.pa.AddArray(1, self.varName)  # 0 for PointData, 1 for CellData, 2 for FieldData
        self.pa.Update()
        self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetAbstractArray(self.varName))
        #self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetArray(0))
        self.label_FrameStatus.setText(str(self.currentTimeStep) + "/" + str(self.maxTimeSteps))
        self.iren.Render()

    @pyqtSlot()
    def on_comboboxDims_changed(self):
        selectedDimension = str(self.comboBox_dims.currentText())
        # self.reader.ComputeArraySelection()
        # self.reader.SetDimensions(selectedDimension)
        dimNames = self.reader.GetVariableDimensions()
        varNames = self.reader.GetAllVariableArrayNames()
        dimNamesList = []
        varNamesList = []
        for i in range(dimNames.GetNumberOfValues()):
            dimNamesList.append(str(dimNames.GetValue(i)))
        for i in range(varNames.GetNumberOfValues()):
            varNamesList.append(str(varNames.GetValue(i)))
        index_pos_list = [i for i in range(len(dimNamesList)) if dimNamesList[i] == selectedDimension]
        visVarList = []  # Variables of interest
        for indexLocation in index_pos_list:
            visVarList.append(self.reader.GetVariableArrayName(indexLocation))

        # Update variable list
        self.listWidget_Variables.clear()
        for i in range(len(visVarList)):
            item = QListWidgetItem(str(visVarList[i]))
            # item.setFlags(item.flags() | qCore.Qt.ItemIsUserCheckable)
            # item.setCheckState(qCore.Qt.Unchecked)
            self.listWidget_Variables.addItem(item)

    @pyqtSlot()
    def comboBox_ColorMaps_changed(self):
        for cmapItem in self.cmaps:
            if(cmapItem['name'] == str(self.comboBox_ColorMaps.currentText())):
                color1List = [int(x) for x in cmapItem['color1'].split(',')]
                color2List = [int(x) for x in cmapItem['color2'].split(',')]
                gradientList = []
                cstart = (0, QColor(color1List[0], color1List[1], color1List[2], color1List[3]))
                cend = (1, QColor(color2List[0], color2List[1], color2List[2], color2List[3]))
                stops = cmapItem['stops'].split(':')
                gradientList.append(cstart)
                for item in stops:
                    stopData = item.split(';')
                    stop = float(stopData[0])
                    cvalues = [int(x) for x in stopData[1].split(',')]
                    gradientList.append((stop, QColor(cvalues[0], cvalues[1], cvalues[2], cvalues[3])))
                gradientList.append(cend)
                self.gradient.setGradient(gradientList)
                self.gradient.update()
                break

    @pyqtSlot()
    def updateLUT(self):
        #print("updating lut")
        gradients = self.gradient.gradient()
        dataRange = self.mapper.GetInput().GetCellData().GetScalars(self.varName).GetRange()
        stops = [data[0] for data in gradients]
        oldMin = 0
        oldMax = 1
        newMin = dataRange[0]
        newMax = dataRange[1]
        newRange = newMax - newMin

        self.ctf.RemoveAllPoints()
        for gradient in gradients:
            #print(type(gradient[1]))
            oldValue = float(gradient[0])
            newValue = ((oldValue - oldMin) * newRange) + newMin
            if(isinstance(gradient[1], str)==True):
                 rgb = matplotlib.colors.to_rgb(gradient[1])
                 self.ctf.AddRGBPoint(newValue, rgb[0], rgb[1], rgb[2])
            else:
                self.ctf.AddRGBPoint(newValue, gradient[1].redF(), gradient[1].greenF(), gradient[1].blueF())
        self.ctf.Build()
        self.mapper.Update()
        self.iren.Render()

    # Handler for browse folder button click.
    @pyqtSlot()
    def initializeRenderer(self):
        self.vl = Qt.QVBoxLayout()
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.vl.addWidget(self.vtkWidget)
        self.ren = vtk.vtkRenderer()
        self.ren.SetBackground(33 / 255.0, 37.0 / 255, 43.0 / 255)
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        #self.vtkWidget.GetRenderWindow().SetMultiSamples(4)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        self.actor_style = vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(self.actor_style)

        self.iren.SetRenderWindow(self.vtkWidget.GetRenderWindow())
        #self.ren.UseFXAAOn()
        self.ren.ResetCamera()
        self.frame.setLayout(self.vl)
        self.iren.Initialize()
        # Sign up to receive TimerEvent
        #cb = vtkTimerCallback(1, self.iren)
        #self.iren.AddObserver('TimerEvent', cb.execute)
        #cb.timerId = self.iren.CreateRepeatingTimer(500)

        self.iren.Render()
        self.ren.Render()

        self.timer = qCore.QTimer()
        self.timer.timeout.connect(self.onTimerEvent)
        #self.timer.start(100)

        # web view
        #self.webView = QWebEngineView()
        print("Renderer Initialized.")

    def onTimerEvent(self):
        if (self.stackedWidget.currentWidget().objectName() == "page_3DMap" or self.stackedWidget.currentWidget().objectName() == "page_2DMap"):
            if(self.animationDirection == -1):
                if (self.currentTimeStep > 1):
                    self.currentTimeStep = self.currentTimeStep - 1
                else:
                    self.currentTimeStep = self.maxTimeSteps
            else:
                if (self.currentTimeStep < self.maxTimeSteps):
                    self.currentTimeStep = self.currentTimeStep + 1
                else:
                    self.currentTimeStep = 1
            self.reader.GetOutputInformation(0).Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(), self.rawTimes[self.currentTimeStep - 1])
            self.pa.AddArray(1, self.varName)  # 0 for PointData, 1 for CellData, 2 for FieldData
            self.pa.Update()
            if (self.IsTemporalDataset == True):
                self.textActor.SetInput(str(self.actualTimeStrings[self.currentTimeStep-1]))
            self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetAbstractArray(self.varName))
            # self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetArray(0))
            self.label_FrameStatus.setText(str(self.currentTimeStep) + "/" + str(self.maxTimeSteps))
            self.iren.Render()

    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)
        self.vtkWidget.Finalize()

    def initializeApp(self):
        self.pa = vtk.vtkPassArrays()
        self.gradient = Gd.Gradient()
        self.gradient.setGradient([(0, 'black'), (1, 'green'), (0.5, 'red')])
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.gradient, qCore.Qt.AlignCenter)
        self.frame_colormap.setLayout(self.layout)
        # Read color map information.
        self.cmaps = Utils.readColorMapInfo(self, "assets//colormaps//colormaps.xml")
        for item in self.cmaps:
            self.comboBox_ColorMaps.addItem(item['name'])
        color1List = [int(x) for x in self.cmaps[0]['color1'].split(',')]
        color2List = [int(x) for x in self.cmaps[0]['color2'].split(',')]
        gradientList = []
        cstart = (0, QColor(color1List[0],color1List[1], color1List[2], color1List[3]))
        cend = (1, QColor(color2List[0], color2List[1], color2List[2], color2List[3]))
        stops = self.cmaps[0]['stops'].split(':')
        gradientList.append(cstart)
        for item in stops:
            stopData = item.split(';')
            stop = float(stopData[0])
            cvalues = [int(x) for x in stopData[1].split(',')]
            gradientList.append((stop, QColor(cvalues[0], cvalues[1], cvalues[2], cvalues[3])))
        gradientList.append(cend)
        self.gradient.setGradient(gradientList)
        self.comboBox_ColorMaps.currentTextChanged.connect(self.comboBox_ColorMaps_changed)  # Changed dimensions handler.
        self.gradient.gradientChanged.connect(self.colorMapChanged)

        # Disable all data controls when mainwindow loads.
        Utils.controlsSetVisible(self, False)


    # Visualization color map changed.
    def colorMapChanged(self):
        self.updateLUT()

    # Reset UI state when loading dataset.
    def resetUI(self):
        pass

    def progbar(self):
        self.layout = QVBoxLayout()
        self.prog_win = qWidget.QDialog()
        self.prog_win.resize(500, 300)
        self.prog_win.setModal(True)
        self.prog_win.setWindowFlags(qCore.Qt.FramelessWindowHint)
        self.prog_win.setFixedSize(self.prog_win.size())
        self.prog_win.setWindowTitle("Processing request")
        stylesheet = "border: 2px solid rgb(52, 59, 72);border-radius: 5px;	background-color: rgb(52, 59, 72);color:rgb(175, 199, 242);"
        self.prog_win.setStyleSheet(stylesheet)

        self.lbl = qWidget.QLabel(self.prog_win)
        self.lbl.setAlignment(qCore.Qt.AlignCenter)
        self.lbl.setStyleSheet("font: 12pt Arial;")
        self.lbl.setText("Processing data... Please wait...")
        # self.lbl.move(15,18)
        self.progressBar = qWidget.QProgressBar(self.prog_win)
        # self.progressBar.resize(410, 25)
        self.progressBar.setMaximum(0)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximumHeight(15)
        self.progressBar.setStyleSheet("background-color: rgb(90, 102, 125); border-radius: 2px;")
        # self.progressBar.move(15, 40)

        self.layout.addWidget(self.lbl, qCore.Qt.AlignCenter)
        self.layout.addWidget(self.progressBar, qCore.Qt.AlignCenter)

        # widget = QWidget()
        self.prog_win.setLayout(self.layout)
        # self.setCentralWidget(self.prog_win)
        # self.progressBar.setRange(0,1)

    def onStart(self, reload=True):
        # self.progressBar.setRange(0,0)
        if (reload == True):
            self.myLongTask.start()
        else:
            self.myDimensionUpdateTask.start()

    # added this function to close the progress bar
    def onFinished(self):
        # self.progressBar.setRange(0,1)
        self.prog_win.close()
        for item in self.dataDimensions:
            self.comboBox_dims.addItem(item)
        self.plainTextEdit_netCDFDataText.setPlainText(self.str_data)

        if (self.rawTimes != None): # valid time points available.
            self.maxTimeSteps = len(self.rawTimes)
            self.label_FrameStatus.setText("1/" + str(self.maxTimeSteps))
            self.horizontalSlider_Main.setMaximum(self.maxTimeSteps-1)
            self.horizontalSlider_Main.setEnabled(True)
        else: # no time points available
            self.maxTimeSteps = 1
            self.horizontalSlider_Main.setEnabled(False)
            self.label_FrameStatus.setText("1/1")
        self.currentTimeStep = 1
        # self.stackedWidget.setCurrentWidget(self.page_InspectData)
        Utils.statusMessage(self, "Data loaded.", "success")
        # Enable all data controls
        Utils.controlsSetVisible(self, True)

    # Handler for browse folder button click.
    @pyqtSlot()
    def on_buttonClick(self):
        btn = self.sender()
        btnName = btn.objectName()

        ###########################
        # Browse NetCDF data button
        ############################
        if btnName == "pushButton_LoadDataset":
            path = QFileDialog.getOpenFileName(self, 'Open a file', '', 'NetCDF files (*.nc)')
            if path != ('', ''):
                self.radioButton_RawView.setChecked(True)
                self.path = path[0]
                self.prog_win.show()

                self.comboBox_dims.clear()  # clear dim var combobox
                self.listWidget_Variables.clear()  # clear variable list.

                self.prog_win.show()
                self.onStart()  # Start your very very long computation/process

        ############################
        # Apply selected variables.
        ############################
        if btnName == "pushButton_SetDimensions":
            # print("need to something here to regrid the data based on selected dimensions.")
            #print("Setting dimensions to ", self.comboBox_dims.currentText())
            self.comboBox_dims.clear()
            self.listWidget_Variables.clearSelection()
            self.reader.SetDimensions(self.comboBox_dims.currentText())
            self.reader.ComputeArraySelection()
            self.prog_win.show()
            self.onStart(False)  # Start your very very long computation/process
            # Utils.loadGlobeGeometry(self)
            # self.reader.Update()disc
            # self.mapper.Update()

            # self.reader.Update()
            # print("NUmber of var array is ", self.reader.GetNumberOfVariableArrays())
            # print(selectedDimension)

            # selectedVariables = []
            # #print("count is", self.listWidget_Variables.count())
            # for index in range(self.listWidget_Variables.count()):
            #     if(self.listWidget_Variables.item(index).isSelected() == True):
            #         selectedVariables.append(self.listWidget_Variables.item(index).text())
            # #print(selectedVariables)
            # # Update vis params list
            # self.listWidget_VisParams.clear()
            # for i in range(len(selectedVariables)):
            #     item = QListWidgetItem(str(selectedVariables[i]))
            #     #item.setFlags(item.flags() | qCore.Qt.ItemIsUserCheckable)
            #     #item.setCheckState(qCore.Qt.Unchecked)
            #     self.listWidget_VisParams.addItem(item)
            #
            # self.tabWidget.setCurrentIndex(1)
            # self.stackedWidget.setCurrentWidget(self.page_3DMap)

        ############################
        # Play Reverse
        ############################
        if btnName == "pushButton_PlayReverse":
            if (self.maxTimeSteps != 1):
                self.animationDirection = -1
                if(self.timer.isActive() == False):
                    self.timer.start()

        ############################
        # Previous Frame
        ############################
        if btnName == "pushButton_PreviousFrame":
            if (self.maxTimeSteps == 1):
                return
            if (self.stackedWidget.currentWidget().objectName() == "page_3DMap" or self.stackedWidget.currentWidget().objectName() == "page_2DMap"):
                if (self.currentTimeStep > 1):
                    self.currentTimeStep = self.currentTimeStep - 1
                else:
                    self.currentTimeStep = self.maxTimeSteps
                self.reader.GetOutputInformation(0).Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(), self.rawTimes[self.currentTimeStep - 1])
                if (self.IsTemporalDataset == True):
                    self.textActor.SetInput(str(self.actualTimeStrings[self.currentTimeStep-1]))
                self.pa.AddArray(1, self.varName)  # 0 for PointData, 1 for CellData, 2 for FieldData
                self.pa.Update()
                self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetAbstractArray(self.varName))
                #self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetArray(0))
                self.label_FrameStatus.setText(str(self.currentTimeStep) + "/" + str(self.maxTimeSteps))
                self.iren.Render()

        ############################
        # Pause
        ############################
        if btnName == "pushButton_Pause":
            #print("pause playback")
            self.timer.stop()

        ############################
        # Next frame
        ############################
        if btnName == "pushButton_NextFrame":
            if(self.maxTimeSteps == 1):
                return
            if (self.stackedWidget.currentWidget().objectName() == "page_3DMap" or self.stackedWidget.currentWidget().objectName() == "page_2DMap"):
                if(self.currentTimeStep < self.maxTimeSteps):
                    self.currentTimeStep = self.currentTimeStep + 1
                else:
                    self.currentTimeStep = 1

                self.reader.GetOutputInformation(0).Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(), self.rawTimes[self.currentTimeStep - 1])
                self.pa.AddArray(1, self.varName)  # 0 for PointData, 1 for CellData, 2 for FieldData
                self.pa.Update()
                if (self.IsTemporalDataset == True):
                    self.textActor.SetInput(str(self.actualTimeStrings[self.currentTimeStep-1]))
                self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetAbstractArray(self.varName))
                #self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetArray(0))
                self.mapper.GetInput().GetCellData().SetActiveScalars(self.varName)
                self.label_FrameStatus.setText(str(self.currentTimeStep) + "/" + str(self.maxTimeSteps))
                #self.mapper.Update()
                self.iren.Render()

        ############################
        # Play forward
        ############################
        if btnName == "pushButton_PlayForward":
            if(self.maxTimeSteps != 1):
                self.animationDirection = 1
                if (self.timer.isActive() == False):
                    self.timer.start()

    
    def closeEvent(self, event):
        self.timer.stop()
        sys.exit()

##############################################################################
################# Data Reader Thread
##############################################################################
class TaskThread(qCore.QThread):
    taskFinished = qCore.pyqtSignal()

    # I also added this so that I can pass data between classes
    def __init__(self, mainObject, isRefresh, parent=None):
        QThread.__init__(self, parent)
        self.main = mainObject
        self.isRefresh = isRefresh

    def run(self):
        if (self.isRefresh == True):
            print("Processing NetCDF file")
            nc_fid = Dataset(self.main.path, 'r')  # Dataset is the class behavior to open the file
            nc_attrs, nc_dims, nc_vars, self.main.str_data = Utils.ncdump(nc_fid)
            if('time' in nc_fid.variables):
                sfctmp = nc_fid.variables['time']
                timedim = sfctmp.dimensions[0]  # time dim name
                times = nc_fid.variables[timedim]
                dates = num2date(times[:], times.units)
                self.main.actualTimeStrings = [date.strftime('%Y-%m-%d %H:%M:%S') for date in dates[:]]
                self.main.IsTemporalDataset = True
            else:
                self.main.IsTemporalDataset = False
            # Reader NETCDF
            self.main.reader = vtk.vtkNetCDFCFReader()
            self.main.reader.SetFileName(self.main.path)
            self.main.reader.UpdateMetaData()
            # reader.SetVariableArrayStatus("w", 1)
            self.main.reader.SphericalCoordinatesOn()
            self.main.reader.ReplaceFillValueWithNanOn()
            self.main.dataDimensions = []
            allDimensions = self.main.reader.GetAllDimensions()
            for i in range(allDimensions.GetNumberOfValues()):
                dimension = allDimensions.GetValue(i)
                self.main.dataDimensions.append(dimension)

        self.main.pa.SetInputConnection(self.main.reader.GetOutputPort())
        Utils.loadGlobeGeometry(self.main)
        if(self.main.IsTemporalDataset == True):
            Utils.loadOverlay(self.main, self.main.actualTimeStrings)
        self.main.rawTimes = self.main.reader.GetOutputInformation(0).Get(vtk.vtkStreamingDemandDrivenPipeline.TIME_STEPS())

        # tunits = self.main.reader.GetTimeUnits()

        # print("RAW TIMES:", self.main.rawTimes)
        self.taskFinished.emit()

app = qWidget.QApplication(sys.argv)
window = mainWindow()
window.setupUI()
window.show()

window.showMaximized()
sys.exit(app.exec_())
