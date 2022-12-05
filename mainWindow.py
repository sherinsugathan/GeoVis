from PyQt5 import QtWidgets as qWidget
from PyQt5 import QtGui as qGui
from PyQt5 import QtCore as qCore
from PyQt5.QtCore import pyqtSlot

from PyQt5.QtWidgets import QFileDialog, QCheckBox, QButtonGroup, QAbstractButton, QVBoxLayout, QListWidgetItem, \
    QAbstractItemView, QSizePolicy
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QThread

qWidget.QApplication.setAttribute(qCore.Qt.AA_EnableHighDpiScaling, True)  # enable highdpi scaling
qWidget.QApplication.setAttribute(qCore.Qt.AA_UseHighDpiPixmaps, True)  # use highdpi icons

from PyQt5 import uic, Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys
import vtk

vtk.vtkObject.GlobalWarningDisplayOff()
import os
import modules.utils as Utils
from netCDF4 import Dataset
import netCDF4 as nc
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
import cftime
import cftime._strptime


class mainWindow(qWidget.QMainWindow):
    """Main window class."""

    def __init__(self, *args):
        """Init."""
        super(mainWindow, self).__init__(*args)
        self.path = None
        self.rawTimes = []
        self.currentTimeStep = None
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
        self.radioButton_2DView.toggled.connect(self.changeView)
        self.radioButton_3DView.toggled.connect(self.changeView)

        # Variable list double click
        self.listWidget_Variables.doubleClicked.connect(self.applyVariable)

        Utils.populateSupportedColorMaps(self)
        self.progbar()

        self.myLongTask = TaskThread(self, isRefresh=True)  # initializing and passing data to QThread
        self.myLongTask.taskFinished.connect(self.onFinished)  # this won't be read until QThread send a signal i think
        self.myDimensionUpdateTask = TaskThread(self, isRefresh=False)  # initializing and passing data to QThread
        self.myDimensionUpdateTask.taskFinished.connect(
            self.onFinished)  # this won't be read until QThread send a signal i think

        # self.horizontalSlider_start.valueChanged.connect(self.onsliderminChanged)
        # self.horizontalSlider_end.valueChanged.connect(self.onslidermaxChanged)

    @pyqtSlot()
    def applyVariable(self):
        # scalarVariables = [item.text() for item in self.listWidget_Variables.selectedItems()]
        # print(scalarVariables)
        varName = self.listWidget_Variables.currentItem().text()
        Utils.updateGlobeGeometry(self, varName)

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

                self.webView.setHtml(data.getvalue().decode())
                layout.addWidget(self.webView)
            ############################
            # 3D Render View
            ############################
            if (rbtn.text() == "3D"):
                self.stackedWidget.setCurrentWidget(self.page_3DMap)

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
    def updateLUT(self, newValue):
        self.ctf.RemoveAllPoints()
        self.ctf.AddRGBPoint(-1018.2862548828125, 0.231373, 0.298039, 0.752941)
        self.ctf.AddRGBPoint(newValue, 0.865003, 0.865003, 0.865003)
        self.ctf.AddRGBPoint(3747.783203125, 0.705882, 0.0156863, 0.14902)
        self.ctf.Build()
        self.mapper.Update()
        self.iren.Render()

    @pyqtSlot()
    def onsliderminChanged(self):
        self.valueStart = self.horizontalSlider_start.value()
        newValue = ((self.valueStart * 4765) / 2382) - 1018
        self.updateLUT(newValue)
        # print("start changing", self.newValue)

    @pyqtSlot()
    def onslidermaxChanged(self):
        self.valueEnd = self.horizontalSlider_end.value()
        print("end changing")

    @pyqtSlot()
    def on_click_printHello(self):
        print("Hello Sherin!")

    # Handler for browse folder button click.
    @pyqtSlot()
    def initializeRenderer(self):
        self.vl = Qt.QVBoxLayout()
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.vl.addWidget(self.vtkWidget)
        self.ren = vtk.vtkRenderer()
        self.ren.SetBackground(5 / 255.0, 10.0 / 255, 38.0 / 255)
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        self.actor_style = vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(self.actor_style)

        self.iren.SetRenderWindow(self.vtkWidget.GetRenderWindow())
        self.ren.ResetCamera()
        self.frame.setLayout(self.vl)
        self.iren.Initialize()
        # web view
        self.webView = QWebEngineView()
        print("Renderer Initialized.")

    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)
        self.vtkWidget.Finalize()

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
        print("Task started")

    # added this function to close the progress bar
    def onFinished(self):
        # self.progressBar.setRange(0,1)
        self.prog_win.close()
        for item in self.dataDimensions:
            self.comboBox_dims.addItem(item)
        self.plainTextEdit_netCDFDataText.setPlainText(self.str_data)
        if (self.rawTimes != None):
            self.maxTimeSteps = len(self.rawTimes)
            self.label_FrameStatus.setText("1/" + str(self.maxTimeSteps))
            self.currentTimeStep = 0
        # self.stackedWidget.setCurrentWidget(self.page_InspectData)
        Utils.statusMessage(self, "Data loaded.", "success")

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
            print("Setting dimensions to ", self.comboBox_dims.currentText())
            self.reader.SetDimensions(self.comboBox_dims.currentText())
            self.reader.ComputeArraySelection()
            self.prog_win.show()
            self.onStart(False)  # Start your very very long computation/process
            # Utils.loadGlobeGeometry(self)
            # self.reader.Update()
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
            print("play reverse")

        ############################
        # Previous Frame
        ############################
        if btnName == "pushButton_PreviousFrame":
            if (self.stackedWidget.currentWidget().objectName() == "page_3DMap" or self.stackedWidget.currentWidget().objectName() == "page_2DMap"):
                print("previous frame")

        ############################
        # Pause
        ############################
        if btnName == "pushButton_Pause":
            print("pause playback")

        ############################
        # Next frame
        ############################
        if btnName == "pushButton_NextFrame":
            if (self.stackedWidget.currentWidget().objectName() == "page_3DMap" or self.stackedWidget.currentWidget().objectName() == "page_2DMap"):
                print("next frame")
                if(self.currentTimeStep < self.maxTimeSteps):
                    #print("Current step is ", self.rawTimes[self.currentTimeStep])
                    self.reader.GetOutputInformation(0).Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(), self.rawTimes[self.currentTimeStep])
                    self.mapper.Update()
                    self.iren.Render()
                    self.currentTimeStep = self.currentTimeStep + 1
                else:
                    self.currentTimeStep = 0



                #
                #print("here")

        ############################
        # Play forward
        ############################
        if btnName == "pushButton_PlayForward":
            print("play forward")

##############################################################################
################# Data Reader Thread
##############################################################################
# My Thread
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

        Utils.loadGlobeGeometry(self.main)
        self.main.rawTimes = self.main.reader.GetOutputInformation(0).Get(
            vtk.vtkStreamingDemandDrivenPipeline.TIME_STEPS())
        # tunits = self.main.reader.GetTimeUnits()

        # print("RAW TIMES:", self.main.rawTimes)
        self.taskFinished.emit()


app = qWidget.QApplication(sys.argv)
window = mainWindow()
window.setupUI()
window.show()

window.showMaximized()
sys.exit(app.exec_())
