import numpy as np
import datetime as dt
import vtk
import xml.etree.ElementTree as ET
from PyQt5.QtWidgets import QInputDialog, QErrorMessage, QFileDialog, QMessageBox
from PyQt5 import QtCore as qCore
from PyQt5.QtCore import QThread
import time
import math

##############################################################################
################# outputs dimensions, variables and their attribute information.
##############################################################################
def ncdump(nc_fid, verb=True):
	'''
	ncdump outputs dimensions, variables and their attribute information.
	The information is similar to that of NCAR's ncdump utility.
	ncdump requires a valid instance of Dataset.

	Parameters
	----------
	nc_fid : netCDF4.Dataset
		A netCDF4 dateset object
	verb : Boolean
		whether or not nc_attrs, nc_dims, and nc_vars are printed

	Returns
	-------
	nc_attrs : list
		A Python list of the NetCDF file global attributes
	nc_dims : list
		A Python list of the NetCDF file dimensions
	nc_vars : list
		A Python list of the NetCDF file variables
	str_data : basestring
		String representation of netCDF data
	'''

	def print_ncattr(key):
		"""
		Prints the NetCDF file attributes for a given key

		Parameters
		----------
		key : unicode
			a valid netCDF4.Dataset.variables key
		"""
		str = ""
		try:
			#print(type(repr(nc_fid.variables[key].dtype)))
			str += "\t\ttype:" + repr(nc_fid.variables[key].dtype) + "\n"
			for ncattr in nc_fid.variables[key].ncattrs():
				str += '\t\t%s:' % ncattr + repr(nc_fid.variables[key].getncattr(ncattr)) + "\n"
			return str
		except KeyError:
			str += "\t\tWARNING: %s does not contain variable attributes" % key
			return str

	global str_data
	str_data = ""
	# NetCDF global attributes
	nc_attrs = nc_fid.ncattrs()
	if verb:
		str_data += "NetCDF Global Attributes:" + "\n"
		for nc_attr in nc_attrs:
			str_data += '\t%s:' % nc_attr + " " + repr(nc_fid.getncattr(nc_attr)) + "\n"
	nc_dims = [dim for dim in nc_fid.dimensions]  # list of nc dimensions
	# Dimension shape information.
	if verb:
		str_data += "NetCDF dimension information:" + "\n"
		for dim in nc_dims:
			str_data += "\tName:" + str(dim) + "\n"
			str_data += "\t\tsize:" + str(len(nc_fid.dimensions[dim])) + "\n"
			str_data += print_ncattr(dim)
	# Variable information.
	nc_vars = [var for var in nc_fid.variables]  # list of nc variables
	if verb:
		str_data += "NetCDF variable information:" + "\n"
		for var in nc_vars:
			if var not in nc_dims:
				str_data += '\tName:' + str(var) + "\n"
				str_data += "\t\tdimensions:" + str(nc_fid.variables[var].dimensions) + "\n"
				str_data += "\t\tsize:" + str(nc_fid.variables[var].size) + "\n"
				str_data += print_ncattr(var)
	return nc_attrs, nc_dims, nc_vars, str_data

