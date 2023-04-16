import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5 import QtCore as qCore
from PyQt5.QtWidgets import QWidget, QPushButton, QLineEdit, QInputDialog
import modules.utils as Utils
import math

class Gradient(QtWidgets.QWidget):
    gradientChanged = Signal()

    def __init__(self, g_type, smain=None, gradient=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        if gradient:
            self._gradient = gradient

        if smain:
            self.main = smain

        if g_type:
            self.g_type = g_type

        else:
            self._gradient = [
                (0.0, '#000000'),
                (1.0, '#ffffff'),
            ]

        # Stop point handle sizes.
        self._handle_w = 10
        self._handle_h = 10

        self._drag_position = None

    def paintEvent(self, e):

        if self.g_type == "contour":
            if(self.main.newMinContours == None or self.main.newMaxContours == None):
                return
        if self.g_type == "color":
            if(self.main.newMin == None or self.main.newMax == None):
                return
        painter = QtGui.QPainter(self)
        width = painter.device().width()
        height = painter.device().height()/2

        # Draw the linear horizontal gradient.
        gradient = QtGui.QLinearGradient(0, 0, width, 0)
        for stop, color in self._gradient:
            gradient.setColorAt(stop, QtGui.QColor(color))

        rect = QtCore.QRect(0, 0, width, int(height))
        painter.fillRect(rect, gradient)

        pen = QtGui.QPen()
        painter.setFont(QtGui.QFont("Arial", 8))
        y = painter.device().height() / 4

        
        # Draw the stop handles.
        for stop, _ in self._gradient:
            pen.setColor(QtGui.QColor('white'))
            painter.setPen(pen)
            painter.drawLine(int(stop * width), int(y - self._handle_h), int(stop * width), int(y + self._handle_h))
            
            pen.setColor(QtGui.QColor(175, 199, 242, 255))
            painter.setPen(pen)

            if self.g_type == "contour":
                newRange = self.main.newMaxContours - self.main.newMinContours
                newValue = (stop * newRange) + self.main.newMinContours
                if(stop == 0.0):
                    painter.drawText(int(stop * width)+2,int(y)+20, str(self.truncate(newValue,1)))
                elif(stop == 1.0):
                    painter.drawText(int(stop * width)-40,int(y)+20, str(self.truncate(newValue,1)))
                else:
                    painter.drawText(int(stop * width)-10,int(y)+20, str(self.truncate(newValue,1)))
            if self.g_type == "color":
                newRange = self.main.newMax - self.main.newMin
                newValue = (stop * newRange) + self.main.newMin
                if(stop == 0.0):
                    painter.drawText(int(stop * width)+2,int(y)+20, str(self.truncate(newValue,1)))
                elif(stop == 1.0):
                    painter.drawText(int(stop * width)-40,int(y)+20, str(self.truncate(newValue,1)))
                else:
                    painter.drawText(int(stop * width)-10,int(y)+20, str(self.truncate(newValue,1)))


            #if(self.main.newMin!=None):

            pen.setColor(QtGui.QColor('red'))
            painter.setPen(pen)
            

            rect = QtCore.QRect(
                int(stop * width - self._handle_w / 2),
                int(y - self._handle_h / 2),
                int(self._handle_w),
                int(self._handle_h)
            )
            painter.drawRect(rect)
        #self.gradientChanged.emit()
        painter.end()

    def truncate(self, f, n):
        return math.floor(f * 10 ** n) / 10 ** n

    def sizeHint(self):
        return QtCore.QSize(200, 50)

    def _sort_gradient(self):
        self._gradient = sorted(self._gradient, key=lambda g: g[0])

    def _constrain_gradient(self):
        self._gradient = [
            # Ensure values within valid range.
            (max(0.0, min(1.0, stop)), color)
            for stop, color in self._gradient
        ]

    def setGradient(self, gradient):
        assert all([0.0 <= stop <= 1.0 for stop, _ in gradient])
        self._gradient = gradient
        self._constrain_gradient()
        self._sort_gradient()
        self.gradientChanged.emit()

    def gradient(self):
        return self._gradient

    @property
    def _end_stops(self):
        return [0, len(self._gradient) - 1]

    def addStop(self, stop, color=None, refresh = True):
        # Stop is a value 0...1, find the point to insert this stop
        # in the list.
        assert 0.0 <= stop <= 1.0

        for n, g in enumerate(self._gradient):
            if g[0] > stop:
                # Insert before this entry, with specified or next color.
                self._gradient.insert(n, (stop, color or g[1]))
                break
        self._constrain_gradient()
        if(refresh == True):
            self.gradientChanged.emit()
        self.update()

    def removeStopAtPosition(self, n, refresh = True):
        if n not in self._end_stops:
            del self._gradient[n]
            if(refresh == True):
                self.gradientChanged.emit()
            self.update()

    def setColorAtPosition(self, n, color):
        if n < len(self._gradient):
            stop, _ = self._gradient[n]
            self._gradient[n] = stop, color
            self.gradientChanged.emit()
            self.update()

    def chooseColorAtPosition(self, n, current_color=None):
        dlg = QtWidgets.QColorDialog(self)
        if current_color:
            dlg.setCurrentColor(QtGui.QColor(current_color))

        if dlg.exec_():
            self.setColorAtPosition(n, dlg.currentColor().toRgb())

    def _find_stop_handle_for_event(self, e, to_exclude=None):
        width = self.width()
        height = self.height()/2
        midpoint = height / 4

        # Are we inside a stop point? First check y.
        if (
                e.y() >= midpoint - self._handle_h and
                e.y() <= midpoint + self._handle_h
        ):

            for n, (stop, color) in enumerate(self._gradient):
                if to_exclude and n in to_exclude:
                    # Allow us to skip the extreme ends of the gradient.
                    continue
                if (
                        e.x() >= stop * width - self._handle_w and
                        e.x() <= stop * width + self._handle_w
                ):
                    return n

    def mousePressEvent(self, e):
        # We're in this stop point.
        if e.button() == Qt.RightButton:
            n = self._find_stop_handle_for_event(e)
            if n is not None:
                _, color = self._gradient[n]
                self.chooseColorAtPosition(n, color)

        elif e.button() == Qt.LeftButton:
            n = self._find_stop_handle_for_event(e, to_exclude=self._end_stops)
            if n is not None:
                # Activate drag mode.
                self._drag_position = n
        elif e.button() == Qt.MiddleButton:
            #text, ok = QInputDialog.getText(self, 'Set Value', 'Please enter a value for this stop.')

            inputDialog = QInputDialog(None)
            inputDialog.setInputMode(QInputDialog.TextInput)
            inputDialog.setLabelText('Please enter a value for this stop:')
            Utils.applyTheme(inputDialog)
            inputDialog.setWindowFlags(qCore.Qt.FramelessWindowHint)
            ok = inputDialog.exec_()
            if not ok:
                return
            text = inputDialog.textValue()

            if (text.replace('.','',1).isdigit() == False): # if not a number
                return
            if self.g_type == "color":
                if(float(text) <=self.main.newMin or float(text) >=self.main.newMax): # Trying to set out of range values.
                    return
                
            if self.g_type == "contour":
                if(float(text) <=self.main.newMinContours or float(text) >=self.main.newMaxContours): # Trying to set out of range values.
                    return
            n = self._find_stop_handle_for_event(e)
            normalized_value, color = self._gradient[n]
            self.removeStopAtPosition(n, refresh=False)
            if self.g_type == "color":
                normalized_user_input = (float(text) - self.main.newMin)/(self.main.newMax - self.main.newMin)
            if self.g_type == "contour":
                normalized_user_input = (float(text) - self.main.newMinContours)/(self.main.newMaxContours - self.main.newMinContours)
            self.addStop(float(normalized_user_input), color, refresh = False)
            self._drag_position = None
            self._sort_gradient()
            self.gradientChanged.emit()

    def mouseReleaseEvent(self, e):
        self._drag_position = None
        self._sort_gradient()
        self.gradientChanged.emit()

    def mouseMoveEvent(self, e):
        # If drag active, move the stop.
        if self._drag_position:
            stop = e.x() / self.width()
            _, color = self._gradient[self._drag_position]
            self._gradient[self._drag_position] = stop, color
            self._constrain_gradient()
            self.update()
            self.gradientChanged.emit()  # disable this line for stopping continuous cmap updates.

    def mouseDoubleClickEvent(self, e):
        # Calculate the position of the click relative 0..1 to the width.
        n = self._find_stop_handle_for_event(e)
        if n:
            self._sort_gradient()  # Ensure ordered.
            # Delete existing, if not at the ends.
            if n > 0 and n < len(self._gradient) - 1:
                self.removeStopAtPosition(n)

        else:
            stop = e.x() / self.width()
            self.addStop(stop)
