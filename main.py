from PySide6.QtWidgets import QApplication, QVBoxLayout
import pyqtgraph.opengl as gl
from PySide6.QtUiTools import QUiLoader
from surfaces import surface_data
import numpy as np
import sys
import os


# Простой загрузчик UI
class CustomLoader(QUiLoader):
    def createWidget(self, classname, parent=None, name=''):
        return super().createWidget(classname, parent, name)


surface_item = None
current_func = None
current_zmin = None
current_zmax = None
gd_method = None


def generate_surface(func, xmin, xmax, ymin, ymax, npoints=300):
    from matplotlib import pyplot
    x = np.linspace(xmin, xmax, npoints)
    y = np.linspace(ymin, ymax, npoints)
    X, Y = np.meshgrid(x, y, indexing='ij')
    Z_raw = func(X, Y)
    Z_min = Z_raw.min()
    Z_max = Z_raw.max()
    if Z_max != Z_min:
        Z_vis = (Z_raw - Z_min) / (Z_max - Z_min) * 10
    else:
        Z_vis = Z_raw

    norm = (Z_vis - Z_vis.min()) / (Z_vis.max() - Z_vis.min())
    cmap = pyplot.get_cmap("jet")
    colors = cmap(norm)
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


def update_surface():
    global surface_item, current_func, current_zmin, current_zmax

    try:
        xmin = float(window.lineEdit.text())
        xmax = float(window.lineEdit_2.text())
        ymin = float(window.lineEdit_3.text())
        ymax = float(window.lineEdit_4.text())
        npoints = int(window.lineEdit_5.text())
    except:
        window.textEdit.append("Ошибка ввода параметров")
        return

    name = window.comboBox.currentText()
    if name not in surface_data:
        return

    data = surface_data[name]
    func = data["func"]

    surface, Z_raw, Z_vis, zmin, zmax = generate_surface(
        func,
        xmin, xmax,
        ymin, ymax,
        npoints
    )

    current_zmin = zmin
    current_zmax = zmax
    current_func = func

    if surface_item:
        view.removeItem(surface_item)

    view.addItem(surface)
    surface_item = surface

    window.textEdit.append(f"Построена поверхность: {name}")

    # Обновляем текст кнопки
    window.pushButton.setText("Запустить ГС")


def gradient_descent():
    global current_func, current_zmin, current_zmax

    if current_func is None:
        window.textEdit.append("Сначала построй поверхность")
        return

    try:
        x_start = float(window.x_field.text()) if window.x_field.text() else 0
        y_start = float(window.y_field.text()) if window.y_field.text() else 0
        step_size = float(window.step_field.text())
        max_iter = int(window.iterations_field.text())
        delay = int(window.delay_field.text())
    except ValueError:
        window.textEdit.append("Ошибка параметров ГС")
        return

    # Очищаем старую траекторию
    global point_item
    point_item.setData(pos=np.array([]))

    # Запускаем градиентный спуск
    run_gradient_descent(x_start, y_start, step_size, max_iter, delay)