##############################################################################
################# load globe geometry
##############################################################################
def loadGlobeGeometry(self, variableToLoad=None):
	self.ren.RemoveAllViewProps()
	#print("Loading NetCDF...")
	self.reader.Update()
	#print("reading completed")

	#print(self.reader.GetCalendar())

	self.cellDataToPointData = vtk.vtkCellDataToPointData()
	self.cellDataToPointData.SetInputData(self.reader.GetOutput())
	self.cellDataToPointData.ProcessAllArraysOn()
	self.cellDataToPointData.PassCellDataOn()
	#cellDataToPointData.Update()

	# calculator = vtk.vtkArrayCalculator()
	# calculator.SetInputData(cellDataToPointData.GetOutput())
	# calculator.SetAttributeTypeToPointData()
	# calculator.ReplaceInvalidValuesOn()
	# calculator.SetReplacementValue(0)
	# calculator.AddScalarArrayName("elevation")
	# calculator.AddCoordinateScalarVariable("coordsX", 0)
	# calculator.AddCoordinateScalarVariable("coordsY", 1)
	# calculator.AddCoordinateScalarVariable("coordsZ", 2)
	# # print("Hi Sherin", calculator.GetScalarArrayNames())
	# # print("i am here2")
	# calculator.CoordinateResultsOn()
	# # calculator.SetFunction("(1 + (elevation/6370000) * 40)* ( iHat * cos(asin(coordsZ)) * cos(atan(coordsY/coordsX)) * coordsX/abs(coordsX) + jHat * cos(asin(coordsZ)) * sin(atan(coordsY/coordsX)) * coordsX/abs(coordsX) + kHat * coordsZ)")
	# calculator.SetResultArrayName("Result")
	# calculator.Update()

	# texturemaptosphere = vtk.vtkTextureMapToSphere()
	# texturemaptosphere.SetInputData(calculator.GetUnstructuredGridOutput())
	# texturemaptosphere.Update()

	# print("Calculator output is", type(calculator.GetUnstructuredGridOutput()))
	# print(calculator.GetUnstructuredGridOutput())
	# quit()

	# goemetryFilter = vtk.vtkGeometryFilter()
	# goemetryFilter.SetInputData(calculator.GetUnstructuredGridOutput())
	# goemetryFilter.Update()

	# goemetryFilter = vtk.vtkGeometryFilter()
	# goemetryFilter.SetInputData(cellDataToPointData.GetUnstructuredGridOutput())
	# goemetryFilter.Update()

	goemetryFilter = vtk.vtkGeometryFilter()
	goemetryFilter.SetInputConnection(self.cellDataToPointData.GetOutputPort())
	goemetryFilter.Update()

	self.ctf = vtk.vtkColorTransferFunction()
	self.ctf.AddRGBPoint(-1018.2862548828125, 0.231373, 0.298039, 0.752941)
	self.ctf.AddRGBPoint(1364.7484741210938, 0.865003, 0.865003, 0.865003)
	self.ctf.AddRGBPoint(3747.783203125, 0.705882, 0.0156863, 0.14902)
	self.ctf.Build()

	self.mapper = vtk.vtkPolyDataMapper()
	self.mapper.SetInputData(goemetryFilter.GetOutput())
	self.mapper.SetColorModeToMapScalars()
	if variableToLoad != None:
		self.mapper.GetInput().GetPointData().SetActiveScalars("elevation")
		self.mapper.SetLookupTable(self.ctf)
	self.mapper.ScalarVisibilityOn()
	#self.mapper.Update()

	# print(goemetryFilter.GetOutput())

	self.actor = vtk.vtkActor()
	self.actor.SetMapper(self.mapper)
	self.actor.GetProperty().SetOpacity(0)
	self.ren.AddActor(self.actor)
	self.ren.ResetCamera()
	#self.iren.Render()
	#print("render issued")


##############################################################################
################# load globe geometry
##############################################################################
def loadOverlay(self, timeStrings):
	# Create text overlay
	self.textActor = vtk.vtkTextActor()
	self.textActor.SetInput(str(timeStrings[0]))
	self.textActor.GetTextProperty().SetColor(1.0, 1.0, 1.0)
	self.textActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
	self.textActor.SetPosition(0.99, 0.96)
	self.textActor.SetVisibility(True)
	txtprop = self.textActor.GetTextProperty()
	txtprop.SetFontFamily(4)
	txtprop.SetFontFile("assets\\fonts\\arial.ttf")
	txtprop.SetFontSize(16)
	txtprop.SetColor(0.686274, 0.7803921, 0.949019)
	txtprop.SetJustificationToRight()
	self.ren.AddActor2D(self.textActor)

##############################################################################
################# load globe geometry
##############################################################################
def updateGlobeGeometry(self, variableName):
	#print("updating globe geometry")
	if(variableName == None or variableName == ""):
		self.mapper.ScalarVisibilityOff()
		self.actor.GetProperty().SetOpacity(0)
		return
	else:
		#self.pa.AddArray(1, variableName)  # 0 for PointData, 1 for CellData, 2 for FieldData
		#self.pa.Update()
		self.mapper.ScalarVisibilityOn()
		#self.mapper.GetInput().GetPointData().SetActiveScalars(variableName)
		#print(self.pa.GetOutput().GetCellData().GetNumberOfArrays())
		#print(self.pa.GetOutput().GetCellData().GetScalars())
		#numberOfArrays = self.pa.GetOutput().GetCellData().GetNumberOfArrays()
		#for i in range(numberOfArrays):
		#    print(self.pa.GetOutput().GetCellData().GetArray(i).GetName())
		self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetAbstractArray(variableName))
		#self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetArray(0))
		self.mapper.GetInput().GetCellData().SetActiveScalars(variableName)
		self.dataRange = self.mapper.GetInput().GetCellData().GetScalars(variableName).GetRange()

		#print("sherin", self.gradient.gradient())

		# self.ctf.RemoveAllPoints()
		# self.ctf.AddRGBPoint(dataRange[0], 0.231373, 0.298039, 0.752941)
		# self.ctf.AddRGBPoint(dataRange[1], 0.705882, 0.0156863, 0.14902)
		# self.ctf.Build()
		gradients = self.gradient.gradient()
		stops = [data[0] for data in gradients]
		oldMin = 0
		oldMax = 1
		newMin = self.dataRange[0]
		newMax = self.dataRange[1]
		#self.label_VarMin.setText(str(f'{newMin:.2f}'))
		#self.label_VarMax.setText(str(f'{newMax:.2f}'))
		newRange = newMax - newMin

		self.ctf.RemoveAllPoints()
		for gradient in gradients:
			oldValue = float(gradient[0])
			newValue = ((oldValue - oldMin) * newRange) + newMin
			self.ctf.AddRGBPoint(newValue, gradient[1].redF(), gradient[1].greenF(), gradient[1].blueF())
		if(self.checkBox_LogScale.isChecked()):
			self.ctf.SetScaleToLog10()
		else:
			self.ctf.SetScaleToLinear()
		self.ctf.Build()

		#print("entering here")
		#self.test = self.mapper.GetInput().GetPointData()
		#self.test2 = self.mapper.GetInput().GetPointData()
		#print(self.test)
		#print(self.test2)
		self.mapper.SetLookupTable(self.ctf)
		self.actor.GetProperty().SetOpacity(1)
		self.mapper.Update()
		self.iren.Render()

