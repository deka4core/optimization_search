# main.py
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtUiTools import QUiLoader
import pyqtgraph.opengl as gl

from surface_viewer import SurfaceViewer

class CustomLoader(QUiLoader):
    def createWidget(self, classname, parent=None, name=''):
        if classname == 'GLViewWidget':
            return gl.GLViewWidget(parent)
        return super().createWidget(classname, parent, name)

app = QApplication(sys.argv)

loader = CustomLoader()
window = loader.load("ui/main_window.ui")

# Настройка отступов
view = window.openGLWidget
parent_layout = view.parent().layout()
parent_layout.setContentsMargins(5, 0, 5, 0)

# Создание менеджера поверхностей
surface_viewer = SurfaceViewer(
    gl_widget=view,
    combo=window.comboBox,
    x_interval=window.lineEdit,
    y_interval=window.lineEdit_2,
    axis_check=window.checkBox,
    grid_check=window.checkBox_2,
    axis_x=window.lineEdit_3,
    axis_y=window.lineEdit_4,
    z_scale=window.lineEdit_5
)

window.show()
sys.exit(app.exec())