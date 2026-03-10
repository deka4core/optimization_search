import numpy as np
from OpenGL.GL import *


class PathVisualization:
    """Класс для визуализации пути оптимизации"""

    @staticmethod
    def draw_path(points, func, color=(1.0, 1.0, 0.0)):
        """Отрисовка пути оптимизации в 3D"""
        if len(points) < 2:
            return

        # Получаем Z-координаты для точек пути
        path_3d = []
        for x, y in points:
            z = func(x, y)
            path_3d.append((x, y, z))

        glDisable(GL_LIGHTING)

        # Отрисовка линии пути
        glColor3f(*color)
        glLineWidth(2)
        glBegin(GL_LINE_STRIP)
        for x, y, z in path_3d:
            glVertex3f(x, y, z)
        glEnd()

        # Отрисовка точек пути
        glPointSize(6)
        glBegin(GL_POINTS)
        for i, (x, y, z) in enumerate(path_3d):
            if i == 0:
                glColor3f(0, 1, 0)  # Стартовая точка - зеленая
            elif i == len(path_3d) - 1:
                glColor3f(1, 0, 0)  # Конечная точка - красная
            else:
                glColor3f(1, 1, 0)  # Промежуточные точки - желтые
            glVertex3f(x, y, z)
        glEnd()

        glEnable(GL_LIGHTING)

    @staticmethod
    def draw_projection(points, func, plane='xy', color=(0.5, 0.5, 0.5)):
        """Отрисовка проекции пути на плоскость"""
        if len(points) < 2:
            return

        glDisable(GL_LIGHTING)
        glColor3f(*color)
        glLineWidth(1)
        glBegin(GL_LINE_STRIP)

        for x, y in points:
            z = func(x, y)
            if plane == 'xy':
                glVertex3f(x, y, 0)
            elif plane == 'xz':
                glVertex3f(x, 0, z)
            elif plane == 'yz':
                glVertex3f(0, y, z)

        glEnd()
        glEnable(GL_LIGHTING)