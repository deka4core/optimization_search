# gradient_descent.py
import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtWidgets import QLineEdit, QPushButton, QTextEdit
import pyqtgraph.opengl as gl
from surfaces import surface_data


class GradientDescentVisualizer(QObject):
    """Класс для визуализации градиентного спуска с постоянным шагом"""

    # Сигналы для обновления интерфейса
    iteration_completed = Signal(int, float, float, float)  # номер итерации, x, y, значение функции
    algorithm_finished = Signal()
    algorithm_error = Signal(str)

    def __init__(self, gl_widget: gl.GLViewWidget,
                 x_field: QLineEdit,
                 y_field: QLineEdit,
                 step_field: QLineEdit,
                 iterations_field: QLineEdit,
                 delay_field: QLineEdit,
                 start_button: QPushButton,
                 console: QTextEdit,
                 surface_viewer):  # ссылка на SurfaceViewer для получения текущей функции
        super().__init__()

        self.gl_widget = gl_widget
        self.x_field = x_field
        self.y_field = y_field
        self.step_field = step_field
        self.iterations_field = iterations_field
        self.delay_field = delay_field
        self.start_button = start_button
        self.console = console
        self.surface_viewer = surface_viewer

        # Таймер для пошагового выполнения
        self.timer = QTimer()
        self.timer.timeout.connect(self._next_iteration)

        # Переменные для хранения состояния алгоритма
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_iteration = 0
        self.max_iterations = 0
        self.step_size = 0.0
        self.trajectory_points = []  # для хранения траектории
        self.trajectory_line = None  # линия траектории
        self.current_point = None  # текущая точка

        # Подключение сигналов
        self.start_button.clicked.connect(self.start_algorithm)
        self.iteration_completed.connect(self._update_console)
        self.algorithm_finished.connect(self._on_algorithm_finished)
        self.algorithm_error.connect(self._show_error)

    def _parse_float(self, text: str, default=0.0):
        """Парсинг числа с плавающей точкой"""
        try:
            return float(text.replace(',', '.').strip())
        except (ValueError, AttributeError):
            return default

    def _parse_int(self, text: str, default=0):
        """Парсинг целого числа"""
        try:
            return int(text.strip())
        except (ValueError, AttributeError):
            return default

    def _get_current_function(self):
        """Получение текущей функции из SurfaceViewer"""
        func_name = self.surface_viewer.combo.currentText()
        if func_name and func_name in surface_data:
            return surface_data[func_name]['func']
        return None

    def _numerical_gradient(self, func, x, y, epsilon=1e-8):
        """Вычисление градиента численным методом"""
        grad_x = (func(x + epsilon, y) - func(x - epsilon, y)) / (2 * epsilon)
        grad_y = (func(x, y + epsilon) - func(x, y - epsilon)) / (2 * epsilon)
        return grad_x, grad_y

    def _create_trajectory_line(self, points):
        """Создание линии траектории"""
        if len(points) < 2:
            return None

        points_array = np.array(points)
        line_item = gl.GLLinePlotItem(
            pos=points_array,
            color=(1.0, 0.0, 0.0, 1.0),  # красный цвет
            width=3,
            antialias=True,
            mode='line_strip'
        )
        return line_item

    def _create_point_marker(self, x, y, z):
        """Создание маркера для текущей точки"""
        marker = gl.GLScatterPlotItem(
            pos=np.array([[x, y, z]]),
            color=(1.0, 1.0, 0.0, 1.0),  # желтый цвет
            size=15,
            pxMode=True
        )
        return marker

    def _get_function_value(self, func, x, y):
        """Получение значения функции с учетом масштаба Z"""
        try:
            # Получаем сырое значение функции
            z_raw = func(x, y)

            # Применяем тот же масштаб, что и в SurfaceViewer
            z_scale = self._parse_float(self.surface_viewer.z_scale.text(), 1.0)

            # Получаем интервалы для нормализации (как в SurfaceViewer)
            func_name = self.surface_viewer.combo.currentText()
            if func_name and func_name in surface_data:
                func_info = surface_data[func_name]
                x_min, x_max = self.surface_viewer._parse_interval(
                    self.surface_viewer.x_interval.text(),
                    func_info['xmin'],
                    func_info['xmax']
                )
                y_min, y_max = self.surface_viewer._parse_interval(
                    self.surface_viewer.y_interval.text(),
                    func_info['ymin'],
                    func_info['ymax']
                )

                # Создаем небольшую сетку для оценки диапазона
                test_x = np.linspace(x_min, x_max, 50)
                test_y = np.linspace(y_min, y_max, 50)
                X, Y = np.meshgrid(test_x, test_y, indexing='ij')
                Z_test = func(X, Y)
                z_min, z_max = Z_test.min(), Z_test.max()

                # Нормализуем как в SurfaceViewer
                if z_max != z_min:
                    z_vis = (z_raw - z_min) / (z_max - z_min) * 10 * z_scale
                else:
                    z_vis = z_raw * z_scale
            else:
                z_vis = z_raw * z_scale

            return z_raw, z_vis
        except Exception as e:
            print(f"Error computing function value: {e}")
            return 0, 0

    def start_algorithm(self):
        """Запуск алгоритма градиентного спуска"""
        # Получаем начальные параметры
        self.current_x = self._parse_float(self.x_field.text(), 0.0)
        self.current_y = self._parse_float(self.y_field.text(), 0.0)
        self.step_size = self._parse_float(self.step_field.text(), 0.1)
        self.max_iterations = self._parse_int(self.iterations_field.text(), 100)
        delay = self._parse_int(self.delay_field.text(), 100)

        # Проверка наличия функции
        func = self._get_current_function()
        if func is None:
            self.algorithm_error.emit("Не выбрана функция для оптимизации")
            return

        # Очищаем предыдущую траекторию
        self._clear_trajectory()

        # Инициализация
        self.current_iteration = 0
        self.trajectory_points = []

        # Получаем начальное значение функции
        _, z_vis = self._get_function_value(func, self.current_x, self.current_y)
        self.trajectory_points.append([self.current_x, self.current_y, z_vis])

        # Создаем начальную точку
        self.current_point = self._create_point_marker(self.current_x, self.current_y, z_vis)
        self.gl_widget.addItem(self.current_point)

        # Вывод в консоль
        self.console.clear()
        self.iteration_completed.emit(0, self.current_x, self.current_y, z_vis)

        # Настройка и запуск таймера
        self.timer.setInterval(max(10, min(1000, delay)))  # ограничиваем задержку
        self.timer.start()

        # Блокируем кнопку на время выполнения
        self.start_button.setEnabled(False)

    def _next_iteration(self):
        """Выполнение следующей итерации"""
        if self.current_iteration >= self.max_iterations:
            self.timer.stop()
            self.algorithm_finished.emit()
            return

        func = self._get_current_function()
        if func is None:
            self.timer.stop()
            self.algorithm_error.emit("Функция не найдена")
            return

        try:
            # Вычисляем градиент
            grad_x, grad_y = self._numerical_gradient(func, self.current_x, self.current_y)

            # Обновляем позицию (градиентный спуск: идем против градиента)
            new_x = self.current_x - self.step_size * grad_x
            new_y = self.current_y - self.step_size * grad_y

            # Получаем значение функции в новой точке
            _, z_vis = self._get_function_value(func, new_x, new_y)

            # Обновляем текущую позицию
            self.current_x = new_x
            self.current_y = new_y
            self.current_iteration += 1

            # Добавляем точку в траекторию
            self.trajectory_points.append([self.current_x, self.current_y, z_vis])

            # Обновляем визуализацию
            self._update_visualization()

            # Вывод в консоль
            self.iteration_completed.emit(
                self.current_iteration,
                self.current_x,
                self.current_y,
                z_vis
            )

        except Exception as e:
            self.timer.stop()
            self.algorithm_error.emit(f"Ошибка на итерации {self.current_iteration}: {str(e)}")

    def _update_visualization(self):
        """Обновление визуализации траектории"""
        # Удаляем старую линию траектории
        if self.trajectory_line:
            self.gl_widget.removeItem(self.trajectory_line)

        # Создаем новую линию траектории
        if len(self.trajectory_points) >= 2:
            self.trajectory_line = self._create_trajectory_line(self.trajectory_points)
            if self.trajectory_line:
                self.gl_widget.addItem(self.trajectory_line)

        # Обновляем позицию текущей точки
        if self.current_point:
            self.gl_widget.removeItem(self.current_point)

        func = self._get_current_function()
        if func:
            _, z_vis = self._get_function_value(func, self.current_x, self.current_y)
            self.current_point = self._create_point_marker(self.current_x, self.current_y, z_vis)
            self.gl_widget.addItem(self.current_point)

    def _clear_trajectory(self):
        """Очистка траектории"""
        if self.trajectory_line:
            self.gl_widget.removeItem(self.trajectory_line)
            self.trajectory_line = None

        if self.current_point:
            self.gl_widget.removeItem(self.current_point)
            self.current_point = None

    @Slot(int, float, float, float)
    def _update_console(self, iteration, x, y, z):
        """Обновление консоли"""
        if iteration == 0:
            self.console.append("=" * 50)
            self.console.append("ЗАПУСК ГРАДИЕНТНОГО СПУСКА")
            self.console.append("=" * 50)
            self.console.append(f"Начальная точка: ({x:.6f}, {y:.6f})")
            self.console.append(f"Начальное значение: {z:.6f}")
            self.console.append(f"Шаг: {self.step_size:.6f}")
            self.console.append(f"Максимум итераций: {self.max_iterations}")
            self.console.append("-" * 50)
        else:
            self.console.append(f"Итерация {iteration:3d}: ({x:.6f}, {y:.6f}) -> {z:.6f}")

    @Slot()
    def _on_algorithm_finished(self):
        """Обработка завершения алгоритма"""
        self.console.append("-" * 50)
        self.console.append("АЛГОРИТМ ЗАВЕРШЕН")
        self.console.append(f"Финальная точка: ({self.current_x:.6f}, {self.current_y:.6f})")

        func = self._get_current_function()
        if func:
            z_raw, z_vis = self._get_function_value(func, self.current_x, self.current_y)
            self.console.append(f"Финальное значение: {z_vis:.6f} (исходное: {z_raw:.6f})")

        self.console.append("=" * 50)

        # Разблокируем кнопку
        self.start_button.setEnabled(True)

    @Slot(str)
    def _show_error(self, error_message):
        """Отображение ошибки"""
        self.console.append(f"ОШИБКА: {error_message}")
        self.start_button.setEnabled(True)

    def stop_algorithm(self):
        """Остановка алгоритма"""
        if self.timer.isActive():
            self.timer.stop()
            self.algorithm_finished.emit()