def run_gradient_descent(x_start, y_start, step_size, max_iter, delay_ms):
    global current_func, point_item

    # Функция для численного градиента
    def gradient(x, y, h=1e-5):
        df_dx = (current_func(x + h, y) - current_func(x - h, y)) / (2 * h)
        df_dy = (current_func(x, y + h) - current_func(x, y - h)) / (2 * h)
        return df_dx, df_dy

    x, y = x_start, y_start
    points = [(x, y, current_func(x, y))]

    window.pushButton.setText("Остановить")
    window.pushButton.clicked.disconnect()
    window.pushButton.clicked.connect(stop_gradient_descent)

    # Запоминаем для остановки
    global gd_running
    gd_running = True

    for i in range(max_iter):
        if not gd_running:
            window.textEdit.append("ГС остановлен")
            break

        z = current_func(x, y)
        points.append((x, y, z))

        # Обновляем точку
        point_item.setData(pos=np.array([[x, y, z]]))

        # Обновляем траекторию (последние 100 точек)
        if len(points) > 1:
            traj_points = np.array(points[-100:])
            trajectory_item.setData(pos=traj_points)

        # Вычисляем градиент
        grad_x, grad_y = gradient(x, y)

        # Проверка на сходимость
        if np.sqrt(grad_x ** 2 + grad_y ** 2) < 1e-6:
            window.textEdit.append(f"Сошлись на итерации {i + 1}")
            break

        # Обновляем координаты
        x_new = x - step_size * grad_x
        y_new = y - step_size * grad_y

        # Уменьшаем шаг если надо
        if current_func(x_new, y_new) > z:
            step_size *= 0.5
            window.textEdit.append(f"Шаг уменьшен до {step_size:.6f}")

        x, y = x_new, y_new

        # Задержка для визуализации
        if delay_ms > 0:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(delay_ms, lambda: None)
            QApplication.processEvents()

    # Возвращаем кнопку в исходное состояние
    window.pushButton.setText("Выполнить")
    window.pushButton.clicked.disconnect()
    window.pushButton.clicked.connect(on_execute_clicked)
    gd_running = False


def stop_gradient_descent():
    global gd_running
    gd_running = False


def on_execute_clicked():
    if surface_item is None:
        update_surface()
    else:
        gradient_descent()


def on_function_changed():
    name = window.comboBox.currentText()
    if name not in surface_data:
        return

    data = surface_data[name]
    window.lineEdit.setText(str(data["xmin"]))
    window.lineEdit_2.setText(str(data["xmax"]))
    window.lineEdit_3.setText(str(data["ymin"]))
    window.lineEdit_4.setText(str(data["ymax"]))


def toggle_axes(state):
    if state:
        axis.show()
    else:
        axis.hide()


def toggle_grid(state):
    if state:
        grid.show()
    else:
        grid.hide()


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

# Загружаем UI
loader = CustomLoader()
current_dir = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(current_dir, "ui", "main_window.ui")
window = loader.load(ui_path)

# ============= ИСПРАВЛЕНО: теперь просто добавляем виджет в контейнер =============
# Получаем контейнер (теперь это QWidget, а не QOpenGLWidget)
container = window.openGLWidget

# Создаем layout для контейнера
layout = QVBoxLayout(container)
layout.setContentsMargins(0, 0, 0, 0)

# Создаем GLViewWidget и добавляем в layout
view = gl.GLViewWidget()
view.setStyleSheet("background-color: black;")
layout.addWidget(view)

# Сетка
grid = gl.GLGridItem()
grid.setSize(20, 20)
grid.setSpacing(1, 1)
grid.translate(0, 0, -1)
view.addItem(grid)

# Оси
axis = gl.GLAxisItem()
axis.setSize(5, 5, 5)
view.addItem(axis)

# Точка для отображения
point_item = gl.GLScatterPlotItem(
    size=15,
    color=(1, 0, 0, 1)
)
point_item.setGLOptions('opaque')
view.addItem(point_item)

# Траектория
trajectory_item = gl.GLLinePlotItem(
    color=(1, 0.5, 0, 1),
    width=2,
    antialias=True
)
view.addItem(trajectory_item)
# =================================================================================

# Заполняем комбобокс
for name in surface_data.keys():
    window.comboBox.addItem(name)

# Устанавливаем значения по умолчанию
window.step_field.setText("0.01")
window.iterations_field.setText("100")
window.delay_field.setText("50")
window.lineEdit_5.setText("100")

# Подключаем сигналы
window.comboBox.currentTextChanged.connect(on_function_changed)
window.pushButton.clicked.connect(on_execute_clicked)
window.checkBox.stateChanged.connect(toggle_axes)
window.checkBox_2.stateChanged.connect(toggle_grid)

# Устанавливаем первую функцию
on_function_changed()

window.show()
sys.exit(app.exec())