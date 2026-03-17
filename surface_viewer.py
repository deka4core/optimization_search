# surface_viewer.py
import numpy as np
from matplotlib import pyplot
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QComboBox, QLineEdit, QCheckBox
import pyqtgraph.opengl as gl
from surfaces import surface_data


class SurfaceViewer(QObject):
    """Класс для управления отрисовкой 3D поверхностей в GLViewWidget"""

    def __init__(self, gl_widget: gl.GLViewWidget,
                 combo: QComboBox,
                 x_interval: QLineEdit,
                 y_interval: QLineEdit,
                 axis_check: QCheckBox,
                 grid_check: QCheckBox,
                 axis_x: QLineEdit,
                 axis_y: QLineEdit,
                 z_scale: QLineEdit):
        super().__init__()

        self.gl_widget = gl_widget
        self.combo = combo
        self.x_interval = x_interval
        self.y_interval = y_interval
        self.axis_check = axis_check
        self.grid_check = grid_check
        self.axis_x = axis_x
        self.axis_y = axis_y
        self.z_scale = z_scale

        # Текущие элементы на сцене
        self.current_surface = None
        self.current_axis = None
        self.current_grid = None

        # Настройка начальных значений
        self._setup_defaults()

        # Подключение сигналов
        self._connect_signals()

        # Первоначальная отрисовка
        self.update_surface()

    def _setup_defaults(self):
        """Установка значений по умолчанию"""
        # Заполнение комбобокса
        self.combo.clear()
        self.combo.addItems(surface_data.keys())

        # Установка интервалов для первой функции
        first_func = list(surface_data.values())[0]
        self.x_interval.setText(f"{first_func['xmin']}, {first_func['xmax']}")
        self.y_interval.setText(f"{first_func['ymin']}, {first_func['ymax']}")

        # Интервалы осей по умолчанию
        self.axis_x.setText("-10, 10")
        self.axis_y.setText("-10, 10")

        # Масштаб Z по умолчанию
        self.z_scale.setText("1.0")

        # Чекбоксы по умолчанию
        self.axis_check.setChecked(True)
        self.grid_check.setChecked(True)

    def _connect_signals(self):
        """Подключение сигналов для автообновления"""
        self.combo.currentTextChanged.connect(self.update_surface)
        self.x_interval.textChanged.connect(self.update_surface)
        self.y_interval.textChanged.connect(self.update_surface)
        self.axis_check.stateChanged.connect(self.update_axis_grid)
        self.grid_check.stateChanged.connect(self.update_axis_grid)
        self.axis_x.textChanged.connect(self.update_axis_grid)
        self.axis_y.textChanged.connect(self.update_axis_grid)
        self.z_scale.textChanged.connect(self.update_surface)

    def _parse_interval(self, text: str, default_min=-5, default_max=5):
        """Парсинг интервала из текста вида 'min, max'"""
        try:
            parts = text.replace(' ', '').split(',')
            if len(parts) == 2:
                return float(parts[0]), float(parts[1])
        except:
            pass
        return default_min, default_max

    def _parse_float(self, text: str, default=1.0):
        """Парсинг числа с плавающей точкой"""
        try:
            return float(text.replace(',', '.'))
        except:
            return default

    def generate_surface_item(self, func, xmin, xmax, ymin, ymax, npoints=300, z_scale=1.0):
        """
        Создание поверхности с раскраской от matplotlib

        Возвращает:
            surface_item: GLSurfacePlotItem для отображения
            z_raw: исходные значения Z
            z_vis: масштабированные значения Z для визуализации
            z_min: минимум исходной функции
            z_max: максимум исходной функции
        """
        x = np.linspace(xmin, xmax, npoints)
        y = np.linspace(ymin, ymax, npoints)
        X, Y = np.meshgrid(x, y, indexing='ij')

        # Вычисляем исходные значения функции
        Z_raw = func(X, Y)
        Z_min = Z_raw.min()
        Z_max = Z_raw.max()

        # Масштабируем для визуализации с учетом пользовательского масштаба
        if Z_max != Z_min:
            Z_vis = (Z_raw - Z_min) / (Z_max - Z_min) * 10 * z_scale
        else:
            Z_vis = Z_raw * z_scale

        # Создаем цветовую карту
        norm = (Z_vis - Z_vis.min()) / (Z_vis.max() - Z_vis.min())
        cmap = pyplot.get_cmap("jet")
        colors = cmap(norm)

        # Создаем поверхность
        surface_item = gl.GLSurfacePlotItem(
            x=x,
            y=y,
            z=Z_vis,
            colors=colors,
            smooth=True,
            drawEdges=False,
            shader="shaded"
        )

        return surface_item, Z_raw, Z_vis, Z_min, Z_max

    def update_surface(self):
        """Обновление поверхности"""
        # Получаем выбранную функцию
        func_name = self.combo.currentText()
        if not func_name or func_name not in surface_data:
            return

        # Данные функции
        func_info = surface_data[func_name]

        # Парсим интервалы
        x_min, x_max = self._parse_interval(
            self.x_interval.text(),
            func_info['xmin'],
            func_info['xmax']
        )
        y_min, y_max = self._parse_interval(
            self.y_interval.text(),
            func_info['ymin'],
            func_info['ymax']
        )

        # Количество точек из данных функции или по умолчанию
        points = func_info.get('points', 300)

        # Масштаб Z
        z_scale = self._parse_float(self.z_scale.text(), 1.0)

        # Создаем поверхность с раскраской
        surface_item, _, _, _, _ = self.generate_surface_item(
            func=func_info['func'],
            xmin=x_min,
            xmax=x_max,
            ymin=y_min,
            ymax=y_max,
            npoints=points,
            z_scale=z_scale
        )

        # Удаляем старую поверхность
        if self.current_surface:
            self.gl_widget.removeItem(self.current_surface)

        # Добавляем новую
        self.gl_widget.addItem(surface_item)
        self.current_surface = surface_item

        # Обновляем оси и сетку (они могут быть перекрыты новой поверхностью)
        self.update_axis_grid()

    def update_axis_grid(self):
        """Обновление осей и сетки"""
        # Удаляем старые
        if self.current_axis:
            self.gl_widget.removeItem(self.current_axis)
            self.current_axis = None

        if self.current_grid:
            self.gl_widget.removeItem(self.current_grid)
            self.current_grid = None

        # Добавляем оси если нужно
        if self.axis_check.isChecked():
            x_min, x_max = self._parse_interval(self.axis_x.text(), -10, 10)
            y_min, y_max = self._parse_interval(self.axis_y.text(), -10, 10)

            axis_item = gl.GLAxisItem()
            axis_item.setSize(x=x_max - x_min, y=y_max - y_min, z=5)
            axis_item.translate(
                (x_min + x_max) / 2,
                (y_min + y_max) / 2,
                0
            )

            self.gl_widget.addItem(axis_item)
            self.current_axis = axis_item

        # Добавляем сетку если нужно
        if self.grid_check.isChecked():
            grid_item = gl.GLGridItem()
            grid_item.setSpacing(1, 1, 1)

            self.gl_widget.addItem(grid_item)
            self.current_grid = grid_item