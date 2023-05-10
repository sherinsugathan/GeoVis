from PyQt5 import QtWidgets as qWidget
from PyQt5 import QtGui as qGui
from PyQt5 import QtCore as qCore
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from pathlib import Path

from PyQt5.QtWidgets import (
    QFileDialog,
    QCheckBox,
    QMessageBox,
    QButtonGroup,
    QAbstractButton,
    QVBoxLayout,
    QListWidgetItem,
    QAbstractItemView,
    QSizePolicy,
)
#from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QInputDialog, QErrorMessage

qWidget.QApplication.setAttribute(
    qCore.Qt.AA_EnableHighDpiScaling, True
)  # enable highdpi scaling
qWidget.QApplication.setAttribute(
    qCore.Qt.AA_UseHighDpiPixmaps, True
)  # use highdpi icons

from PyQt5 import uic, Qt
from PyQt5.QtGui import QColor
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys
import vtk

vtk.vtkObject.GlobalWarningDisplayOff()
import os
import time
import ctypes
import modules.utils as Utils
import modules.gradient as Gd
import matplotlib
import xml.etree.ElementTree as ET
import numpy as np
import vtkplotlib as vpl

# import matplotlib.colorsp


from netCDF4 import Dataset
import netCDF4 as nc
from netCDF4 import num2date, date2num, date2index

# import folium
import io
import xarray as xr

# Pyinstaller exe requirements
# import pkg_resources.py2_warn
import vtkmodules
import vtkmodules.all
import vtkmodules.qt.QVTKRenderWindowInteractor
import vtkmodules.util
import vtkmodules.util.numpy_support