##############################################################################
################# load globe geometry
##############################################################################
def loadContours(self, variableName):
	if self.contActor != None:
		self.ren.RemoveActor(self.contActor)
	assignAttribute = vtk.vtkAssignAttribute()
	assignAttribute.SetInputConnection(self.cellDataToPointData.GetOutputPort())
	assignAttribute.Assign(variableName, "SCALARS", "POINT_DATA")
	assignAttribute.Update()

	dataRange = self.mapper.GetInput().GetCellData().GetScalars(variableName).GetRange()
	
	self.contourFilter.SetInputData(assignAttribute.GetOutput())
	self.contourFilter.SetInputArrayToProcess(0, 0, 0, 0, variableName)
	oldMin = 0
	oldMax = 1
	newRange = self.newMax - self.newMin
	isos = self.gradientContours.gradient()[1:-1]  # extract subset after removing first and last elements.
	contourIndex = 0
	for item in isos:
		oldValue = float(item[0])
		newValue = ((oldValue - oldMin) * newRange) + self.newMin
		self.contourFilter.SetValue(contourIndex, newValue)
		#print("Seting Value ", newValue)
		contourIndex = contourIndex + 1

	#contourFilter.SetValue(0, 2000.0)
	#self.contourFilter.GenerateValues(3, dataRange[0], dataRange[1])
	self.contourFilter.Update()

	self.contourMapper = vtk.vtkPolyDataMapper()
	self.contourMapper.SetInputData(self.contourFilter.GetOutput())
	self.contourMapper.Update()
	if self.contActor == None:
		self.contActor = vtk.vtkActor()	
	self.contActor.SetMapper(self.contourMapper)
	self.contActor.GetProperty().SetColor(0,0,0)
	self.contActor.GetProperty().SetLineWidth(5.0)
	 
	self.ren.AddActor(self.contActor)
	self.iren.Render()


##############################################################################
################# update loaded contours
##############################################################################
def updateExistingContours(self):
	pass

##############################################################################
################# show status message
################# type = success (showed in green) , type = error (showed in red)
##############################################################################
def statusMessage(self, message, type="success"):
	if(type == "success"):
		self.textEdit_Status.setStyleSheet("background-color: #7E9C73;")
	if(type == "error"):
		self.textEdit_Status.setStyleSheet("background-color: #DE7575;")
	self.textEdit_Status.setPlainText(message)


##############################################################################
################# show/hide basic data controls
##############################################################################
def controlsSetVisible(self, visibility):
	self.horizontalSlider_Main.setVisible(visibility)
	self.pushButton_SetDimensions.setVisible(visibility)
	self.gradient.setVisible(visibility)
	self.comboBox_dims.setVisible(visibility)
	self.label_3.setVisible(visibility)
	self.label.setVisible(visibility)
	self.label_5.setVisible(visibility)
	self.frame_2.setVisible(visibility)
	self.listWidget_Variables.setVisible(visibility)
	self.label_6.setVisible(visibility)
	self.textEdit_Status.setVisible(visibility)
	if(visibility==True):
		visibility = not visibility
	self.frame_3.setVisible(visibility)
	self.comboBox_ColorMaps.setVisible(visibility)
	self.checkBox_LogScale.setVisible(visibility)
	self.label_FrameStatus.setVisible(visibility)
	self.label_2.setVisible(visibility)
	self.label_4.setVisible(visibility)
	self.label_10.setVisible(visibility)
	self.frame_4.setVisible(visibility)


