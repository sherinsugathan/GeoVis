import numpy as np
import datetime as dt
import vtk


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
################# populate color maps to GUI control
##############################################################################
def populateSupportedColorMaps(self):
    self.comboBox_ColorMaps.addItem("spectrum")
    self.comboBox_ColorMaps.addItem("warm")
    self.comboBox_ColorMaps.addItem("cool")
    self.comboBox_ColorMaps.addItem("blues")
    self.comboBox_ColorMaps.addItem("wild_flower")
    self.comboBox_ColorMaps.addItem("citrus")
    self.comboBox_ColorMaps.addItem("brewer_diverging_purple_orange_11")
    self.comboBox_ColorMaps.addItem("brewer_diverging_purple_orange_10")
    self.comboBox_ColorMaps.addItem("brewer_diverging_purple_orange_9")
    self.comboBox_ColorMaps.addItem("brewer_diverging_purple_orange_8")
    self.comboBox_ColorMaps.addItem("brewer_diverging_purple_orange_7")
    self.comboBox_ColorMaps.addItem("brewer_diverging_purple_orange_6")
    self.comboBox_ColorMaps.addItem("brewer_diverging_purple_orange_5")
    self.comboBox_ColorMaps.addItem("brewer_diverging_purple_orange_4")
    self.comboBox_ColorMaps.addItem("brewer_diverging_purple_orange_3")
    self.comboBox_ColorMaps.addItem("brewer_diverging_spectral_11")
    self.comboBox_ColorMaps.addItem("brewer_diverging_spectral_10")
    self.comboBox_ColorMaps.addItem("brewer_diverging_spectral_9")
    self.comboBox_ColorMaps.addItem("brewer_diverging_spectral_8")
    self.comboBox_ColorMaps.addItem("brewer_diverging_spectral_7")
    self.comboBox_ColorMaps.addItem("brewer_diverging_spectral_6")
    self.comboBox_ColorMaps.addItem("brewer_diverging_spectral_5")
    self.comboBox_ColorMaps.addItem("brewer_diverging_spectral_4")
    self.comboBox_ColorMaps.addItem("brewer_diverging_spectral_3")
    self.comboBox_ColorMaps.addItem("brewer_diverging_brown_blue_green_11")
    self.comboBox_ColorMaps.addItem("brewer_diverging_brown_blue_green_10")
    self.comboBox_ColorMaps.addItem("brewer_diverging_brown_blue_green_9")
    self.comboBox_ColorMaps.addItem("brewer_diverging_brown_blue_green_8")
    self.comboBox_ColorMaps.addItem("brewer_diverging_brown_blue_green_7")
    self.comboBox_ColorMaps.addItem("brewer_diverging_brown_blue_green_6")
    self.comboBox_ColorMaps.addItem("brewer_diverging_brown_blue_green_5")
    self.comboBox_ColorMaps.addItem("brewer_diverging_brown_blue_green_4")
    self.comboBox_ColorMaps.addItem("brewer_diverging_brown_blue_green_3")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_green_9")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_green_8")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_green_7")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_green_6")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_green_5")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_green_4")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_green_3")
    self.comboBox_ColorMaps.addItem("brewer_sequential_yellow_orange_brown_9")
    self.comboBox_ColorMaps.addItem("brewer_sequential_yellow_orange_brown_8")
    self.comboBox_ColorMaps.addItem("brewer_sequential_yellow_orange_brown_7")
    self.comboBox_ColorMaps.addItem("brewer_sequential_yellow_orange_brown_6")
    self.comboBox_ColorMaps.addItem("brewer_sequential_yellow_orange_brown_5")
    self.comboBox_ColorMaps.addItem("brewer_sequential_yellow_orange_brown_4")
    self.comboBox_ColorMaps.addItem("brewer_sequential_yellow_orange_brown_3")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_purple_9")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_purple_8")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_purple_7")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_purple_6")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_purple_5")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_purple_4")
    self.comboBox_ColorMaps.addItem("brewer_sequential_blue_purple_3")


##############################################################################
################# load globe geometry
##############################################################################
def loadGlobeGeometry(self, variableToLoad=None):
    self.ren.RemoveAllViewProps()
    print("Loading NetCDF...")
    self.reader.Update()
    print("reading completed")

    #print(self.reader.GetOutput())

    cellDataToPointData = vtk.vtkCellDataToPointData()
    cellDataToPointData.SetInputData(self.reader.GetOutput())
    cellDataToPointData.ProcessAllArraysOn()
    cellDataToPointData.PassCellDataOn()
    cellDataToPointData.Update()

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
    goemetryFilter.SetInputConnection(cellDataToPointData.GetOutputPort())
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

    self.ren.AddActor(self.actor)
    self.ren.ResetCamera()
    self.iren.Render()
    print("render issued")

##############################################################################
################# load globe geometry
##############################################################################
def updateGlobeGeometry(self, variableName):
    if(variableName == None or variableName == ""):
        self.mapper.ScalarVisibilityOff()
        return
    else:
        self.mapper.ScalarVisibilityOn()
        self.mapper.GetInput().GetPointData().SetActiveScalars(variableName)
        self.mapper.SetLookupTable(self.ctf)
        self.mapper.Update()
        self.iren.Render()

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