if os.name == "nt":
    import cftime
    import cftime._strptime

    myappid = "uio.geovis.netcdfvisualizer.100"  # arbitrary string
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
        self.cmapFile = os.path.join(os.path.dirname(__file__), "assets/colormaps/colormaps.xml")
        self.cmapDefaultFile = os.path.join(os.path.dirname(__file__), "assets/colormaps/colormapsDefault.xml")
        self.currentTimeStep = None
        self.animationDirection = 1
        self.actualTimeStrings = None
        self.IsTemporalDataset = False
        self.maxTimeSteps = None
        self.newMin = None
        self.newMax = None
        self.newMinContours = None
        self.newMaxContours = None
        self.dataRange = None
        self.varName = None
        self.contourVarName = None
        self.videoExportFolderName = None
        self.contActor = None
        self.update
        # set app icon
        app_icon = qGui.QIcon()
        app_icon.addFile(os.path.join(os.path.dirname(__file__), "assets/icons/geo.png"), qCore.QSize(80, 80))
        self.setWindowIcon(app_icon)
        ui = os.path.join(os.path.dirname(__file__), "assets/ui/gui.ui")

        uic.loadUi(ui, self)

    def setupUI(self):
        print("Starting application...")
        print("Please note that the application may take some time to start. So please be patient and wait...")
        self.initializeRenderer()
        self.pushButton_LoadDataset.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_SetDimensions.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_PlayReverse.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_PreviousFrame.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_Pause.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_NextFrame.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_PlayForward.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_UpdateRange.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_ResetRange.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_ExportImage.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_ExportVideo.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_SaveColorMap.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_RemoveColormap.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_RestoreDefaultColormaps.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.pushButton_Export3DModel.clicked.connect(
            self.on_buttonClick
        )  # Attaching button click handler.
        self.dial_videoQuality.valueChanged.connect(self.on_videoQualityUpdate)
        self.dial_videoFrameRate.valueChanged.connect(self.on_frameRateUpdate)
        self.comboBox_dims.currentTextChanged.connect(
            self.on_comboboxDims_changed
        )  # Changed dimensions handler.

        # View radio buttons
        self.radioButton_RawView.toggled.connect(self.changeView)
        # self.radioButton_2DView.toggled.connect(self.changeView)
        self.radioButton_3DView.toggled.connect(self.changeView)

        # Variable list double click
        self.listWidget_Variables.doubleClicked.connect(self.applyVariable)
        #self.listWidget_Variables.setSelectionMode(QAbstractItemView.NoSelection)
        #self.listWidget_Variables.setSelectionMode(QAbstractItemView.NoSelection)

        # time slider
        self.horizontalSlider_Main.valueChanged.connect(self.on_timeSlider_Changed)

        # Contour thickness updated
        self.spinBox_ContourThickness.valueChanged.connect(self.on_contourThicknessUpdated)

        # Log scale
        self.checkBox_LogScale.stateChanged.connect(self.on_scaleChanged)
        self.progbar()

        # View mode radio buttons
        self.radioButton_ColorMode.toggled.connect(self.on_colorModeSelected)
        self.radioButton_ContourMode.toggled.connect(self.on_contourModeSelected)

        self.myLongTask = TaskThread(
            self, isRefresh=True
        )  # initializing and passing data to QThread
        self.myLongTask.taskFinished.connect(
            self.onFinished
        )  # this won't be read until QThread send a signal i think
        self.myDimensionUpdateTask = TaskThread(
            self, isRefresh=False
        )  # initializing and passing data to QThread
        self.myDimensionUpdateTask.taskFinished.connect(
            self.onFinished
        )  # this won't be read until QThread send a signal i think
        # self.videoExportTask = Utils.VideoTaskThread(self)
        # self.videoExportTask.taskFinished.connect(self.onFinishedVideoExport)

        logoImagePath = "assets/ui/logo.png"
        self.label_8.setStyleSheet("border-image: url(" + logoImagePath + ") 0 0 0 0 stretch stretch;border-radius: 0px;")
        self.horizontalSlider_Main.setVisible(False)
        self.initializeApp()

    @pyqtSlot()
    def on_contourThicknessUpdated(self):
        if(self.varName != None and self.radioButton_ContourMode.isChecked()):
            Utils.loadContours(self, self.varName)

    @pyqtSlot()
    def on_colorModeSelected(self):
        if self.radioButton_ColorMode.isChecked():
            self.gradientContours.setVisible(False)
            self.gradient.setVisible(True)
            if(self.varName != None):
                items = self.listWidget_Variables.findItems(self.varName, qCore.Qt.MatchExactly)
                item = items[0]
                item.setSelected(True)
            if self.contActor != None:
                self.ren.RemoveActor(self.contActor)
                self.iren.Render()

    @pyqtSlot()
    def on_contourModeSelected(self):
        if self.radioButton_ContourMode.isChecked():
            if(self.newMinContours != None):
                self.gradientContours.setVisible(True)
            self.gradient.setVisible(True)
            if(self.contourVarName != None):
                items = self.listWidget_Variables.findItems(self.contourVarName, qCore.Qt.MatchExactly)
                item = items[0]
                item.setSelected(True)
                if self.contActor != None:
                    self.ren.AddActor(self.contActor)
                    self.iren.Render()
                #self.applyVariable(False)   # commented as part of bug fix
            else:
                self.listWidget_Variables.clearSelection()

    @pyqtSlot()
    def on_videoQualityUpdate(self):
        dialValue = self.dial_videoQuality.value()
        self.label_videoQuality.setText(str(dialValue))

    @pyqtSlot()
    def on_frameRateUpdate(self):
        dialValue = self.dial_videoFrameRate.value()
        self.label_frameRate.setText(str(dialValue))

    @pyqtSlot()
    def on_scaleChanged(self):
        if self.checkBox_LogScale.isChecked() == True:
            self.ctf.SetScaleToLog10()
        else:
            self.ctf.SetScaleToLinear()
        self.ctf.Build()
        self.mapper.SetLookupTable(self.ctf)
        self.mapper.Update()
        self.iren.Render()

    @pyqtSlot()
    def applyVariable(self, refreshVariable = True):
        if(refreshVariable == True and self.radioButton_ColorMode.isChecked()): # if color mode
            self.varName = self.listWidget_Variables.currentItem().text()
            self.label_color_varname.setText(self.varName)
        if self.radioButton_ContourMode.isChecked(): # if contour mode
            self.contourVarName = self.listWidget_Variables.currentItem().text()
            self.label_contour_varname.setText(self.contourVarName)

        # currentItemIndex = self.listWidget_Variables.indexFromItem(self.listWidget_Variables.currentItem()).row()
        # for index in range(self.listWidget_Variables.count()):
        #     item = self.listWidget_Variables.item(index)
        #     print(currentItemIndex, index)
        #     if(currentItemIndex==index):
        #         self.listWidget_Variables.item(index).setBackground((QColor(138, 157, 191)))
        #     else:
        #         self.listWidget_Variables.item(index).setBackground((QColor(52, 59, 72)))

        self.fmt = qGui.QTextCharFormat()
        self.cursor = qGui.QTextCursor(self.plainTextEdit_netCDFDataText.document())
        self.cursor.select(qGui.QTextCursor.Document)
        self.cursor.setCharFormat(qGui.QTextCharFormat())  # Clear existing selections
        self.cursor.clearSelection()
        pattern = "Name:" + str(self.varName)
        regex = qCore.QRegExp(pattern)
        pos = 0
        index = regex.indexIn(
            self.plainTextEdit_netCDFDataText.document().toPlainText(), pos
        )

        if index != -1:
            self.cursor.setPosition(index, qGui.QTextCursor.MoveAnchor)
            self.cursor.setPosition(index + len(pattern), qGui.QTextCursor.KeepAnchor)
            self.plainTextEdit_netCDFDataText.ensureCursorVisible()
            self.cursor.setCharFormat(self.fmt)
            self.plainTextEdit_netCDFDataText.setTextCursor(self.cursor)
            self.plainTextEdit_netCDFDataText.textCursor().clearSelection()
        if self.radioButton_3DView.isChecked() == True:
            Utils.variableControlsSetVisible(self, True)

        if self.radioButton_ColorMode.isChecked():  # If color mode is selected
            Utils.updateGlobeGeometry(self, self.varName)
            if(refreshVariable):
                self.dataRange = self.mapper.GetInput().GetCellData().GetScalars(self.varName).GetRange()
                self.newMin = self.dataRange[0]
                self.newMax = self.dataRange[1]
            self.gradient.update()
        if self.radioButton_ContourMode.isChecked():  # If contour mode is selected
            # self.colorGradientsBackup = self.gradient.gradient()
            # self.contourGradients = [(0.0, QColor(52, 59, 72)), (0.5, QColor(52, 59, 72)), (1.0, QColor(52, 59, 72))]
            # self.gradient.setGradient(self.contourGradients)
            # print(self.colorGradientsBackup)
            self.dataRangeContours = self.mapper.GetInput().GetCellData().GetScalars(self.contourVarName).GetRange()
            self.newMinContours = self.dataRangeContours[0]
            self.newMaxContours = self.dataRangeContours[1]
            Utils.loadContours(self, self.contourVarName)
            self.gradientContours.update()
            if(self.gradientContours.isVisible() == False):
                self.gradientContours.setVisible(True)

    @pyqtSlot()
    def changeView(self):
        rbtn = self.sender()
        if rbtn.isChecked() == True:
            if rbtn.text() == "Metadata":
                self.stackedWidget.setCurrentWidget(self.page_InspectData)
                Utils.variableControlsSetVisible(self, False)
            ############################
            # 2D Render View  (# Not going to be implemented.)
            ############################
            # if (rbtn.text() == "2D"):  # Not going to be implemented.
            # self.stackedWidget.setCurrentWidget(self.page_2DMap)
            # layout = QVBoxLayout()
            # self.frame_2D.setLayout(layout)
            # coordinate = (37.8199286, -122.4782551)
            # m = folium.Map(
            #    tiles='cartodbpositron',
            #    zoom_start=13,
            #    location=coordinate, zoom_control=False
            # )
            ## save map data to data object
            # data = io.BytesIO()
            # m.save(data, close_file=False)
            ## Enable the following two lines when 2D maps are required.
            ##self.webView.setHtml(data.getvalue().decode())
            ##layout.addWidget(self.webView)
            ############################
            # 3D Render View
            ############################
            if rbtn.text() == "3D":
                self.stackedWidget.setCurrentWidget(self.page_3DMap)
                if self.varName != None:
                    Utils.variableControlsSetVisible(self, True)

    @pyqtSlot()
    def on_timeSlider_Changed(self):
        self.currentTimeStep = self.horizontalSlider_Main.value()
        if self.IsTemporalDataset == True:
            self.textActor.SetInput(str(self.actualTimeStrings[self.currentTimeStep]))
        self.reader.GetOutputInformation(0).Set(
            vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(),
            self.rawTimes[self.currentTimeStep - 1],
        )
        self.pa.AddArray(
            1, self.varName
        )  # 0 for PointData, 1 for CellData, 2 for FieldData
        self.pa.Update()
        self.mapper.GetInput().GetCellData().AddArray(
            self.pa.GetOutput().GetCellData().GetAbstractArray(self.varName)
        )
        # self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetArray(0))
        self.label_FrameStatus.setText(
            str(self.currentTimeStep) + "/" + str(self.maxTimeSteps)
        )
        if self.radioButton_ContourMode.isChecked():
            Utils.loadContours(self, self.contourVarName)
        else:
            if self.contActor != None:
                self.ren.RemoveActor(self.contActor)
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
        index_pos_list = [
            i for i in range(len(dimNamesList)) if dimNamesList[i] == selectedDimension
        ]
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
        if(self.tabWidget.currentWidget().objectName() == "Settings"): # Do not update when user in settings page.
            return
        for cmapItem in self.cmaps:
            if cmapItem["name"] == str(self.comboBox_ColorMaps.currentText()):
                color1List = [int(x) for x in cmapItem["color1"].split(",")]
                color2List = [int(x) for x in cmapItem["color2"].split(",")]
                gradientList = []
                cstart = (
                    0,
                    QColor(color1List[0], color1List[1], color1List[2], color1List[3]),
                )
                cend = (
                    1,
                    QColor(color2List[0], color2List[1], color2List[2], color2List[3]),
                )
                stops = cmapItem["stops"].split(":")
                gradientList.append(cstart)
                for item in stops:
                    stopData = item.split(";")
                    stop = float(stopData[0])
                    cvalues = [int(x) for x in stopData[1].split(",")]
                    gradientList.append(
                        (stop, QColor(cvalues[0], cvalues[1], cvalues[2], cvalues[3]))
                    )
                gradientList.append(cend)
                self.gradient.setGradient(gradientList)
                self.gradient.update()
                break

    @pyqtSlot()
    def updateLUT(self):
        # print("updating lut")
        gradients = self.gradient.gradient()

        stops = [data[0] for data in gradients]
        oldMin = 0
        oldMax = 1

        newRange = self.newMax - self.newMin

        self.ctf.RemoveAllPoints()
        for gradient in gradients:
            # print(type(gradient[1]))
            oldValue = float(gradient[0])
            newValue = ((oldValue - oldMin) * newRange) + self.newMin
            if isinstance(gradient[1], str) == True:
                rgb = matplotlib.colors.to_rgb(gradient[1])
                self.ctf.AddRGBPoint(newValue, rgb[0], rgb[1], rgb[2])
            else:
                self.ctf.AddRGBPoint(
                    newValue,
                    gradient[1].redF(),
                    gradient[1].greenF(),
                    gradient[1].blueF(),
                )
        self.ctf.Build()
        self.mapper.Update()
        self.iren.Render()

    # Handler for browse folder button click.
    @pyqtSlot()
    def initializeRenderer(self):
        self.vl = Qt.QVBoxLayout()
        self.vl.setContentsMargins(0,0,0,0)
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.vl.addWidget(self.vtkWidget)
        self.ren = vtk.vtkRenderer()
        self.ren.SetBackground(33 / 255.0, 37.0 / 255, 43.0 / 255)
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        # self.vtkWidget.GetRenderWindow().SetMultiSamples(4)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        self.actor_style = vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(self.actor_style)

        self.iren.SetRenderWindow(self.vtkWidget.GetRenderWindow())
        # self.ren.UseFXAAOn()
        self.ren.ResetCamera()
        self.frame.setLayout(self.vl)
        self.iren.Initialize()

        # Get the generic render window ID
        #gl_info = self.vtkWidget.GetRenderWindow().GetOpenGLInformation()
        openglRendererInUse = self.ren.GetRenderWindow().ReportCapabilities().splitlines()[1].split(":")[1].strip()

        # Print the active graphics card info
        self.label_6.setText("Current Graphics Vendor:" + "\n" + str(openglRendererInUse))

        # Sign up to receive TimerEvent
        # cb = vtkTimerCallback(1, self.iren)
        # self.iren.AddObserver('TimerEvent', cb.execute)
        # cb.timerId = self.iren.CreateRepeatingTimer(500)

        self.iren.Render()
        self.ren.Render()

        self.timer = qCore.QTimer()
        self.timer.timeout.connect(self.onTimerEvent)
        # self.timer.start(100)
        self.contourFilter = vtk.vtkContourFilter()
        # web view
        # self.webView = QWebEngineView()
        #print("Renderer Initialized.")

    def onTimerEvent(self):
        if (
            self.stackedWidget.currentWidget().objectName() == "page_3DMap"
            or self.stackedWidget.currentWidget().objectName() == "page_2DMap"
        ):
            if self.animationDirection == -1:
                if self.currentTimeStep > 1:
                    self.currentTimeStep = self.currentTimeStep - 1
                else:
                    self.currentTimeStep = self.maxTimeSteps
            else:
                if self.currentTimeStep < self.maxTimeSteps:
                    self.currentTimeStep = self.currentTimeStep + 1
                else:
                    self.currentTimeStep = 1
            self.reader.GetOutputInformation(0).Set(
                vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(),
                self.rawTimes[self.currentTimeStep - 1],
            )
            self.pa.AddArray(
                1, self.varName
            )  # 0 for PointData, 1 for CellData, 2 for FieldData
            self.pa.Update()
            if self.IsTemporalDataset == True:
                self.textActor.SetInput(
                    str(self.actualTimeStrings[self.currentTimeStep - 1])
                )
            self.mapper.GetInput().GetCellData().AddArray(
                self.pa.GetOutput().GetCellData().GetAbstractArray(self.varName)
            )
            # self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetArray(0))
            self.label_FrameStatus.setText(
                str(self.currentTimeStep) + "/" + str(self.maxTimeSteps)
            )
            if self.radioButton_ContourMode.isChecked():
                Utils.loadContours(self, self.contourVarName)
            else:
                if self.contActor != None:
                    self.ren.RemoveActor(self.contActor)
            self.iren.Render()

    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)
        self.vtkWidget.Finalize()

    def initializeApp(self):
        self.pa = vtk.vtkPassArrays()
        self.gradient = Gd.Gradient("color", self)
        self.gradient.setGradient([(0, "black"), (1, "green"), (0.5, "red")])
        self.gradientContours = Gd.Gradient("contour", self)
        self.gradientContours.setGradient(
            [
                (0, QColor(52, 59, 72)),
                (1, QColor(52, 59, 72)),
                (0.5, QColor(52, 59, 72)),
            ]
        )
        self.gradient.setFixedHeight(35)
        self.gradientContours.setFixedHeight(35)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.gradient, qCore.Qt.AlignCenter)
        self.layout.addWidget(self.gradientContours, qCore.Qt.AlignCenter)
        self.gradientContours.setVisible(False)
        self.frame_colormap.setLayout(self.layout)
        # Read color map information.
        self.cmaps = Utils.readColorMapInfo(self, self.cmapFile)
        for item in self.cmaps:
            self.comboBox_ColorMaps.addItem(item["name"])
            self.comboBox_ColorMapsSettings.addItem(item["name"])
        color1List = [int(x) for x in self.cmaps[0]["color1"].split(",")]
        color2List = [int(x) for x in self.cmaps[0]["color2"].split(",")]
        gradientList = []
        cstart = (0, QColor(color1List[0], color1List[1], color1List[2], color1List[3]))
        cend = (1, QColor(color2List[0], color2List[1], color2List[2], color2List[3]))
        stops = self.cmaps[0]["stops"].split(":")
        gradientList.append(cstart)
        for item in stops:
            stopData = item.split(";")
            stop = float(stopData[0])
            cvalues = [int(x) for x in stopData[1].split(",")]
            gradientList.append(
                (stop, QColor(cvalues[0], cvalues[1], cvalues[2], cvalues[3]))
            )
        gradientList.append(cend)
        self.gradient.setGradient(gradientList)
        self.comboBox_ColorMaps.currentTextChanged.connect(
            self.comboBox_ColorMaps_changed
        )  # Changed dimensions handler.
        self.gradient.gradientChanged.connect(self.colorMapChanged)
        self.gradientContours.gradientChanged.connect(self.contourValuesChanged)
        self.progressBar_ExportVideo.setVisible(False)
        # Disable all data controls when mainwindow loads.
        self.tabWidget.setVisible(False)
        Utils.controlsSetVisible(self, False)

    # Contour values changed.
    def contourValuesChanged(self):
        Utils.loadContours(self, self.contourVarName)

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
        self.progressBar.setStyleSheet(
            "background-color: rgb(90, 102, 125); border-radius: 2px;"
        )
        # self.progressBar.move(15, 40)

        self.layout.addWidget(self.lbl, qCore.Qt.AlignCenter)
        self.layout.addWidget(self.progressBar, qCore.Qt.AlignCenter)

        # widget = QWidget()
        self.prog_win.setLayout(self.layout)
        # self.setCentralWidget(self.prog_win)
        # self.progressBar.setRange(0,1)

    def onStart(self, reload=True):
        # self.progressBar.setRange(0,0)
        if reload == True:
            self.myLongTask.start()
        else:
            self.myDimensionUpdateTask.start()

    # added this function to close the progress bar
    # def onFinishedVideoExport(self):
    # self.prog_win.close()

    # added this function to close the progress bar
    def onFinished(self):
        # self.progressBar.setRange(0,1)
        self.prog_win.close()
        for item in self.dataDimensions:
            self.comboBox_dims.addItem(item)
        self.plainTextEdit_netCDFDataText.setPlainText(self.str_data)

        if self.rawTimes != None:  # valid time points available.
            self.maxTimeSteps = len(self.rawTimes)
            self.label_FrameStatus.setText("1/" + str(self.maxTimeSteps))
            self.horizontalSlider_Main.setMaximum(self.maxTimeSteps - 1)
            self.horizontalSlider_Main.setEnabled(True)
            self.IsTemporalDataset = True
        else:  # no time points available
            self.maxTimeSteps = 1
            self.horizontalSlider_Main.setEnabled(False)
            self.label_FrameStatus.setText("1/1")
            self.IsTemporalDataset = False

        self.currentTimeStep = 1
        # self.stackedWidget.setCurrentWidget(self.page_InspectData)
        # Enable all data controls
        self.tabWidget.setVisible(True)
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
            path = QFileDialog.getOpenFileName(
                self, "Open a file", "", "NetCDF files (*.nc)"
            )
            if path != ("", ""):
                # Stop play threads if running
                if self.timer.isActive() == True:
                    self.timer.stop()
                self.radioButton_RawView.setChecked(True)
                self.path = path[0]

                self.comboBox_dims.clear()  # clear dim var combobox
                self.listWidget_Variables.clear()  # clear variable list.
                self.gradientContours.setVisible(False) # hide contour widget.
                self.currentTimeStep = None
                self.animationDirection = 1
                self.actualTimeStrings = None
                self.varName = None
                self.contourVarName = None
                self.IsTemporalDataset = False
                self.maxTimeSteps = None
                self.newMin = None
                self.newMax = None
                self.newMinContours = None
                self.newMaxContours = None
                self.dataRange = None
                self.contActor = None
                self.radioButton_ColorMode.blockSignals(True)
                self.radioButton_ColorMode.setChecked(True)
                self.radioButton_ColorMode.blockSignals(False)
                #if(self.ren!=None):
                #    self.ren.RemoveAllViewProps()

                self.label_color_varname.setText("")
                self.label_contour_varname.setText("")
                self.prog_win.show()
                self.onStart()  # Start your very very long computation/process

        ############################
        # Apply selected variables.
        ############################
        if btnName == "pushButton_SetDimensions":
            # print("need to something here to regrid the data based on selected dimensions.")
            # print("Setting dimensions to ", self.comboBox_dims.currentText())

            # Stop play threads if running
            if self.timer.isActive() == True:
                self.timer.stop()
            self.comboBox_dims.clear()
            self.listWidget_Variables.clearSelection()
            self.reader.SetDimensions(self.comboBox_dims.currentText())
            self.reader.ComputeArraySelection()
            self.radioButton_RawView.setChecked(True)
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
            if self.maxTimeSteps != 1:
                self.animationDirection = -1
                if self.timer.isActive() == False:
                    self.timer.start()

        ############################
        # Previous Frame
        ############################
        if btnName == "pushButton_PreviousFrame":
            if self.maxTimeSteps == 1:
                return
            if (
                self.stackedWidget.currentWidget().objectName() == "page_3DMap"
                or self.stackedWidget.currentWidget().objectName() == "page_2DMap"
            ):
                if self.currentTimeStep > 1:
                    self.currentTimeStep = self.currentTimeStep - 1
                else:
                    self.currentTimeStep = self.maxTimeSteps
                self.reader.GetOutputInformation(0).Set(
                    vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(),
                    self.rawTimes[self.currentTimeStep - 1],
                )
                if self.IsTemporalDataset == True:
                    self.textActor.SetInput(
                        str(self.actualTimeStrings[self.currentTimeStep - 1])
                    )
                self.pa.AddArray(
                    1, self.varName
                )  # 0 for PointData, 1 for CellData, 2 for FieldData
                self.pa.Update()
                self.mapper.GetInput().GetCellData().AddArray(
                    self.pa.GetOutput().GetCellData().GetAbstractArray(self.varName)
                )
                # self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetArray(0))
                self.label_FrameStatus.setText(
                    str(self.currentTimeStep) + "/" + str(self.maxTimeSteps)
                )
                if self.radioButton_ContourMode.isChecked():
                    Utils.loadContours(self, self.contourVarName)
                else:
                    if self.contActor != None:
                        self.ren.RemoveActor(self.contActor)
                self.iren.Render()

        ############################
        # Pause
        ############################
        if btnName == "pushButton_Pause":
            # print("pause playback")
            self.timer.stop()

        ############################
        # Next frame
        ############################
        if btnName == "pushButton_NextFrame":
            if self.maxTimeSteps == 1:
                return
            if (
                self.stackedWidget.currentWidget().objectName() == "page_3DMap"
                or self.stackedWidget.currentWidget().objectName() == "page_2DMap"
            ):
                if self.currentTimeStep < self.maxTimeSteps:
                    self.currentTimeStep = self.currentTimeStep + 1
                else:
                    self.currentTimeStep = 1

                self.reader.GetOutputInformation(0).Set(
                    vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(),
                    self.rawTimes[self.currentTimeStep - 1],
                )
                self.pa.AddArray(
                    1, self.varName
                )  # 0 for PointData, 1 for CellData, 2 for FieldData
                self.pa.Update()
                if self.IsTemporalDataset == True:
                    self.textActor.SetInput(
                        str(self.actualTimeStrings[self.currentTimeStep - 1])
                    )
                self.mapper.GetInput().GetCellData().AddArray(
                    self.pa.GetOutput().GetCellData().GetAbstractArray(self.varName)
                )
                # self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetArray(0))
                self.mapper.GetInput().GetCellData().SetActiveScalars(self.varName)
                self.label_FrameStatus.setText(
                    str(self.currentTimeStep) + "/" + str(self.maxTimeSteps)
                )

                if self.radioButton_ContourMode.isChecked():
                    Utils.loadContours(self, self.contourVarName)
                else:
                    if self.contActor != None:
                        self.ren.RemoveActor(self.contActor)
                # self.mapper.Update()
                self.iren.Render()

        ############################
        # Play forward
        ############################
        if btnName == "pushButton_PlayForward":
            if self.maxTimeSteps != 1:
                self.animationDirection = 1
                if self.timer.isActive() == False:
                    self.timer.start()

        ############################
        # Set New Scalar Range
        ############################
        if btnName == "pushButton_UpdateRange":
            if self.radioButton_ColorMode.isChecked():
                if self.varName == None:
                    return
            else:
                if(self.contourVarName == None):
                    return
            inputDialog = QInputDialog(None)
            inputDialog.setInputMode(QInputDialog.TextInput)
            inputDialog.setLabelText('Please enter the start value:')
            Utils.applyTheme(inputDialog)
            inputDialog.setWindowFlags(qCore.Qt.FramelessWindowHint)
            ok = inputDialog.exec_()
            if not ok:
                return
            text_start = inputDialog.textValue()

            if (
                isinstance(text_start, int) == True
                or isinstance(text_start, float) == True
            ):
                em = QErrorMessage(self)
                em.showMessage("Unable to set the range. Please check your data.")
                return

            inputDialog = QInputDialog(None)
            inputDialog.setInputMode(QInputDialog.TextInput)
            inputDialog.setLabelText('Please enter the end value:')
            Utils.applyTheme(inputDialog)
            inputDialog.setWindowFlags(qCore.Qt.FramelessWindowHint)
            ok = inputDialog.exec_()
            if not ok:
                return
            text_end = inputDialog.textValue()

            if (
                isinstance(text_end, int) == True or isinstance(text_end, float) == True
            ):  # if not a numberupdate_scene_for_new_range
                em = QErrorMessage(self)
                em.showMessage("Unable to set the range. Please check your data.")
                return
            self.update_scene_for_new_range(text_start, text_end)

        ############################
        # Reset variable scalar range to default.
        ############################
        if btnName == "pushButton_ResetRange":
            if self.radioButton_ColorMode.isChecked():
                if self.varName == None:
                    return
            else:
                if(self.contourVarName == None):
                    return
            self.update_scene_for_new_range()
            if self.radioButton_ColorMode.isChecked():
                self.gradient.update()
            if self.radioButton_ContourMode.isChecked():
                self.gradientContours.update()
                Utils.loadContours(self, self.contourVarName)

        ############################
        # Export image.
        ############################
        if btnName == "pushButton_ExportImage":
            if self.varName == None:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("No variable selected!")
                Utils.applyTheme(dlg)
                dlg.setText(
                    "No variable has been selected. Please select a variable first for using export feature."
                )
                dlg.exec()
                return
            Utils.exportImage(self)

        ############################
        # Export video.
        ############################
        if btnName == "pushButton_ExportVideo":
            if self.varName == None:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("No variable selected!")
                Utils.applyTheme(dlg)
                dlg.setText(
                    "No variable has been selected. Please select a variable first for using export feature."
                )
                dlg.exec()
                return
            if self.IsTemporalDataset == False:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("Cannot export as video.")
                Utils.applyTheme(dlg)
                dlg.setText(
                    "The current dataset do not have multiple time points. Please load a temporal dataset to use the video export feature."
                )
                dlg.exec()
                return
            self.videoExportFolderName = str(
                QFileDialog.getExistingDirectory(self, "Select Directory")
            )
            if self.videoExportFolderName == "":
                return

            # Stop play threads if running
            if self.timer.isActive() == True:
                self.timer.stop()

            self.progressBar_ExportVideo.setVisible(True)

            windowToImageFilter = vtk.vtkWindowToImageFilter()
            windowToImageFilter.SetInput(self.vtkWidget.GetRenderWindow())
            windowToImageFilter.SetInputBufferTypeToRGB()
            windowToImageFilter.ReadFrontBufferOff()
            windowToImageFilter.Update()

            screenshotWidth = windowToImageFilter.GetOutput().GetDimensions()[0]
            channels_count = 3
            pixmap = self.gradient.grab()

            pixmapScaled = pixmap.scaledToWidth(screenshotWidth) 
            image = pixmapScaled.toImage()
            new_image = image.convertToFormat(QImage.Format_RGB888)
            height = pixmapScaled.height()
            width = pixmapScaled.width()
        
            b = new_image.bits()
            b.setsize(height * width * channels_count)
            arr = np.frombuffer(b, np.uint8).reshape((height, width, channels_count))
            image_data = vpl.image_io.vtkimagedata_from_array(arr, image_data=None)

            # Concatenate the two images vertically
            append = vtk.vtkImageAppend()
            append.SetAppendAxis(1)  # 0 for horizontal, 1 for vertical
            append.AddInputData(windowToImageFilter.GetOutput())
            append.AddInputData(image_data)
            if self.radioButton_ContourMode.isChecked() and self.contourVarName != None:
                pixmapContours = self.gradientContours.grab()
                pixmapScaledContours = pixmapContours.scaledToWidth(screenshotWidth)
                imageContours = pixmapScaledContours.toImage()
                new_image_contours = imageContours.convertToFormat(QImage.Format_RGB888)
                height = pixmapScaledContours.height()
                width = pixmapScaledContours.width()
                b_contours = new_image_contours.bits()
                b_contours.setsize(height * width * channels_count)
                arr_contours = np.frombuffer(b_contours, np.uint8).reshape((height, width, channels_count))
                image_data_conntours = vpl.image_io.vtkimagedata_from_array(arr_contours, image_data=None)
                append.AddInputData(image_data_conntours)
            append.Update()

            varString = ""
            fileString = ""
            if (self.varName != None):
                varString += "_" + self.varName
            if (self.contourVarName != None):
                varString += "-" + self.contourVarName
            fileString = os.path.basename(self.path)

            oggWriter = vtk.vtkOggTheoraWriter()
            timestr = time.strftime(fileString + "_Video_%Y%m%d-%H%M%S" + varString)
            oggWriter.SetFileName(self.videoExportFolderName + "/" + timestr + ".ogv")
            oggWriter.SetInputConnection(append.GetOutputPort())
            oggWriter.SetQuality(self.dial_videoQuality.value())
            oggWriter.SetRate(self.dial_videoFrameRate.value())
            oggWriter.Start()

            frameIndex = 0
            # Write frames to the file.
            for timeIndex in self.rawTimes:
                frameIndex = frameIndex + 1
                perc = (frameIndex / self.maxTimeSteps) * 100
                self.progressBar_ExportVideo.setValue(int(perc))
                if self.currentTimeStep < self.maxTimeSteps:
                    self.currentTimeStep = self.currentTimeStep + 1
                else:
                    self.currentTimeStep = 1
                self.reader.GetOutputInformation(0).Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(), timeIndex)
                self.pa.AddArray(1, self.varName)  # 0 for PointData, 1 for CellData, 2 for FieldData
                self.pa.Update()
                self.textActor.SetInput(str(self.actualTimeStrings[self.currentTimeStep - 1]))
                self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetAbstractArray(self.varName))
                # self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetArray(0))
                self.mapper.GetInput().GetCellData().SetActiveScalars(self.varName)
                self.label_FrameStatus.setText(str(self.currentTimeStep) + "/" + str(self.maxTimeSteps))
                if self.radioButton_ContourMode.isChecked():
                    Utils.loadContours(self, self.contourVarName)
                else:
                    if self.contActor != None:
                        self.ren.RemoveActor(self.contActor)
                # self.mapper.Update()
                self.iren.Render()
                windowToImageFilter.Modified()
                windowToImageFilter.Update()

                oggWriter.Write()

            oggWriter.End()

            self.progressBar_ExportVideo.setVisible(False)
            # self.videoExportTask.start()

        ############################
        # Save color map.
        ############################
        if btnName == "pushButton_SaveColorMap":
            if(self.varName==None):
                Utils.themedMessageBox(self, "No variable selected!", "No variable has been selected. Please select a variable first.")
                return

            # Create and show the input dialog
            # ---------------------------------
            inputDialog = QInputDialog(None)
            inputDialog.setInputMode(QInputDialog.TextInput)
            inputDialog.setLabelText('Enter a name for the color map:')
            Utils.applyTheme(inputDialog)
            inputDialog.setWindowFlags(qCore.Qt.FramelessWindowHint)
            ok = inputDialog.exec_()
            filename = inputDialog.textValue()
            if(len(filename.strip())==0):
                Utils.themedMessageBox(self, "Unable to save colormap", "Unable to save the colormap with an empty name. Please try again with a valid string.")
                return
            if(ok):
                gradients = self.gradient.gradient()
                adjustible_stops = gradients[1:-1]
                if(adjustible_stops == []):
                    stops = ""
                else:
                    stops = ""
                    for item in adjustible_stops:
                        stops = stops + "%f;%d,%d,%d,255:" % (item[0], item[1].red(), item[1].green(), item[1].blue())
                    stops = stops[:-1]
                
                addItem = filename.strip()
                color1 = "%d,%d,%d,255" % (gradients[0][1].red(), gradients[0][1].green(), gradients[0][1].blue())
                color2 = "%d,%d,%d,255" % (gradients[-1][1].red(), gradients[-1][1].green(), gradients[-1][1].blue())
                success = Utils.addColormap(self, addItem, color1, color2, stops)
                if(success == True):
                    Utils.refreshCmapControls(self)
                    Utils.themedMessageBox(self, "Colormap added.", "The new colormap have been successfully added.")
            else:
                return

        ############################
        # Remove colormap.
        ############################
        if btnName == "pushButton_RemoveColormap":
            cmapname = self.comboBox_ColorMapsSettings.currentText() 
            Utils.removeColormap(self, cmapname)
            Utils.refreshCmapControls(self)
            Utils.themedMessageBox(self, "Colormap removed.", "The selected colormap is now removed.")
            
        ############################
        # Restore default colormap.
        ############################
        if btnName == "pushButton_RestoreDefaultColormaps":
            treeDefault = ET.parse(self.cmapDefaultFile)
            treeDefault.write(self.cmapFile)
            Utils.refreshCmapControls(self)
            Utils.themedMessageBox(self, "Default colormap restored.", "The default colomap have been successfully restored!")

        ############################
        # Save 3D model (GLB/GLTF)
        ############################
        if btnName == "pushButton_Export3DModel":
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Not implemented.")
            dlg.setText("Sorry! This feature is not implemented yet.")
            Utils.applyTheme(dlg)
            #dlg.setWindowFlags(qCore.Qt.FramelessWindowHint)
            dlg.exec_()
            return
            #self.modelExportFolderName = str(
            #    QFileDialog.getExistingDirectory(self, "Select Directory")
            #)
            #if self.modelExportFolderName == "":
            #    return
            ##exporter = vtk.vtkGLTFExporter()
            #timestr = time.strftime("3DModelCapture_%Y%m%d-%H%M%S")
            ##exporter.SetRenderWindow(self.vtkWidget.GetRenderWindow())
            ##exporter.SetFileName(self.modelExportFolderName + "/" + timestr + ".glb")
            ##exporter.SetInlineData(True)
            ##exporter.SetSaveNormal(True)
            ##exporter.Update()


            #writer = vtk.vtkGLTFExporter()
            #writer.SetFileName(self.modelExportFolderName + "/" + timestr + ".gltf")
            #writer.InlineDataOn()
            #writer.SetRenderWindow(self.vtkWidget.GetRenderWindow())
            #writer.SetActiveRenderer(self.ren)
            #writer.Write()


    ##############################################################################
    # Update the scene for new range.
    ##############################################################################
    def update_scene_for_new_range(self, text_start=None, text_end=None):
        # dataRange = self.mapper.GetInput().GetCellData().GetScalars(self.varName).GetRange()
        oldMin = 0
        oldMax = 1
        if text_start == None and text_end == None:
            if self.radioButton_ColorMode.isChecked():
                self.newMin = self.dataRange[0]
                self.newMax = self.dataRange[1]
            else:
                self.newMinContours = self.dataRangeContours[0]
                self.newMaxContours = self.dataRangeContours[1]
        else:
            if self.radioButton_ColorMode.isChecked():
                if (
                    float(text_start) >= float(text_end)
                    or float(text_start) < Utils.truncate(self.dataRange[0], 1)
                    or float(text_end) > Utils.truncate(self.dataRange[1], 1)
                ):
                    dlg = QMessageBox(self)
                    dlg.setWindowTitle("Invalid range detected.")
                    dlg.setText("Unable to set the range. Please check your data.")
                    Utils.applyTheme(dlg)
                    #dlg.setWindowFlags(qCore.Qt.FramelessWindowHint)
                    dlg.exec_()
                    return
                self.newMin = float(text_start)
                self.newMax = float(text_end)
            else: # contour mode is selected
                if (
                    float(text_start) >= float(text_end)
                    or float(text_start) < Utils.truncate(self.dataRangeContours[0], 1)
                    or float(text_end) > Utils.truncate(self.dataRangeContours[1], 1)
                ):
                    dlg = QMessageBox(self)
                    dlg.setWindowTitle("Invalid range detected.")
                    dlg.setText("Unable to set the range. Please check your data.")
                    Utils.applyTheme(dlg)
                    #dlg.setWindowFlags(qCore.Qt.FramelessWindowHint)
                    dlg.exec_()
                    return
                self.newMinContours = float(text_start)
                self.newMaxContours = float(text_end)

        if self.radioButton_ColorMode.isChecked():
            newRange = self.newMax - self.newMin
            gradients = self.gradient.gradient()
            self.ctf.RemoveAllPoints()
            for gradient in gradients:
                oldValue = float(gradient[0])
                newValue = ((oldValue - oldMin) * newRange) + self.newMin
                self.ctf.AddRGBPoint(
                    newValue, gradient[1].redF(), gradient[1].greenF(), gradient[1].blueF()
                )
            if self.checkBox_LogScale.isChecked():
                self.ctf.SetScaleToLog10()
            else:
                self.ctf.SetScaleToLinear()
            self.ctf.Build()
        if self.radioButton_ContourMode.isChecked():
            Utils.loadContours(self, self.contourVarName)
        self.iren.Render()

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
        if self.isRefresh == True:
            #print("Processing NetCDF file")
            nc_fid = Dataset(
                self.main.path, "r"
            )  # Dataset is the class behavior to open the file
            nc_attrs, nc_dims, nc_vars, self.main.str_data = Utils.ncdump(nc_fid)
            if "time" in nc_fid.variables:
                sfctmp = nc_fid.variables["time"]
                timedim = sfctmp.dimensions[0]  # time dim name
                times = nc_fid.variables[timedim]
                dates = num2date(times[:], times.units)
                self.main.actualTimeStrings = [
                    date.strftime("%Y-%m-%d %H:%M:%S") for date in dates[:]
                ]
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
        if self.main.IsTemporalDataset == True:
            Utils.loadOverlay(self.main, self.main.actualTimeStrings)
        self.main.rawTimes = self.main.reader.GetOutputInformation(0).Get(
            vtk.vtkStreamingDemandDrivenPipeline.TIME_STEPS()
        )

        # tunits = self.main.reader.GetTimeUnits()

        # print("RAW TIMES:", self.main.rawTimes)
        self.taskFinished.emit()


app = qWidget.QApplication(sys.argv)
window = mainWindow()
window.setupUI()
window.show()

window.showMaximized()
sys.exit(app.exec_())