##############################################################################
################# show/hide variable data controls
##############################################################################
def variableControlsSetVisible(self, visibility):
	self.frame_3.setVisible(visibility)
	self.comboBox_ColorMaps.setVisible(visibility)
	self.checkBox_LogScale.setVisible(visibility)
	self.label_FrameStatus.setVisible(visibility)
	self.label_2.setVisible(visibility)
	self.label_4.setVisible(visibility)
	self.label_10.setVisible(visibility)
	self.frame_4.setVisible(visibility)

##############################################################################
################# read color ramp xml file
################# returns color data as list of dictionaries.
##############################################################################
def readColorMapInfo(self, colorRampFile):
	tree = ET.parse(colorRampFile)
	root = tree.getroot()
	colorDataList = []
	# parse color xml info.
	for elem in root:
		cmapitem = {}
		cmapitem['name'] = elem.attrib['name']
		for subelem in elem:
			if (subelem.attrib['k'] == 'color1'):
				cmapitem['color1'] = subelem.attrib['v']
			if (subelem.attrib['k'] == 'color2'):
				cmapitem['color2'] = subelem.attrib['v']
			if (subelem.attrib['k'] == 'stops'):
				cmapitem['stops'] = subelem.attrib['v']
		colorDataList.append(cmapitem)
	return colorDataList


##############################################################################
################# Save current visualization to file.
################# returns nothing.
##############################################################################
def exportImage(self):
	if(self.stackedWidget.currentWidget().objectName() == "page_3DMap"):
		largeImage = vtk.vtkRenderLargeImage()
		largeImage.SetInput(self.ren)
		largeImage.SetMagnification(2)
		largeImage.Update()
		self.iren.Render()

		writer = vtk.vtkPNGWriter()
		file = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
		if(file==""):
			return
		timestr = time.strftime("%Y%m%d-%H%M%S")
		writer.SetFileName(file+"/"+timestr+".png")
		writer.SetInputConnection(largeImage.GetOutputPort())
		writer.Write()
	else:
		dlg = QMessageBox(self)
		dlg.setWindowTitle("Incorrect view selected.")
		dlg.setText("Cannot save current view as image file. Please switch to 3D view and try again.")
		dlg.exec()

##############################################################################
################# Save current visualization as a video to file.
################# returns nothing.
##############################################################################
def exportVideo(self):
	pass

##############################################################################
################# Truncate float value
################# returns truncated value
##############################################################################
def truncate(f, n):
		return math.floor(f * 10 ** n) / 10 ** n

##############################################################################
################# Video Writer
##############################################################################
class VideoTaskThread(qCore.QThread):
	taskFinished = qCore.pyqtSignal()

	# I also added this so that I can pass data between classes
	def __init__(self, mainObject, parent=None):
		QThread.__init__(self, parent)
		self.main = mainObject

	def run(self):
		print("entering here")


		windowToImageFilter = vtk.vtkWindowToImageFilter()
		windowToImageFilter.SetInput(self.main.vtkWidget.GetRenderWindow())
		windowToImageFilter.SetInputBufferTypeToRGB()
		windowToImageFilter.ReadFrontBufferOff()
		windowToImageFilter.Update()

		aviWriter = vtk.vtkAVIWriter()
		aviWriter.SetFileName(self.main.videoExportFolderName)
		aviWriter.SetInputData(windowToImageFilter.GetOutput())
		aviWriter.SetQuality(2)
		aviWriter.SetRate(24)
		aviWriter.SetCompressorFourCC("DIB")
		aviWriter.Start()
		print("entering here3")

		# Write frames to the file.
		for timeIndex in range(self.main.rawTimes):
			print("Writing frame", timeIndex)
			self.main.reader.GetOutputInformation(0).Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(), timeIndex)
			self.main.pa.AddArray(1, self.varName)  # 0 for PointData, 1 for CellData, 2 for FieldData
			self.main.pa.Update()
			self.main.mapper.GetInput().GetCellData().AddArray(self.main.pa.GetOutput().GetCellData().GetAbstractArray(self.main.varName))
			#self.mapper.GetInput().GetCellData().AddArray(self.pa.GetOutput().GetCellData().GetArray(0))
			self.main.mapper.GetInput().GetCellData().SetActiveScalars(self.main.varName)
			#self.mapper.Update()
			self.main.iren.Render()
			windowToImageFilter.Modified()
			windowToImageFilter.Update()
			aviWriter.Write()
		
		aviWriter.End()

		self.taskFinished.emit()