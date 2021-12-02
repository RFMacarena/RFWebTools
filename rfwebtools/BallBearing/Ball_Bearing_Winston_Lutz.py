#
# Ball_Bearing_Winston_Lutz
#
# Script para realizar el test de Winston_Lutz en los Versa, a partir de registros dicom del iview.
# Analiza independientemente la dependencia con el brazo, colimador y mesa.
# Para el gantry utiliza cuatro imagenes dcm con los giros 0, 90, 180 y 270.
# Para el colimador utiliza cuatro imagenes dcm con los giros 0, 90, 180 y 270.
# Para la mesa utiliza tres imagenes dcm con los giros 0, 90 y 270.
# Las imagenes Gantry 0, Colimador 0 y Mesa 0 son la misma.
#
# En las imagenes Gantry la coordenada "y" de la matriz dicom es siempre la coordenada "y" real,
# pero la coordenada "x" de la matriz dicom es la coordenada "x" real para las incidencias 0 y 180, y
# la coordenada "z" real para las incidencias 90 y 270.
# En las incidencias 0 y 180, la coordenada "x" real cambia de signo y en las incidencias 90 y 270 lo hace la "z" real.
# Internamente en los casos pertinentes el script hace un flip left-right.
#
# Aplica filtro de mediana 3x3.
#
# En las imagenes Colimador y Mesa las coordenadas "x" e "y" de la matriz dicom coinciden con las coordenadas
# "x" e "y" reales.
#
# Version Mayo 2021 @JMacias
#

# Librerias
import tkinter as tk
from tkinter.filedialog import askopenfilename
import pydicom as dicom
import sys
import numpy as np
import cv2
from PIL import Image as PIL_image
from PIL import ImageTk
from os import remove
from skimage.feature import canny
import matplotlib.pyplot as plt
from skimage.transform import hough_circle, hough_circle_peaks
from skimage.transform import hough_line, hough_line_peaks
import math
import os
import time
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Definicion de objeto principal, relacionado con cada una de las imagenes dcm implicadas
# Cada una de las cuatro imagenes de gantry, cuatro del colimador y tres de la mesa
class Objeto_ppal:
    def __init__(self):
        self.nombre_fichero = None
        self.gantry = None
        self.colimador = None
        self.mesa = None
        self.matriz = None

        # Circulo
        self.centro_circulo_pixeles = None
        self.radio_pixel = None

        # Rectas del campo de radiacion
        self.rectas = []
        for i in range(4):
            self.rectas.append(Recta())

        # Pareja de rectas diagonales
        self.diagonales = []
        for i in range(2):
            self.diagonales.append(Recta())

        self.centro_radiacion_pixeles = None

# Definición de objeto recta a partir de un par de puntos
class Recta:
    def __init__(self):
        self.P0 = None
        self.P1 = None

# Clase principal del Script.
# Lanza el escritorio inicial-
class Ball_bearing:
    def __init__(self):
        self.titulo = "Test Winston-Lutz para Ball bearing Elekta V1.0"
        self.Define_escritorio()

    def Define_escritorio(self):
        # Zoom
        self.zoom_i = 300
        self.zoom_f = 700

        # Define escritorio principal
        self.Title = self.titulo
        ancho_ventana = 1000
        alto_ventana = 710
        padx_ppal = 5
        pady_ppal = 5
        geometria_ventana = str(ancho_ventana + 3 * padx_ppal) + "x" + str(alto_ventana + 2 * pady_ppal)

        self.root = tk.Tk()
        self.root.geometry(geometria_ventana)
        self.root.title(self.Title)

        self.canvas1_ppal = tk.Canvas(self.root, bg="blue", height=200, width=200)
        self.canvas1_ppal.grid()
        self.canvas1_ppal.place(x=padx_ppal, y=pady_ppal)

        # Menu
        self.popup_menu = tk.Menu(self.root, tearoff=0)
        self.popup_menu.add_command(label="1. Abrir Imagen 'Magnitud' y 'Angulacion.",
                                    command=lambda: self.Abre_imagen(int(self.E345.get()), int(self.E346.get()),
                                                                     int(self.E347.get())))
        self.popup_menu.add_command(label="   Ver Imagen seleccionada 'Magnitud' y 'Angulacion.",command=lambda: self.Ver_imagen())
        self.popup_menu.add_command(label="2. Calcular", command=lambda: self.Calcular())
        self.canvas1_ppal.bind("<Button-3>", self.popup)
        self.popup_menu.add_command(label="3. Genera informe", command=lambda: self.Genera_Informe())

        # Botones
        self.btn1 = tk.Button(self.root, text="Zoom -", command=lambda: self.zoom_update("-"))
        self.btn1.place(x=50, y=220)
        self.btn2 = tk.Button(self.root, text="Zoom +", command=lambda: self.zoom_update("+"))
        self.btn2.place(x=120, y=220)

        self.var = tk.BooleanVar()
        self.check_box_figuras = tk.Checkbutton(self.root, text="Ver rectas y circulo", variable=self.var)
        self.check_box_figuras.place(x=50, y=250)
        self.check_box_figuras.select()

        # Magnitud a referenciar, gantry, colimador o mesa.
        self.L000 = tk.Label(self.root)
        self.L000.place(x=210, y=0)
        self.L000['text'] = "Magnitud: "
        self.radiobutton_magnitud = tk.IntVar()
        self.check_gantry = tk.Radiobutton(self.root, text="Gantry", variable=self.radiobutton_magnitud, value=0)
        self.check_gantry.place(x=290, y=0)
        self.check_colimador = tk.Radiobutton(self.root, text="Colimador", variable=self.radiobutton_magnitud, value=1)
        self.check_colimador.place(x=355, y=0)
        self.check_mesa = tk.Radiobutton(self.root, text="Mesa", variable=self.radiobutton_magnitud, value=2)
        self.check_mesa.place(x=440, y=0)
        self.check_gantry.select()

        # Angulacion correspondiente
        self.L001 = tk.Label(self.root)
        self.L001.place(x=210, y=20)
        self.L001['text'] = "Angulacion: "
        self.radiobutton_orientacion = tk.IntVar()
        self.check_0 = tk.Radiobutton(self.root, text="0", variable=self.radiobutton_orientacion, value=0)
        self.check_0.place(x=290, y=20)
        self.check_90 = tk.Radiobutton(self.root, text="90", variable=self.radiobutton_orientacion, value=1)
        self.check_90.place(x=355, y=20)
        self.check_180 = tk.Radiobutton(self.root, text="180", variable=self.radiobutton_orientacion, value=2)
        self.check_180.place(x=440, y=20)
        self.check_270 = tk.Radiobutton(self.root, text="270", variable=self.radiobutton_orientacion, value=3)
        self.check_270.place(x=510, y=20)
        self.check_0.select()

        # Parametros Filtro Canny
        self.L345 = tk.Label(self.root)
        self.L345.place(x=210, y=45)
        self.L345['text'] = "Ancho Gaussiana. Canny:"
        self.E345 = tk.Entry(self.root, width=5)
        self.E345.place(x=210, y=65)
        self.E345.insert(0, "2")

        self.L346 = tk.Label(self.root)
        self.L346.place(x=210, y=85)
        self.L346['text'] = "Umbral bajo histéresis. Canny:"
        self.E346 = tk.Entry(self.root, width=5)
        self.E346.place(x=210, y=105)
        self.E346.insert(0, "5")

        self.L347 = tk.Label(self.root)
        self.L347.place(x=210, y=125)
        self.L347['text'] = "Umbral alto histéresis. Canny:"
        self.E347 = tk.Entry(self.root, width=5)
        self.E347.place(x=210, y=145)
        self.E347.insert(0, "30")

        # Gantry
        self.L348 = tk.Label(self.root)
        self.L348.place(x=210, y=185)
        self.L348['text'] = ""

        self.L349 = tk.Label(self.root)
        self.L349.place(x=210, y=205)
        self.L349['text'] = ""

        self.L350 = tk.Label(self.root)
        self.L350.place(x=210, y=225)
        self.L350['text'] = ""

        self.L351 = tk.Label(self.root)
        self.L351.place(x=210, y=245)
        self.L351['text'] = ""

        self.L354 = tk.Label(self.root)
        self.L354.place(x=550, y=185)
        self.L354['text'] = ""

        self.L355 = tk.Label(self.root)
        self.L355.place(x=550, y=205)
        self.L355['text'] = ""

        self.L356 = tk.Label(self.root)
        self.L356.place(x=550, y=225)
        self.L356['text'] = ""

        self.L357 = tk.Label(self.root)
        self.L357.place(x=550, y=245)
        self.L357['text'] = ""

        # Colimador
        self.L368 = tk.Label(self.root)
        self.L368.place(x=210, y=265)
        self.L368['text'] = ""

        self.L374 = tk.Label(self.root)
        self.L374.place(x=550, y=265)
        self.L374['text'] = ""

        self.L369 = tk.Label(self.root)
        self.L369.place(x=210, y=285)
        self.L369['text'] = ""

        self.L375 = tk.Label(self.root)
        self.L375.place(x=550, y=285)
        self.L375['text'] = ""

        self.L370 = tk.Label(self.root)
        self.L370.place(x=210, y=305)
        self.L370['text'] = ""

        self.L376 = tk.Label(self.root)
        self.L376.place(x=550, y=305)
        self.L376['text'] = ""

        self.L371 = tk.Label(self.root)
        self.L371.place(x=210, y=325)
        self.L371['text'] = ""

        self.L377 = tk.Label(self.root)
        self.L377.place(x=550, y=325)
        self.L377['text'] = ""

        # Mesa
        self.L388 = tk.Label(self.root)
        self.L388.place(x=210, y=345)
        self.L388['text'] = ""

        self.L394 = tk.Label(self.root)
        self.L394.place(x=550, y=345)
        self.L394['text'] = ""

        self.L389 = tk.Label(self.root)
        self.L389.place(x=210, y=365)
        self.L389['text'] = ""

        self.L395 = tk.Label(self.root)
        self.L395.place(x=550, y=365)
        self.L395['text'] = ""

        self.L390 = tk.Label(self.root)
        self.L390.place(x=210, y=385)
        self.L390['text'] = ""

        self.L396 = tk.Label(self.root)
        self.L396.place(x=550, y=385)
        self.L396['text'] = ""

        self.L400 = tk.Label(self.root)
        self.L400.place(x=210, y=425)
        self.L400['text'] = ""

        self.L402 = tk.Label(self.root)
        self.L402.place(x=210, y=445)
        self.L402['text'] = ""

        self.L404 = tk.Label(self.root)
        self.L404.place(x=210, y=465)
        self.L404['text'] = ""

        self.L408 = tk.Label(self.root)
        self.L408.place(x=210, y=505)
        self.L408['text'] = ""

        self.L410 = tk.Label(self.root)
        self.L410.place(x=210, y=525)
        self.L410['text'] = ""

        self.L412 = tk.Label(self.root)
        self.L412.place(x=210, y=545)
        self.L412['text'] = ""

        self.L360 = tk.Label(self.root)
        self.L360.place(x=210, y=585)
        self.L360['text'] = ""

        self.L361 = tk.Label(self.root)
        self.L361.place(x=210, y=605)
        self.L361['text'] = ""

        self.L362 = tk.Label(self.root)
        self.L362.place(x=210, y=625)
        self.L362['text'] = ""

        self.L363 = tk.Label(self.root)
        self.L363.place(x=210, y=645)
        self.L363['text'] = ""

        self.L364 = tk.Label(self.root)
        self.L364.place(x=210, y=665)
        self.L364['text'] = ""

        self.L365 = tk.Label(self.root)
        self.L365.place(x=210, y=685)
        self.L365['text'] = ""

        self.L366 = tk.Label(self.root)
        self.L366.place(x=210, y=705)
        self.L366['text'] = ""

        # Crea los once objetos principales (cuatro de gantry (0, 1, 2, 3), cuatro de colimador (4, 5, 6, 7) y cuatro de mesa (8, 9, 10, 11).
        self.Objeto_estudio = []
        for i in range(12):
            self.Objeto_estudio.append(Objeto_ppal())

        # Crea el objeto Laser 3D. Hay tres, uno para gantry (0), colimador (1) y mesa (2)
        self.laser3D = []
        for i in range(3):
            self.laser3D.append(Laser())

        # Crea el objeto Radiacion 3D, uno para gantry (0), colimador (1) y mesa (2)
        self.radiacion3D = []
        for i in range(3):
            self.radiacion3D.append(Radiacion())

        # self.button1 = tk.Button(self.root, text="Cargar Excel de Mosaiq", command=self.clicked)
        # self.button1.place(x=150, y=50)

        self.root.mainloop()

    # Calcular
    def Calcular(self):
        self.Get_Laser()
        self.Get_centro_radiacion()
        self.Evaluacion()
        self.Evaluacion_global()

    # Genera Informe
    def Genera_Informe(self):
        OK_gantry = False
        OK_colimador = False
        OK_mesa = False

        if hasattr(self, 'OK_gantry') == True:
            if self.OK_gantry == True:
                OK_gantry = True
        else:
            OK_gantry = False

        if hasattr(self, 'OK_colimador') == True:
            if self.OK_colimador == True:
                OK_colimador = True
        else:
            OK_colimador = False

        if hasattr(self, 'OK_mesa') == True:
            if self.OK_mesa == True:
                OK_mesa = True
        else:
            OK_mesa = False

        Genera_informe(self.pixelsizemm, self.Objeto_estudio, OK_gantry, self.laser3D, self.radiacion3D, OK_colimador, OK_mesa, self.media_x_total_laser, self.media_x_total_radiacion,
                       self.media_y_total_laser, self.media_y_total_radiacion, self.media_z_total_laser, self.media_z_total_radiacion)

    # Evaluacion_global
    def Evaluacion_global(self):
        if self.media_x_total_laser is not None and self.media_x_total_radiacion is not None:
            x = self.media_x_total_laser - self.media_x_total_radiacion
        else:
            x = None
        if self.media_y_total_laser is not None and self.media_y_total_radiacion is not None:
            y = self.media_y_total_laser - self.media_y_total_radiacion
        else:
            y = None
        if self.media_z_total_laser is not None and self.media_z_total_radiacion is not None:
            z = self.media_z_total_laser - self.media_z_total_radiacion
        else:
            z = None

        if x is not None and y is not None and z is not None:
            distancia3D_pixeles = np.sqrt(np.power(x, 2) + np.power(y, 2) + np.power(z, 2))
            self.L366['text'] = "Global Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " + \
                            str("{:.2f}".format(distancia3D_pixeles * self.pixelsizemm)) + " mm"
        else:
            if z is None:
                distancia3D_pixeles = np.sqrt(np.power(x, 2) + np.power(y, 2))
                self.L366['text'] = "Global Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " + \
                                    str("{:.2f}".format(distancia3D_pixeles * self.pixelsizemm)) + " mm"

    # Evaluacion
    def Evaluacion(self):
        if self.OK_gantry == True:
            x = self.laser3D[0].Pos3D_media[0] - self.radiacion3D[0].Pos3D_media[0]
            y = self.laser3D[0].Pos3D_media[1] - self.radiacion3D[0].Pos3D_media[1]
            z = self.laser3D[0].Pos3D_media[2] - self.radiacion3D[0].Pos3D_media[2]
            distancia3D_pixeles = np.sqrt(np.power(x, 2) + np.power(y, 2) + np.power(z, 2))
            self.L360['text'] = "Gantry Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " + \
                                str("{:.2f}".format(distancia3D_pixeles * self.pixelsizemm)) + " mm"
            self.L361['text'] = "Gantry Distancia Componentes 2D Laser-Radiacion (X, Y, Z): (" + str("{:.2f}".format(x)) + ", " + str("{:.2f}".format(y)) + ", " + str("{:.2f}".format(z)) + ") pixeles, (" + str("{:.2f}".format(x * self.pixelsizemm)) + ", " + \
                                str("{:.2f}".format(y * self.pixelsizemm)) + ", " + str("{:.2f}".format(z * self.pixelsizemm)) + ") mm"

        if self.OK_colimador == True:
            x = self.laser3D[1].Pos3D_media[0] - self.radiacion3D[1].Pos3D_media[0]
            y = self.laser3D[1].Pos3D_media[1] - self.radiacion3D[1].Pos3D_media[1]
            distancia3D_pixeles = np.sqrt(np.power(x, 2) + np.power(y, 2))
            self.L362['text'] = "Colimador Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " + \
                                str("{:.2f}".format(distancia3D_pixeles * self.pixelsizemm)) + " mm"

            self.L363['text'] = "Colimador Distancia Componentes 2D Laser-Radiacion (X, Y, ---): (" + str("{:.2f}".format(x)) + ", " + \
                                str("{:.2f}".format(y)) + ", ---) pixeles, (" + str("{:.2f}".format(x * self.pixelsizemm)) + ", " + \
                                str("{:.2f}".format(y * self.pixelsizemm)) + ", ---) mm"

        if self.OK_mesa == True:
            x = self.laser3D[2].Pos3D_media[0] - self.radiacion3D[2].Pos3D_media[0]
            y = self.laser3D[2].Pos3D_media[1] - self.radiacion3D[2].Pos3D_media[1]
            distancia3D_pixeles = np.sqrt(np.power(x, 2) + np.power(y, 2))
            self.L364['text'] = "Mesa Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " + \
                                str("{:.2f}".format(distancia3D_pixeles * self.pixelsizemm)) + " mm"
            self.L365['text'] = "Mesa Distancia Componentes 2D Laser-Radiacion (X, Y, ---): (" + str("{:.2f}".format(x)) + ", " +\
                                str("{:.2f}".format(y)) + ", ---) pixeles, (" + str("{:.2f}".format(x * self.pixelsizemm)) + ", " + \
                                str("{:.2f}".format(y * self.pixelsizemm)) + ", ---) mm"

    # Calcula la posicion 3D del centro de radiacion para gantry, colimador, mesa y combinada
    def Get_centro_radiacion(self):
        self.X_total_radiacion = []
        self.Y_total_radiacion = []
        self.Z_total_radiacion = []

        # De las imagenes de gantry
        self.OK_gantry = True
        for i in range(4):
            if self.Objeto_estudio[i].matriz is None:
                self.OK_gantry = False
                break
        if self.OK_gantry == True:
            self.radiacion3D[0].X = []
            self.radiacion3D[0].Y = []
            self.radiacion3D[0].Z = []
            self.radiacion3D[0].X.append(self.Objeto_estudio[0].centro_radiacion_pixeles[0])
            self.radiacion3D[0].Y.append(self.Objeto_estudio[0].centro_radiacion_pixeles[1])
            self.radiacion3D[0].Z.append(self.Objeto_estudio[1].centro_radiacion_pixeles[0])
            self.radiacion3D[0].Y.append(self.Objeto_estudio[1].centro_radiacion_pixeles[1])
            self.radiacion3D[0].X.append(self.Objeto_estudio[2].centro_radiacion_pixeles[0])
            self.radiacion3D[0].Y.append(self.Objeto_estudio[2].centro_radiacion_pixeles[1])
            self.radiacion3D[0].Z.append(self.Objeto_estudio[3].centro_radiacion_pixeles[0])
            self.radiacion3D[0].Y.append(self.Objeto_estudio[3].centro_radiacion_pixeles[1])
            for i in self.radiacion3D[0].X:
                self.X_total_radiacion.append(i)
            for i in self.radiacion3D[0].Y:
                self.Y_total_radiacion.append(i)
            for i in self.radiacion3D[0].Z:
                self.Z_total_radiacion.append(i)

            media_x = Get_media(self.radiacion3D[0].X).media
            media_y = Get_media(self.radiacion3D[0].Y).media
            media_z = Get_media(self.radiacion3D[0].Z).media
            self.radiacion3D[0].Pos3D_media = (media_x, media_y, media_z)
            sigma_x = math.sqrt(Get_varianza(self.radiacion3D[0].X).varianza)
            sigma_y = math.sqrt(Get_varianza(self.radiacion3D[0].Y).varianza)
            sigma_z = math.sqrt(Get_varianza(self.radiacion3D[0].Z).varianza)
            self.radiacion3D[0].Pos3D_sigma = (sigma_x, sigma_y, sigma_z)
            self.radiacion3D[0].Pearson_x = 100 * sigma_x / media_x
            self.radiacion3D[0].Pearson_y = 100 * sigma_y / media_y
            self.radiacion3D[0].Pearson_z = 100 * sigma_z / media_z

        # De las imagenes de colimador
        self.OK_colimador = True
        for i in range(4, 8):
            if self.Objeto_estudio[i].matriz is None and i !=5: # El APEX no admite giro de colimador a 90º !!!:
                self.OK_colimador = False
                break
        if self.OK_colimador == True:
            self.radiacion3D[1].X = []
            self.radiacion3D[1].Y = []
            self.radiacion3D[1].X.append(self.Objeto_estudio[4].centro_radiacion_pixeles[0])
            self.radiacion3D[1].Y.append(self.Objeto_estudio[4].centro_radiacion_pixeles[1])
            if self.Objeto_estudio[5].matriz is not None:
                self.radiacion3D[1].X.append(self.Objeto_estudio[5].centro_radiacion_pixeles[0])
                self.radiacion3D[1].Y.append(self.Objeto_estudio[5].centro_radiacion_pixeles[1])
            self.radiacion3D[1].X.append(self.Objeto_estudio[6].centro_radiacion_pixeles[0])
            self.radiacion3D[1].Y.append(self.Objeto_estudio[6].centro_radiacion_pixeles[1])
            self.radiacion3D[1].X.append(self.Objeto_estudio[7].centro_radiacion_pixeles[0])
            self.radiacion3D[1].Y.append(self.Objeto_estudio[7].centro_radiacion_pixeles[1])
            for i in self.radiacion3D[1].X:
                self.X_total_radiacion.append(i)
            for i in self.radiacion3D[1].Y:
                self.Y_total_radiacion.append(i)

            media_x = Get_media(self.radiacion3D[1].X).media
            media_y = Get_media(self.radiacion3D[1].Y).media
            media_z = None
            self.radiacion3D[1].Pos3D_media = (media_x, media_y, media_z)
            sigma_x = math.sqrt(Get_varianza(self.radiacion3D[1].X).varianza)
            sigma_y = math.sqrt(Get_varianza(self.radiacion3D[1].Y).varianza)
            sigma_z = None
            self.radiacion3D[1].Pos3D_sigma = (sigma_x, sigma_y, sigma_z)
            self.radiacion3D[1].Pearson_x = 100 * sigma_x / media_x
            self.radiacion3D[1].Pearson_y = 100 * sigma_y / media_y
            self.radiacion3D[1].Pearson_z = None

        # De las imagenes de mesa
        self.OK_mesa = True
        for i in range(8, 12):
            if self.Objeto_estudio[i].matriz is None and i != 10:
                self.OK_mesa = False
                break
        if self.OK_mesa == True:
            self.radiacion3D[2].X = []
            self.radiacion3D[2].Y = []
            self.radiacion3D[2].X.append(self.Objeto_estudio[8].centro_radiacion_pixeles[0])
            self.radiacion3D[2].Y.append(self.Objeto_estudio[8].centro_radiacion_pixeles[1])
            self.radiacion3D[2].X.append(self.Objeto_estudio[9].centro_radiacion_pixeles[0])
            self.radiacion3D[2].Y.append(self.Objeto_estudio[9].centro_radiacion_pixeles[1])
            self.radiacion3D[2].X.append(self.Objeto_estudio[11].centro_radiacion_pixeles[0])
            self.radiacion3D[2].Y.append(self.Objeto_estudio[11].centro_radiacion_pixeles[1])
            for i in self.radiacion3D[2].X:
                self.X_total_radiacion.append(i)
            for i in self.radiacion3D[2].Y:
                self.Y_total_radiacion.append(i)

            media_x = Get_media(self.radiacion3D[2].X).media
            media_y = Get_media(self.radiacion3D[2].Y).media
            media_z = None
            self.radiacion3D[2].Pos3D_media = (media_x, media_y, media_z)
            sigma_x = math.sqrt(Get_varianza(self.radiacion3D[2].X).varianza)
            sigma_y = math.sqrt(Get_varianza(self.radiacion3D[2].Y).varianza)
            sigma_z = None
            self.radiacion3D[2].Pos3D_sigma = (sigma_x, sigma_y, sigma_z)
            self.radiacion3D[2].Pearson_x = 100 * sigma_x / media_x
            self.radiacion3D[2].Pearson_y = 100 * sigma_y / media_y
            self.radiacion3D[2].Pearson_z = None

        # Evalua conjuntamente gantry, colimador y mesa
        if len(self.X_total_radiacion) != 0:
            self.media_x_total_radiacion = Get_media(self.X_total_radiacion).media
            self.sigma_x_total_radiacion = math.sqrt(Get_varianza(self.X_total_radiacion).varianza)
        else:
            self.media_x_total_radiacion = None
            self.sigma_x_total_radiacion = None

        if len(self.Y_total_radiacion) != 0:
            self.media_y_total_radiacion = Get_media(self.Y_total_radiacion).media
            self.sigma_y_total_radiacion = math.sqrt(Get_varianza(self.Y_total_radiacion).varianza)
        else:
            self.media_y_total_radiacion = None
            self.sigma_y_total_radiacion = None

        if len(self.Z_total_radiacion) != 0:
            self.media_z_total_radiacion = Get_media(self.Z_total_radiacion).media
            self.sigma_z_total_radiacion = math.sqrt(Get_varianza(self.Z_total_radiacion).varianza)
        else:
            self.media_z_total_radiacion = None
            self.sigma_z_total_radiacion = None

        if self.radiacion3D[0].Pos3D_media is not None:
            self.L408['text'] = "Radiacion Gantry (X, Y, Z): (" + str("{:.2f}".format(self.radiacion3D[0].Pos3D_media[0])) + ", " + \
                            str("{:.2f}".format(self.radiacion3D[0].Pos3D_media[1])) + ", " + str("{:.2f}".format(self.radiacion3D[0].Pos3D_media[2])) + \
                            ") +- (" + str("{:.2f}".format(self.radiacion3D[0].Pos3D_sigma[0])) + \
                            ", " + str("{:.2f}".format(self.radiacion3D[0].Pos3D_sigma[1])) + ", " + str("{:.2f}".format(self.radiacion3D[0].Pos3D_sigma[2])) + ") pixeles; " + "Pearson: " +\
                            str("{:.2f}".format(self.radiacion3D[0].Pearson_x)) + " %, " + str("{:.2f}".format(self.radiacion3D[0].Pearson_y)) +\
                            " %, " + str("{:.2f}".format(self.radiacion3D[0].Pearson_z)) + " %"

        if self.radiacion3D[1].Pos3D_media is not None:
            self.L410['text'] = "Radiacion Colimador (X, Y, Z): (" + str("{:.2f}".format(self.radiacion3D[1].Pos3D_media[0])) + ", " + \
                            str("{:.2f}".format(self.radiacion3D[1].Pos3D_media[1])) + ", ---) +- (" +\
                            str("{:.2f}".format(self.radiacion3D[1].Pos3D_sigma[0])) + \
                            ", " + str("{:.2f}".format(self.radiacion3D[1].Pos3D_sigma[1])) + ", ---) pixeles; " +\
                            "Pearson: " + str("{:.2f}".format(self.radiacion3D[1].Pearson_x)) + " %, " +\
                            str("{:.2f}".format(self.radiacion3D[1].Pearson_y)) + " %, --- %"


        if self.radiacion3D[2].Pos3D_media is not None:
            self.L412['text'] = "Radiacion Mesa (X, Y, Z): (" + str("{:.2f}".format(self.radiacion3D[2].Pos3D_media[0])) + ", " + \
                            str("{:.2f}".format(self.radiacion3D[2].Pos3D_media[1])) + ", ---) +- (" + str("{:.2f}".format(self.radiacion3D[2].Pos3D_sigma[0])) +\
                                ", " + str("{:.2f}".format(self.radiacion3D[2].Pos3D_sigma[1])) + ", ---) pixeles; " + "Pearson: " + str("{:.2f}".format(self.radiacion3D[2].Pearson_x)) + " %, " + str("{:.2f}".format(self.radiacion3D[2].Pearson_y)) +\
                                " %, --- %"

    # Calcula la posicion 3D del laser para gantry, colimador, mesa y combinado
    def Get_Laser(self):
        self.X_total_laser = []
        self.Y_total_laser = []
        self.Z_total_laser = []

        # De las imagenes de gantry
        self.OK_gantry = True
        for i in range(4):
            if self.Objeto_estudio[i].matriz is None:
                self.OK_gantry = False
                break
        if self.OK_gantry == True:
            self.laser3D[0].X = []
            self.laser3D[0].Y = []
            self.laser3D[0].Z = []
            self.laser3D[0].X.append(self.Objeto_estudio[0].centro_circulo_pixeles[0])
            self.laser3D[0].Y.append(self.Objeto_estudio[0].centro_circulo_pixeles[1])
            self.laser3D[0].Z.append(self.Objeto_estudio[1].centro_circulo_pixeles[0])
            self.laser3D[0].Y.append(self.Objeto_estudio[1].centro_circulo_pixeles[1])
            self.laser3D[0].X.append(self.Objeto_estudio[2].centro_circulo_pixeles[0])
            self.laser3D[0].Y.append(self.Objeto_estudio[2].centro_circulo_pixeles[1])
            self.laser3D[0].Z.append(self.Objeto_estudio[3].centro_circulo_pixeles[0])
            self.laser3D[0].Y.append(self.Objeto_estudio[3].centro_circulo_pixeles[1])
            for i in self.laser3D[0].X:
                self.X_total_laser.append(i)
            for i in self.laser3D[0].Y:
                self.Y_total_laser.append(i)
            for i in self.laser3D[0].Z:
                self.Z_total_laser.append(i)

            media_x = Get_media(self.laser3D[0].X).media
            media_y = Get_media(self.laser3D[0].Y).media
            media_z = Get_media(self.laser3D[0].Z).media
            self.laser3D[0].Pos3D_media = (media_x, media_y, media_z)
            sigma_x = math.sqrt(Get_varianza(self.laser3D[0].X).varianza)
            sigma_y = math.sqrt(Get_varianza(self.laser3D[0].Y).varianza)
            sigma_z = math.sqrt(Get_varianza(self.laser3D[0].Z).varianza)
            self.laser3D[0].Pos3D_sigma = (sigma_x, sigma_y, sigma_z)
            self.laser3D[0].Pearson_x = 100 * sigma_x / media_x
            self.laser3D[0].Pearson_y = 100 * sigma_y / media_y
            self.laser3D[0].Pearson_z = 100 * sigma_z / media_z

        # De las imagenes de colimador
        self.OK_colimador = True
        for i in range(4, 8):
            if self.Objeto_estudio[i].matriz is None and i !=5: # El APEX no admite giro de colimador a 90º !!!
                self.OK_colimador = False
                break
        if self.OK_colimador == True:
            self.laser3D[1].X = []
            self.laser3D[1].Y = []
            self.laser3D[1].X.append(self.Objeto_estudio[4].centro_circulo_pixeles[0])
            self.laser3D[1].Y.append(self.Objeto_estudio[4].centro_circulo_pixeles[1])
            if self.Objeto_estudio[5].matriz is not None:
                self.laser3D[1].X.append(self.Objeto_estudio[5].centro_circulo_pixeles[0])
                self.laser3D[1].Y.append(self.Objeto_estudio[5].centro_circulo_pixeles[1])
            self.laser3D[1].X.append(self.Objeto_estudio[6].centro_circulo_pixeles[0])
            self.laser3D[1].Y.append(self.Objeto_estudio[6].centro_circulo_pixeles[1])
            self.laser3D[1].X.append(self.Objeto_estudio[7].centro_circulo_pixeles[0])
            self.laser3D[1].Y.append(self.Objeto_estudio[7].centro_circulo_pixeles[1])
            for i in self.laser3D[1].X:
                self.X_total_laser.append(i)
            for i in self.laser3D[1].Y:
                self.Y_total_laser.append(i)

            media_x = Get_media(self.laser3D[1].X).media
            media_y = Get_media(self.laser3D[1].Y).media
            media_z = None
            self.laser3D[1].Pos3D_media = (media_x, media_y, media_z)
            sigma_x = math.sqrt(Get_varianza(self.laser3D[1].X).varianza)
            sigma_y = math.sqrt(Get_varianza(self.laser3D[1].Y).varianza)
            sigma_z = None
            self.laser3D[1].Pos3D_sigma = (sigma_x, sigma_y, sigma_z)
            self.laser3D[1].Pearson_x = 100 * sigma_x / media_x
            self.laser3D[1].Pearson_y = 100 * sigma_y / media_y
            self.laser3D[1].Pearson_z = None

        # De las imagenes de mesa
        self.OK_mesa=True
        for i in range(8, 12):
            if self.Objeto_estudio[i].matriz is None and i != 10:
                self.OK_mesa = False
                break
        if self.OK_mesa == True:
            self.laser3D[2].X = []
            self.laser3D[2].Y = []
            self.laser3D[2].X.append(self.Objeto_estudio[8].centro_circulo_pixeles[0])
            self.laser3D[2].Y.append(self.Objeto_estudio[8].centro_circulo_pixeles[1])
            self.laser3D[2].X.append(self.Objeto_estudio[9].centro_circulo_pixeles[0])
            self.laser3D[2].Y.append(self.Objeto_estudio[9].centro_circulo_pixeles[1])
            self.laser3D[2].X.append(self.Objeto_estudio[11].centro_circulo_pixeles[0])
            self.laser3D[2].Y.append(self.Objeto_estudio[11].centro_circulo_pixeles[1])
            for i in self.laser3D[2].X:
                self.X_total_laser.append(i)
            for i in self.laser3D[2].Y:
                self.Y_total_laser.append(i)

            media_x = Get_media(self.laser3D[2].X).media
            media_y = Get_media(self.laser3D[2].Y).media
            media_z = None
            self.laser3D[2].Pos3D_media = (media_x, media_y, media_z)
            sigma_x = math.sqrt(Get_varianza(self.laser3D[2].X).varianza)
            sigma_y = math.sqrt(Get_varianza(self.laser3D[2].Y).varianza)
            sigma_z = None
            self.laser3D[2].Pos3D_sigma = (sigma_x, sigma_y, sigma_z)
            self.laser3D[2].Pearson_x = 100 * sigma_x / media_x
            self.laser3D[2].Pearson_y = 100 * sigma_y / media_y
            self.laser3D[2].Pearson_z = None

        # Evalua conjuntamente gantry, colimador y mesa
        if len(self.X_total_laser) != 0:
            self.media_x_total_laser = Get_media(self.X_total_laser).media
            self.sigma_x_total_laser = math.sqrt(Get_varianza(self.X_total_laser).varianza)
        else:
            self.media_x_total_laser = None
            self.sigma_x_total_laser = None

        if len(self.Y_total_laser) != 0:
            self.media_y_total_laser = Get_media(self.Y_total_laser).media
            self.sigma_y_total_laser = math.sqrt(Get_varianza(self.Y_total_laser).varianza)
        else:
            self.media_y_total_laser = None
            self.sigma_y_total_laser = None

        if len(self.Z_total_laser) != 0:
            self.media_z_total_laser = Get_media(self.Z_total_laser).media
            self.sigma_z_total_laser = math.sqrt(Get_varianza(self.Z_total_laser).varianza)
        else:
            self.media_z_total_laser = None
            self.sigma_z_total_laser = None

        if self.laser3D[0].Pos3D_media is not None:
            self.L400['text'] = "Laser Gantry (X, Y, Z): (" + str("{:.2f}".format(self.laser3D[0].Pos3D_media[0])) + ", " +\
                            str("{:.2f}".format(self.laser3D[0].Pos3D_media[1])) + ", " + str("{:.2f}".format(self.laser3D[0].Pos3D_media[2])) +\
                            ") +- (" + str("{:.2f}".format(self.laser3D[0].Pos3D_sigma[0])) +\
                            ", " + str("{:.2f}".format(self.laser3D[0].Pos3D_sigma[1])) + ", " +\
                                str("{:.2f}".format(self.laser3D[0].Pos3D_sigma[2])) + ") pixeles; " +\
                            "Pearson: " + str("{:.2f}".format(self.laser3D[0].Pearson_x))+ " %, " +\
                                str("{:.2f}".format(self.laser3D[0].Pearson_y)) +\
                            " %, " + str("{:.2f}".format(self.laser3D[0].Pearson_z)) + " %"

        if self.laser3D[1].Pos3D_media is not None:
            self.L402['text'] = "Laser Colimador (X, Y, Z): (" + str("{:.2f}".format(self.laser3D[1].Pos3D_media[0])) + ", " + \
                            str("{:.2f}".format(self.laser3D[1].Pos3D_media[1])) + ", ---) +- (" + str("{:.2f}".format(self.laser3D[1].Pos3D_sigma[0])) + \
                            ", " + str("{:.2f}".format(self.laser3D[1].Pos3D_sigma[1])) + ", ---) pixeles; " + "Pearson: " + \
                            str("{:.2f}".format(self.laser3D[1].Pearson_x)) + " %, " + str("{:.2f}".format(self.laser3D[1].Pearson_y)) + " %, --- %"

        if self.laser3D[2].Pos3D_media is not None:
            self.L404['text'] = "Laser Mesa (X, Y, Z): (" + str("{:.2f}".format(self.laser3D[2].Pos3D_media[0])) + ", " + \
                            str("{:.2f}".format(self.laser3D[2].Pos3D_media[1])) + ", ---) +- (" + str("{:.2f}".format(self.laser3D[2].Pos3D_sigma[0])) +\
                                ", " + str("{:.2f}".format(self.laser3D[2].Pos3D_sigma[1])) + ", ---) pixeles; " + \
                            "Pearson: " + str("{:.2f}".format(self.laser3D[2].Pearson_x)) + " %, " + str("{:.2f}".format(self.laser3D[2].Pearson_y)) + " %, --- %"

    def Ver_imagen(self):
        magnitud = int(self.radiobutton_magnitud.get())
        orientacion = int(self.radiobutton_orientacion.get())
        indice = magnitud * 4 + orientacion
        self.Mostrar(self.Objeto_estudio[indice].matriz, self.canvas1_ppal)

    def zoom_update(self, param):
        paso = 25
        if param == "-":
            if self.zoom_i - paso > 0 and self.zoom_f + paso < self.rows:
                if self.zoom_i - paso < self.zoom_f + paso:
                    self.zoom_i -= paso
                    self.zoom_f += paso
        else: # +
            if self.zoom_i + paso < self.rows and self.zoom_f - paso > 0:
                if self.zoom_i + paso < self.zoom_f - paso:
                    self.zoom_i += paso
                    self.zoom_f -= paso

        magnitud = int(self.radiobutton_magnitud.get())
        orientacion = int(self.radiobutton_orientacion.get())
        indice = magnitud*4+orientacion

        if self.var.get() == False:
            self.Mostrar(self.Objeto_estudio[indice].matriz[self.zoom_i:self.zoom_f, self.zoom_i:self.zoom_f], self.canvas1_ppal)
        else:
            self.Mostrar_circulo_y_rectas()

    def Mostrar_circulo_y_rectas(self):
        magnitud = int(self.radiobutton_magnitud.get())
        orientacion = int(self.radiobutton_orientacion.get())
        indice = magnitud * 4 + orientacion

        imagen = np.copy(self.Objeto_estudio[indice].matriz)
        # Circulo
        cv2.circle(imagen, self.Objeto_estudio[indice].centro_circulo_pixeles, self.Objeto_estudio[indice].radio_pixel, (0, 0, 255), 1)

        # Centro circulo
        Pa = (self.Objeto_estudio[indice].centro_circulo_pixeles[0] - 2, self.Objeto_estudio[indice].centro_circulo_pixeles[1])
        Pb = (self.Objeto_estudio[indice].centro_circulo_pixeles[0] + 2, self.Objeto_estudio[indice].centro_circulo_pixeles[1])
        Pc = (self.Objeto_estudio[indice].centro_circulo_pixeles[0], self.Objeto_estudio[indice].centro_circulo_pixeles[1] - 2)
        Pd = (self.Objeto_estudio[indice].centro_circulo_pixeles[0], self.Objeto_estudio[indice].centro_circulo_pixeles[1] + 2)
        cv2.line(imagen, Pa, Pb, (0, 0, 255), 1)
        cv2.line(imagen, Pc, Pd, (0, 0, 255), 1)

        # Rectas
        for i in range(4):
            P0 = (int(self.Objeto_estudio[indice].rectas[i].P0[0]), int(self.Objeto_estudio[indice].rectas[i].P0[1]))
            P1 = (int(self.Objeto_estudio[indice].rectas[i].P1[0]), int(self.Objeto_estudio[indice].rectas[i].P1[1]))
            cv2.line(imagen, P0, P1, (0, 0, 255), 1)

        # Diagonales
        for i in range(2):
            P0 = (int(self.Objeto_estudio[indice].diagonales[i].P0[0]), int(self.Objeto_estudio[indice].diagonales[i].P0[1]))
            P1 = (int(self.Objeto_estudio[indice].diagonales[i].P1[0]), int(self.Objeto_estudio[indice].diagonales[i].P1[1]))
            cv2.line(imagen, P0, P1, (0, 0, 255), 1)
        self.Mostrar(imagen[self.zoom_i:self.zoom_f, self.zoom_i:self.zoom_f], self.canvas1_ppal)

    def popup(self, event):
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()

    def Abre_imagen(self, sigma, low, high):
        etiqueta = ["0", "90", "180", "270"]
        magnitud = self.radiobutton_magnitud.get()
        angulacion = self.radiobutton_orientacion.get()
        if magnitud == 2 and angulacion == 2:
            tk.messagebox.showinfo(message="Magnitud y angulacion no valida!!!", title="Aviso!!!")
        else:
            answer = askopenfilename(filetypes=[("Dicom files", ".dcm .ima")])
            if answer != "":

                # Lee matriz dcm
                ds = dicom.dcmread(answer)
                rdh = Read_Dicom_Header(ds)
                self.pixelsizemm = rdh.pizel_size_iso_mm # Calcula el tamaño del pixel de la cabecera dicom
                self.rows = rdh.rows
                self.root.title(self.titulo + "; Pixel:  " + str("{:.2f}".format(self.pixelsizemm)) + " mm")

                matriz = ds.pixel_array
                # Si es .ima invierte la imagen
                extension = Get_extension(answer).extension
                if extension == "dcm" or extension == "DCM":
                    pass
                else:
                    matriz = invierte_(matriz).imagen_invertida

                # Aplica filtro de mediana 3x3
                matriz = cv2.medianBlur(matriz, 3)

                # Indexa seleccion.
                #   Gantry (0):
                #           Angulacion 0   ... (0)
                #           Angulacion 90  ... (1)
                #           Angulacion 180 ... (2)
                #           Angulacion 270 ... (3)
                #   Colimador (1):
                #           Angulacion 0   ... (4)
                #           Angulacion 90  ... (5)
                #           Angulacion 180 ... (6)
                #           Angulacion 270 ... (7)
                #   Mesa (2):
                #           Angulacion 0   ... (8)
                #           Angulacion 90  ... (9)
                #           Angulacion 180 ... (10) No procede
                #           Angulacion 270 ... (11)

                indice = magnitud * 4 + angulacion
                self.Objeto_estudio[indice].nombre_fichero = answer
                # print("Magnitud: " + str(magnitud) + " angulacion: " + str(angulacion) + " indice: " + str(indice))

                if magnitud == 0: # Gantry
                    self.Objeto_estudio[indice].gantry = etiqueta[angulacion]
                    if angulacion == 1 or angulacion == 2:
                        matriz = np.fliplr(matriz)
                else:
                    if magnitud == 1: # Colimador
                        self.Objeto_estudio[indice].colimador = etiqueta[angulacion]
                    else: # Mesa
                        self.Objeto_estudio[indice].mesa = etiqueta[angulacion]

                matriz = matriz / 256
                procesed_array = matriz.astype(int)
                self.Objeto_estudio[indice].matriz = procesed_array

                self.Mostrar(procesed_array, self.canvas1_ppal)

                self.edges = canny(procesed_array, sigma=sigma, low_threshold=low, high_threshold=high)
                #plt.plot()
                #plt.imshow(self.edges)
                #plt.show()

                # Rectas
                # Precision de 0.5 grados.
                tested_angles = np.linspace(-np.pi / 2, np.pi / 2, 720, endpoint=False)
                h, theta, d = hough_line(self.edges, theta=tested_angles)
                row1, col1 = self.edges.shape
                n_rectas = 0

                for _, angle, dist in zip(*hough_line_peaks(h, theta, d)):
                    if angle != 0:
                        y0 = (dist - 0 * np.cos(angle)) / np.sin(angle)
                        y1 = (dist - col1 * np.cos(angle)) / np.sin(angle)
                        Punto_0 = (0, y0)
                        Punto_1 = (col1, y1)
                    else:
                        # print("Pendiente infinita")
                        Punto_0 = (dist, 0)
                        Punto_1 = (dist, row1)
                    if n_rectas <4:
                        self.Objeto_estudio[indice].rectas[n_rectas].P0 = Punto_0
                        self.Objeto_estudio[indice].rectas[n_rectas].P1 = Punto_1
                    else:
                        break
                    n_rectas += 1

                if n_rectas == 4:
                    # Busca las diagonales
                    gc = Get_cortes_rectas(self.Objeto_estudio[indice].rectas)
                    """
                    print("Cortes:")
                    print("0 y 1: " + str(gc.corte01))
                    print("0 y 2: " + str(gc.corte02))
                    print("0 y 3: " + str(gc.corte03))
                    print("1 y 2: " + str(gc.corte12))
                    print("1 y 3: " + str(gc.corte13))
                    print("2 y 3: " + str(gc.corte23))
                    """
                    gd = Get_rectas_diagonales(gc, self.rows)
                    """
                    print("Puntos de la diagonal 0:")
                    print(str(gd.punto_0_recta_diagonal_0) + " y " + str(gd.punto_1_recta_diagonal_0))
                    print("Puntos de la diagonal 1:")
                    print(str(gd.punto_0_recta_diagonal_1) + " y " + str(gd.punto_1_recta_diagonal_1))
                    """
                    self.Objeto_estudio[indice].diagonales[0].P0 = gd.punto_0_recta_diagonal_0
                    self.Objeto_estudio[indice].diagonales[0].P1 = gd.punto_1_recta_diagonal_0
                    self.Objeto_estudio[indice].diagonales[1].P0 = gd.punto_0_recta_diagonal_1
                    self.Objeto_estudio[indice].diagonales[1].P1 = gd.punto_1_recta_diagonal_1

                    # Corte de las diagonales
                    cdr = Corte_dos_rectas(gd.punto_0_recta_diagonal_0, gd.punto_1_recta_diagonal_0,
                                            gd.punto_0_recta_diagonal_1, gd.punto_1_recta_diagonal_1)
                    self.Objeto_estudio[indice].centro_radiacion_pixeles = cdr.corte
                    #print("Centro de radiacion: " + str(self.Objeto_estudio[indice].centro_radiacion_pixeles))
                    MsgBox = 'yes' # Para continuar con la deteccion del circulo
                else:
                    tk.messagebox.showinfo(
                        message="Nº de rectas detectadas para campo de radiacion en imagen distinto a 4(" + str(n_rectas) +")!!!", title="Aviso!!!")
                    MsgBox = tk.messagebox.askquestion("Detección de circulo ...", "Continuo con la detección del circulo?",
                                                   icon='warning')
                if MsgBox == 'yes': # Continua con la deteccion del circulo
                    hough_radii = np.arange(5, 20, 2)
                    hough_res = hough_circle(self.edges, hough_radii)

                    # Busca solo un circulo
                    accums, cx, cy, radii = hough_circle_peaks(hough_res, hough_radii, total_num_peaks=1)
                    if len(cx) == 0:  # No encuentra un circulo
                        tk.messagebox.showinfo(
                            message="Circulo no detectado!!! Modifica el umbral maximo del filtro de Canny y vuelve a abrir la imagen (dcm:30, ima:10)",
                            title="Aviso!!!")
                    else:
                        self.Objeto_estudio[indice].centro_circulo_pixeles = (cx[0], cy[0])
                        self.Objeto_estudio[indice].radio_pixel = radii[0]

                # Presenta resultado
                self.Mostrar_resultado(magnitud, angulacion)

    def Mostrar_resultado(self, magnitud, angulacion):
        indice = magnitud*4+angulacion

        if magnitud == 0: # Gantry
            if angulacion == 0:
                cadena = "Gantry 0. Laser(x, y): (" + str(self.Objeto_estudio[indice].centro_circulo_pixeles[0]) +\
                         ", " + str(self.Objeto_estudio[indice].centro_circulo_pixeles[1]) + ", ---)"
                self.L348['text'] = cadena
                cadena = "Radiacion(x, y): (" + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[0])) +\
                         ", " + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[1])) + ", ---)"
                self.L354['text'] = cadena
            if angulacion == 1:
                cadena = "Gantry 90. Laser(y, z): (---, " + str(self.Objeto_estudio[indice].centro_circulo_pixeles[1]) +\
                                                ", " +  str(self.Objeto_estudio[indice].centro_circulo_pixeles[0]) + ")"
                self.L349['text'] = cadena
                cadena = "Radiacion(y, z): (---, " + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[1])) +\
                         ", " + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[0])) + ")"
                self.L355['text'] = cadena
            if angulacion == 2:
                cadena = "Gantry 180. Laser(x, y): (" + str(self.Objeto_estudio[indice].centro_circulo_pixeles[0]) +\
                                                ", " +  str(self.Objeto_estudio[indice].centro_circulo_pixeles[1]) + ", ---)"
                self.L350['text'] = cadena
                cadena = "Radiacion(x, y): (" + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[0])) + \
                         ", " + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[1])) + ", ---)"
                self.L356['text'] = cadena
            if angulacion == 3:
                cadena = "Gantry 270. Laser(y, z): (---, " + str(self.Objeto_estudio[indice].centro_circulo_pixeles[1]) +\
                                                ", " +  str(self.Objeto_estudio[indice].centro_circulo_pixeles[0]) + ")"
                self.L351['text'] = cadena
                cadena = "Radiacion(y, z): (---, " + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[1])) + ", " +\
                         str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[0])) + ")"
                self.L357['text'] = cadena
        else:
            if magnitud == 1: # Colimador
                if angulacion == 0:
                    cadena = "Colimador 0. Laser(x, y): (" + str(self.Objeto_estudio[indice].centro_circulo_pixeles[0]) + \
                             ", " + str(self.Objeto_estudio[indice].centro_circulo_pixeles[1]) + ", ---)"
                    self.L368['text'] = cadena
                    cadena = "Radiacion(x, y): (" + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[0])) + \
                             ", " + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[1])) + ", ---)"
                    self.L374['text'] = cadena
                if angulacion == 1:
                    cadena = "Colimador 90. Laser(x, y): (" + str(self.Objeto_estudio[indice].centro_circulo_pixeles[0]) + \
                             ", " + str(self.Objeto_estudio[indice].centro_circulo_pixeles[1]) + ", ---)"
                    self.L369['text'] = cadena
                    cadena = "Radiacion(x, y): (" + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[0])) + \
                             ", " + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[1])) + ", ---)"
                    self.L375['text'] = cadena
                if angulacion == 2:
                    cadena = "Colimador 180. Laser(x, y): (" + str(self.Objeto_estudio[indice].centro_circulo_pixeles[0]) + \
                             ", " + str(self.Objeto_estudio[indice].centro_circulo_pixeles[1]) + ", ---)"
                    self.L370['text'] = cadena
                    cadena = "Radiacion(x, y): (" + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[0])) + \
                             ", " + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[1])) + ", ---)"
                    self.L376['text'] = cadena
                if angulacion == 3:
                    cadena = "Colimador 270. Laser(x, y): (" + str(self.Objeto_estudio[indice].centro_circulo_pixeles[0]) + \
                             ", " + str(self.Objeto_estudio[indice].centro_circulo_pixeles[1]) + ", ---)"
                    self.L371['text'] = cadena
                    cadena = "Radiacion(x, y): (" + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[0])) + \
                             ", " + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[1])) + ", ---)"
                    self.L377['text'] = cadena
            else: # Mesa
                if angulacion == 0:
                    cadena = "Mesa 0. Laser(x, y): (" + str(
                        self.Objeto_estudio[indice].centro_circulo_pixeles[0]) + \
                             ", " + str(self.Objeto_estudio[indice].centro_circulo_pixeles[1]) + ", ---)"
                    self.L388['text'] = cadena
                    cadena = "Radiacion(x, y): (" + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[0])) + \
                             ", " + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[1])) + ", ---)"
                    self.L394['text'] = cadena
                if angulacion == 1:
                    cadena = "Mesa 90. Laser(x, y): (" + str(
                        self.Objeto_estudio[indice].centro_circulo_pixeles[0]) + \
                             ", " + str(self.Objeto_estudio[indice].centro_circulo_pixeles[1]) + ", ---)"
                    self.L389['text'] = cadena
                    cadena = "Radiacion(x, y): (" + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[0])) + \
                             ", " + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[1])) + ", ---)"
                    self.L395['text'] = cadena
                if angulacion == 3:
                    cadena = "Mesa 270. Laser(x, y): (" + str(
                        self.Objeto_estudio[indice].centro_circulo_pixeles[0]) + \
                             ", " + str(self.Objeto_estudio[indice].centro_circulo_pixeles[1]) + ", ---)"
                    self.L390['text'] = cadena
                    cadena = "Radiacion(x, y): (" + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[0])) + \
                             ", " + str("{:.2f}".format(self.Objeto_estudio[indice].centro_radiacion_pixeles[1])) + ", ---)"
                    self.L396['text'] = cadena

    def Mostrar(self, matriz, canvas):
        ancho_canvas = canvas.winfo_width()
        alto_canvas = canvas.winfo_height()
        fichero_imagen = "out.png"

        if len(matriz.shape) == 2:
            buffer3D = np.zeros((len(matriz), len(matriz[0]), 3))
            for k in range(3):
                buffer3D[:, :, k] = matriz
        else:
            buffer3D = matriz
        cv2.imwrite(fichero_imagen, buffer3D.astype(np.uint8))
        img = PIL_image.open(fichero_imagen)
        img = img.resize((ancho_canvas, alto_canvas), PIL_image.ANTIALIAS)
        self.img1 = ImageTk.PhotoImage(img)
        canvas.create_image(0, 0, anchor="nw", image=self.img1)
        remove(fichero_imagen)

# Posicion del centro de la bola, laser.
# Media, sigma y pearson
class Laser:
    def __init__(self):
        self.X = []
        self.Y = []
        self.Z = []
        self.Pos3D_media = None
        self.Pos3D_sigma = None
        self.Pearson_x = None
        self.Pearson_y = None
        self.Pearson_z = None

# Posicion del centro de radiacion, cuadrado.
# Media, sigma y pearson
class Radiacion:
    def __init__(self):
        self.X = []
        self.Y = []
        self.Z = []
        self.Pos3D_media = None
        self.Pos3D_sigma = None
        self.Pearson_x = None
        self.Pearson_y = None
        self.Pearson_z = None

class Get_cortes_rectas:
    def __init__(self, rectas):
        self.corte01 = Corte_dos_rectas(rectas[0].P0, rectas[0].P1, rectas[1].P0, rectas[1].P1).corte
        self.corte02 = Corte_dos_rectas(rectas[0].P0, rectas[0].P1, rectas[2].P0, rectas[2].P1).corte
        self.corte03 = Corte_dos_rectas(rectas[0].P0, rectas[0].P1, rectas[3].P0, rectas[3].P1).corte
        self.corte12 = Corte_dos_rectas(rectas[1].P0, rectas[1].P1, rectas[2].P0, rectas[2].P1).corte
        self.corte13 = Corte_dos_rectas(rectas[1].P0, rectas[1].P1, rectas[3].P0, rectas[3].P1).corte
        self.corte23 = Corte_dos_rectas(rectas[2].P0, rectas[2].P1, rectas[3].P0, rectas[3].P1).corte

class Corte_dos_rectas:
    def __init__(self, PA0, PA1, PB0, PB1):
        self.corte = None

        x1A = PA0[0]
        y1A = PA0[1]
        x2A = PA1[0]
        y2A = PA1[1]

        x1B = PB0[0]
        y1B = PB0[1]
        x2B = PB1[0]
        y2B = PB1[1]

        # Vectores directores
        VAx = x2A - x1A
        VAy = y2A - y1A

        VBx = x2B - x1B
        VBy = y2B - y1B

        # Modulo de los vectores directores
        mod_A = math.sqrt(VAx * VAx + VAy * VAy)
        mod_B = math.sqrt(VBx * VBx + VBy * VBy)

        # Producto escalar ambos vectores
        prod_esc = VAx*VBx + VAy*VBy

        # Coseno del angulo que forman ambos vectores
        coseno = prod_esc /(mod_A*mod_B)

        # Estudia paralelismo
        if abs(round(coseno, 4)) == 1: # No hay corte o está muy alejado de la zona de interés
            x = None
            y = None
        else:
            den = VAy * VBx - VAx * VBy
            num = VAy * (x1A - x1B) + VAx * (y1B - y1A)
            if den != 0:
                t = num / den

                x = x1B + t * VBx
                y = y1B + t * VBy

        self.corte = (x, y)

class Get_media:
    def __init__(self, lista):
        self.media = None
        s = 0
        for elemento in lista:
            s += elemento
            self.media = s / float(len(lista))

class Get_varianza:
    def __init__(self, lista):
        self.varianza = None

        s = 0
        m = Get_media(lista).media
        for elemento in lista:
            s += ((elemento - m) ** 2)
            self.varianza = s / float(len(lista))

class Get_rectas_diagonales:
    def __init__(self, cortes, fuera_de_rango):
        self.puntos_cortes_validos = []
        self.punto_0_recta_diagonal_0 = None
        self.punto_1_recta_diagonal_0 = None
        self.punto_0_recta_diagonal_1 = None
        self.punto_1_recta_diagonal_1 = None

        if cortes.corte01[0] != None and abs(cortes.corte01[0]) < fuera_de_rango and cortes.corte01[1] != None and abs(cortes.corte01[1]) < fuera_de_rango:
            self.puntos_cortes_validos.append(cortes.corte01)
        if cortes.corte02[0] != None and abs(cortes.corte02[0]) < fuera_de_rango and cortes.corte02[1] != None and abs(cortes.corte02[1]) < fuera_de_rango:
            self.puntos_cortes_validos.append(cortes.corte02)
        if cortes.corte03[0] != None and abs(cortes.corte03[0]) < fuera_de_rango and cortes.corte03[1] != None and abs(cortes.corte03[1]) < fuera_de_rango:
            self.puntos_cortes_validos.append(cortes.corte03)
        if cortes.corte12[0] != None and abs(cortes.corte12[0]) < fuera_de_rango and cortes.corte12[1] != None and abs(cortes.corte12[1]) < fuera_de_rango:
            self.puntos_cortes_validos.append(cortes.corte12)
        if cortes.corte13[0] != None and abs(cortes.corte13[0]) < fuera_de_rango and cortes.corte13[1] != None and abs(cortes.corte13[1]) < fuera_de_rango:
            self.puntos_cortes_validos.append(cortes.corte13)
        if cortes.corte23[0] != None and abs(cortes.corte23[0]) < fuera_de_rango and cortes.corte23[1] != None and abs(cortes.corte23[1]) < fuera_de_rango:
            self.puntos_cortes_validos.append(cortes.corte23)

        if len(self.puntos_cortes_validos) != 4:
            print("Numero de puntos de cortes no válidos!!!")
            sys.exit()

        # Busca los puntos que configuran las diagonales
        P00 = self.puntos_cortes_validos[0]
        d01 = Distancia_dos_puntos_2D(P00, self.puntos_cortes_validos[1]).distancia
        d02 = Distancia_dos_puntos_2D(P00, self.puntos_cortes_validos[2]).distancia
        d03 = Distancia_dos_puntos_2D(P00, self.puntos_cortes_validos[3]).distancia
        distancia_maxima = max(d01, d02, d03)
        if distancia_maxima == d01:
            P01 = self.puntos_cortes_validos[1]
            P10 = self.puntos_cortes_validos[2]
            P11 = self.puntos_cortes_validos[3]
        if distancia_maxima == d02:
            P01 = self.puntos_cortes_validos[2]
            P10 = self.puntos_cortes_validos[1]
            P11 = self.puntos_cortes_validos[3]
        if distancia_maxima == d03:
            P01 = self.puntos_cortes_validos[3]
            P10 = self.puntos_cortes_validos[1]
            P11 = self.puntos_cortes_validos[2]

        self.punto_0_recta_diagonal_0 = P00
        self.punto_1_recta_diagonal_0 = P01
        self.punto_0_recta_diagonal_1 = P10
        self.punto_1_recta_diagonal_1 = P11

class Distancia_dos_puntos_2D:
    def __init__(self, P0, P1):
        x1 = P0[0]
        y1 = P0[1]
        x2 = P1[0]
        y2 = P1[1]
        self.distancia = -1

        x = x2 - x1
        y = y2 - y1
        self.distancia = np.sqrt(np.power(x, 2) + np.power(y, 2))

class Read_Dicom_Header:
    def __init__(self, ds):
        self.rows = ds.get("Rows")
        self.columns = ds.get("Columns")
        self.distancia_foco_panel_mm = ds.get("RTImageSID")
        pizel_size_real_mm = ds.get("ImagePlanePixelSpacing")[0]
        radiation_machine_sad = ds.get("RadiationMachineSAD")
        self.pizel_size_iso_mm = (radiation_machine_sad/self.distancia_foco_panel_mm) * pizel_size_real_mm

class Get_extension:
    def __init__(self, cadena):
        self.path = ""
        long_i = len(cadena)
        long_f = 0

        buffer = cadena
        while True:
            pos = buffer.find(".")
            if pos != -1:
                buffer = buffer[pos + 1:]
            else:
                long_f = len(buffer)
                break
        buffer = cadena[long_i - long_f:]
        self.extension = buffer

class invierte_:
    def __init__(self, matriz):
        self.imagen_invertida = (2**16-1) - np.copy(matriz)

class Get_path:
    def __init__(self, cadena):
        self.path = ""
        long_i = len(cadena)
        long_f = 0

        buffer = cadena
        while True:
            pos = buffer.find("/")
            if pos != -1:
                buffer = buffer[pos + 1:]
            else:
                long_f = len(buffer)
                break
        buffer = cadena[:long_i - long_f]
        self.path = buffer

class Genera_informe:
    def __init__(self, pixelsizemm, Objeto_ppal, OK_gantry, laser3D, radiacion3D, OK_colimador, OK_mesa, media_x_total_laser, media_x_total_radiacion,
                 media_y_total_laser, media_y_total_radiacion, media_z_total_laser, media_z_total_radiacion):
        centro_laser_crucetas_gantry = []
        centro_radiacion_crucetas_gantry = []
        centro_laser_crucetas_colimador = []
        centro_radiacion_crucetas_colimador = []
        centro_laser_crucetas_mesa = []
        centro_radiacion_crucetas_mesa = []

        buffer = Get_path(Objeto_ppal[0].nombre_fichero).path
        cadena_0 = (time.strftime("%d/%m/%y")).replace("/", "_")
        filename_out = buffer + "Informe_Ball_Bearing_" + cadena_0 + ".pdf"
        tk.messagebox.showinfo(
            message="¡¡¡Se va a crear Informe de test W/L : " + filename_out + "!!!",
            title="Aviso!!!")

        doc = SimpleDocTemplate(filename_out, pagesize=letter,
                                rightMargin=18, leftMargin=18,
                                topMargin=18, bottomMargin=18)
        Story = []
        styles = getSampleStyleSheet()

        ptext = '<font size="20">Informe Ball Bearing</font>'
        Story.append(Paragraph(ptext, styles["Normal"]))
        Story.append(Spacer(1, 25))

        linea = cadena_0
        ptext = '<font size="10">' + linea + '</font>'
        Story.append(Paragraph(ptext, styles["Normal"]))
        Story.append(Spacer(1, 25))

        linea = "Tamaño Pixel (mm): " + str(pixelsizemm)
        ptext = '<font size="10">' + linea + '</font>'
        Story.append(Paragraph(ptext, styles["Normal"]))
        Story.append(Spacer(1, 25))

        plt.clf()
        f = plt.figure()
        if OK_gantry == True:
            linea = "Gantry:"
            ptext = '<font size="15">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 25))

            for i in range(0, 4):
                linea = str(Objeto_ppal[i].nombre_fichero)
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = "Laser X, Y, Z:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 5))

            linea = "... 0: (" + str(Objeto_ppal[0].centro_circulo_pixeles[0]) + ", " + str(Objeto_ppal[0].centro_circulo_pixeles[1]) +\
                    ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "..90: (---, " + str(Objeto_ppal[1].centro_circulo_pixeles[1]) + ", " + str(Objeto_ppal[1].centro_circulo_pixeles[0]) + ")"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".180: (" + str(Objeto_ppal[2].centro_circulo_pixeles[0]) + ", " + str(Objeto_ppal[2].centro_circulo_pixeles[1]) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".270: (---, " + str(Objeto_ppal[3].centro_circulo_pixeles[1]) + ", " + str(Objeto_ppal[3].centro_circulo_pixeles[0]) + ")"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = "Radiacion X, Y, Z:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 5))

            linea = "... 0: (" + str("{:.2f}".format(Objeto_ppal[0].centro_radiacion_pixeles[0])) + ", " +\
                    str("{:.2f}".format(Objeto_ppal[0].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "..90: (---, " + str("{:.2f}".format(Objeto_ppal[1].centro_radiacion_pixeles[1])) + ", " +\
                    str("{:.2f}".format(Objeto_ppal[1].centro_radiacion_pixeles[0])) + ")"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".180: (" + str("{:.2f}".format(Objeto_ppal[2].centro_radiacion_pixeles[0])) + ", " +\
                    str("{:.2f}".format(Objeto_ppal[2].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".270: (---, " + str("{:.2f}".format(Objeto_ppal[3].centro_radiacion_pixeles[1])) + ", " +\
                    str("{:.2f}".format(Objeto_ppal[3].centro_radiacion_pixeles[0])) + ")"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = "Posicion 3D Laser: (" + str("{:.2f}".format(laser3D[0].Pos3D_media[0])) + ", " + str("{:.2f}".format(laser3D[0].Pos3D_media[1])) + ", " + str("{:.2f}".format(laser3D[0].Pos3D_media[2])) + ") pixeles"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Posicion 3D Radiacion: (" + str("{:.2f}".format(radiacion3D[0].Pos3D_media[0])) + ", " + str("{:.2f}".format(radiacion3D[0].Pos3D_media[1])) + ", " + str("{:.2f}".format(radiacion3D[0].Pos3D_media[2])) + ") pixeles"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            dif_x = laser3D[0].Pos3D_media[0] - radiacion3D[0].Pos3D_media[0]
            dif_y = laser3D[0].Pos3D_media[1] - radiacion3D[0].Pos3D_media[1]
            dif_z = laser3D[0].Pos3D_media[2] - radiacion3D[0].Pos3D_media[2]
            distancia3D_pixeles = np.sqrt(np.power(dif_x, 2) + np.power(dif_y, 2) + np.power(dif_z, 2))
            distancia3D_mm = distancia3D_pixeles * pixelsizemm

            Story.append(Spacer(1, 5))
            linea = "Solo Gantry:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " +\
                    str("{:.2f}".format(distancia3D_mm)) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia Componentes 2D Laser-Radiacion (X, Y, Z): (" + str("{:.2f}".format(dif_x)) + ", " + str("{:.2f}".format(dif_y)) + ", " +\
                    str("{:.2f}".format(dif_z)) + ") pixeles, (" + str("{:.2f}".format(dif_x * pixelsizemm)) + ", " + str("{:.2f}".format(dif_y * pixelsizemm)) +\
                    ", " + str("{:.2f}".format(dif_z * pixelsizemm)) + ") mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            # Genera Grafica. Gantry, Colimador y Mesa
            _abcisas = [0, 90, 180, 270]
            _x_o_z_dif = []
            _y_dif = []
            for i in range(0, 4):
                _x_o_z_dif.append(float(Objeto_ppal[i].centro_circulo_pixeles[0] - Objeto_ppal[i].centro_radiacion_pixeles[0])*pixelsizemm)
                _y_dif.append(float(Objeto_ppal[i].centro_circulo_pixeles[1] - Objeto_ppal[i].centro_radiacion_pixeles[1])*pixelsizemm)
                centro_laser_crucetas_gantry.append(Objeto_ppal[i].centro_circulo_pixeles)
                centro_radiacion_crucetas_gantry.append(Objeto_ppal[i].centro_radiacion_pixeles)

            plt.subplot(131)
            plt.title("Gantry")
            plt.grid()
            plt.xlabel("º")
            plt.ylabel("mm")
            plt.plot(_abcisas, _x_o_z_dif, label = "X/Z")
            plt.plot(_abcisas, _y_dif, label = "Y")
            plt.legend(["X/Z", "Y"])

        if OK_colimador == True:
            Story.append(Spacer(1, 25))
            linea = "Colimador:"
            ptext = '<font size="15">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 25))

            for i in range(4, 8):
                linea = str(Objeto_ppal[i].nombre_fichero)
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = "Laser X, Y, Z:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 5))

            linea = "... 0: (" + str(Objeto_ppal[4].centro_circulo_pixeles[0]) + ", " + str(
                Objeto_ppal[4].centro_circulo_pixeles[1]) + \
                    ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            if Objeto_ppal[5].centro_circulo_pixeles is not None:
                linea = "..90: (" + str(Objeto_ppal[5].centro_circulo_pixeles[0]) + ", " + str(
                    Objeto_ppal[5].centro_circulo_pixeles[1]) + ", ---)"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".180: (" + str(Objeto_ppal[6].centro_circulo_pixeles[0]) + ", " + str(
                Objeto_ppal[6].centro_circulo_pixeles[1]) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".270: (" + str(Objeto_ppal[7].centro_circulo_pixeles[0]) + ", " + str(
                Objeto_ppal[7].centro_circulo_pixeles[1]) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = "Radiacion X, Y, Z:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 5))

            linea = "... 0: (" + str("{:.2f}".format(Objeto_ppal[4].centro_radiacion_pixeles[0])) + ", " +\
                    str("{:.2f}".format(Objeto_ppal[4].centro_radiacion_pixeles[1])) + ",---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            if Objeto_ppal[5].centro_radiacion_pixeles is not None:
                linea = "..90: (" + str("{:.2f}".format(Objeto_ppal[5].centro_radiacion_pixeles[0])) + ", " +\
                        str("{:.2f}".format(Objeto_ppal[5].centro_radiacion_pixeles[1])) + ", ---)"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".180: (" + str("{:.2f}".format(Objeto_ppal[6].centro_radiacion_pixeles[0])) + ", " +\
                    str("{:.2f}".format(Objeto_ppal[6].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".270: (" + str("{:.2f}".format(Objeto_ppal[7].centro_radiacion_pixeles[0])) + ", " +\
                    str("{:.2f}".format(Objeto_ppal[7].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))

            linea = "Posicion 3D Laser: (" + str("{:.2f}".format(laser3D[1].Pos3D_media[0])) + ", " + str("{:.2f}".format(laser3D[1].Pos3D_media[1])) +\
                    ", ---) pixeles"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Posicion 3D Radiacion: (" + str("{:.2f}".format(radiacion3D[1].Pos3D_media[0])) + ", " +\
                    str("{:.2f}".format(radiacion3D[1].Pos3D_media[1])) + ", ---) pixeles"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            dif_x = laser3D[1].Pos3D_media[0] - radiacion3D[1].Pos3D_media[0]
            dif_y = laser3D[1].Pos3D_media[1] - radiacion3D[1].Pos3D_media[1]
            distancia3D_pixeles = np.sqrt(np.power(dif_x, 2) + np.power(dif_y, 2))
            distancia3D_mm = distancia3D_pixeles * pixelsizemm

            Story.append(Spacer(1, 5))
            linea = "Solo Colimador:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " + str(
                str("{:.2f}".format(distancia3D_mm))) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia Componentes 2D Laser-Radiacion (X, Y, Z): (" + str("{:.2f}".format(dif_x)) + ", " +\
                    str("{:.2f}".format(dif_y)) + ", ---) pixeles, (" + str("{:.2f}".format(dif_x * pixelsizemm)) +\
                    ", " + str("{:.2f}".format(dif_y * pixelsizemm)) + ", ---) mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            # Genera Grafica Colimador
            _abcisas = [0, 90, 180, 270]
            _x_dif = []
            _y_dif = []
            for i in range(4, 8):
                if i != 5:
                    _x_dif.append(
                        float(Objeto_ppal[i].centro_circulo_pixeles[0] - Objeto_ppal[i].centro_radiacion_pixeles[0])*pixelsizemm)
                    _y_dif.append(
                        float(Objeto_ppal[i].centro_circulo_pixeles[1] - Objeto_ppal[i].centro_radiacion_pixeles[1])*pixelsizemm)
                    centro_laser_crucetas_colimador.append(Objeto_ppal[i].centro_circulo_pixeles)
                    centro_radiacion_crucetas_colimador.append(Objeto_ppal[i].centro_radiacion_pixeles)
                else:
                    if Objeto_ppal[5].centro_circulo_pixeles is not None:
                        _x_dif.append(
                            float(Objeto_ppal[i].centro_circulo_pixeles[0] - Objeto_ppal[i].centro_radiacion_pixeles[0]) * pixelsizemm)
                        _y_dif.append(
                            float(Objeto_ppal[i].centro_circulo_pixeles[1] - Objeto_ppal[i].centro_radiacion_pixeles[1]) * pixelsizemm)
                        centro_laser_crucetas_colimador.append(Objeto_ppal[i].centro_circulo_pixeles)
                        centro_radiacion_crucetas_colimador.append(Objeto_ppal[i].centro_radiacion_pixeles)
                    else:
                        _abcisas = [0, 180, 270]

            plt.subplot(132)
            plt.title("Colimador")
            plt.grid()
            plt.xlabel("º")
            plt.plot(_abcisas, _x_dif, label="X")
            plt.plot(_abcisas, _y_dif, label="Y")
            plt.legend(["X", "Y"])

        if OK_mesa == True:
            Story.append(Spacer(1, 25))
            linea = "Mesa:"
            ptext = '<font size="15">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 25))

            for i in range(8, 12):
                if i != 10:
                    linea = str(Objeto_ppal[i].nombre_fichero)
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = "Laser X, Y, Z:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 5))

            linea = "... 0: (" + str(Objeto_ppal[8].centro_circulo_pixeles[0]) + ", " + str(Objeto_ppal[8].centro_circulo_pixeles[1]) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "..90: (" + str(Objeto_ppal[9].centro_circulo_pixeles[0]) + ", " + str(Objeto_ppal[9].centro_circulo_pixeles[1]) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".270: (" + str(Objeto_ppal[11].centro_circulo_pixeles[0]) + ", " + str(Objeto_ppal[11].centro_circulo_pixeles[1]) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = "Radiacion X, Y, Z:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 5))

            linea = "... 0: (" + str("{:.2f}".format(Objeto_ppal[8].centro_radiacion_pixeles[0])) + ", " +\
                    str("{:.2f}".format(Objeto_ppal[8].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "..90: (" + str("{:.2f}".format(Objeto_ppal[9].centro_radiacion_pixeles[0])) + ", " +\
                    str("{:.2f}".format(Objeto_ppal[9].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".270: (" + str("{:.2f}".format(Objeto_ppal[11].centro_radiacion_pixeles[0])) + ", " +\
                    str("{:.2f}".format(Objeto_ppal[11].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))

            linea = "Posicion 3D Laser: (" + str("{:.2f}".format(laser3D[2].Pos3D_media[0])) + ", " +\
                    str("{:.2f}".format(laser3D[2].Pos3D_media[1])) + ", ---) pixeles"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Posicion 3D Radiacion: (" + str("{:.2f}".format(radiacion3D[2].Pos3D_media[0])) +\
                    ", " + str("{:.2f}".format(radiacion3D[2].Pos3D_media[1])) + ", ---) pixeles"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            dif_x = laser3D[2].Pos3D_media[0] - radiacion3D[2].Pos3D_media[0]
            dif_y = laser3D[2].Pos3D_media[1] - radiacion3D[2].Pos3D_media[1]
            distancia3D_pixeles = np.sqrt(np.power(dif_x, 2) + np.power(dif_y, 2))
            distancia3D_mm = distancia3D_pixeles * pixelsizemm

            Story.append(Spacer(1, 5))
            linea = "Solo Mesa:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " +\
                    str("{:.2f}".format(distancia3D_mm)) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia Componentes 2D Laser-Radiacion (X, Y, Z): (" + str("{:.2f}".format(dif_x)) + ", " +\
                    str("{:.2f}".format(dif_y)) +\
                    ", ---) pixeles, (" + str("{:.2f}".format(dif_x * pixelsizemm)) + ", " + str("{:.2f}".format(dif_y * pixelsizemm)) + ", ---) mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            # Genera Grafica Mesa
            _abcisas = [0, 90, 270]
            _x_dif = []
            _y_dif = []
            for i in range(8, 12):
                if i != 10:
                    _x_dif.append(
                        float(Objeto_ppal[i].centro_circulo_pixeles[0] - Objeto_ppal[i].centro_radiacion_pixeles[0])*pixelsizemm)
                    _y_dif.append(
                        float(Objeto_ppal[i].centro_circulo_pixeles[1] - Objeto_ppal[i].centro_radiacion_pixeles[1])*pixelsizemm)
                    centro_laser_crucetas_mesa.append(Objeto_ppal[i].centro_circulo_pixeles)
                    centro_radiacion_crucetas_mesa.append(Objeto_ppal[i].centro_radiacion_pixeles)

            plt.subplot(133)
            plt.title("Mesa")
            plt.grid()
            plt.xlabel("º")
            plt.plot(_abcisas, _x_dif, label="X")
            plt.plot(_abcisas, _y_dif, label="Y")
            plt.legend(["X", "Y"])

        f.savefig("Desviaciones.png")

        im = Image("Desviaciones.png", 6 * inch, 6 * inch)
        Story.append(im)
        Story.append(Spacer(1, 25))
        linea = "Laser - Radiacion"
        ptext = '<font size="10">' + linea + '</font>'
        Story.append(Paragraph(ptext, styles["Normal"]))
        Story.append(Spacer(1, 25))

        # Global
        Story.append(Spacer(1, 25))
        cadx = ""
        cady = ""
        cadz = ""

        if media_x_total_laser is not None and media_x_total_radiacion is not None:
            x = media_x_total_laser - media_x_total_radiacion
        else:
            x = None
        if x is not None:
            if x < 0:
                cadx = "Mover laser \'X\' hacia dcha (Zona Gantry 90º)"
            else:
                if x > 0:
                    cadx = "Mover laser \'X\' hacia izda (Zona Gantry 270º)"
                else:
                    cadx = "No mover Laser \'X\'"

        if media_y_total_laser is not None and media_y_total_radiacion is not None:
            y = media_y_total_laser - media_y_total_radiacion
        else:
            y = None
        if y is not None:
            if y < 0:
                cady = "Mover laser \'Y\' hacia pies (Zona Target)"
            else:
                if y > 0:
                    cady = "Mover laser \'Y\' hacia cabeza (Zona Gun)"
                else:
                    cady = "No mover Laser \'Y\'"

        if media_z_total_laser is not None and media_z_total_radiacion is not None:
            z = media_z_total_laser - media_z_total_radiacion
        else:
            z = None
        if z is not None:
            if z < 0:
                cadz = "Mover laser \'Z\' hacia abajo (Zona Posterior)"
            else:
                if z > 0:
                    cadz = "Mover laser \'Z\' hacia arriba (Zona Anterior)"
                else:
                    cadz = "No mover Laser \'Z\'"

        if x is not None and y is not None and z is not None:
            distancia3D_pixeles = np.sqrt(np.power(x, 2) + np.power(y, 2) + np.power(z, 2))
            linea = "Global:"
            ptext = '<font size="15">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = "Laser (X, Y, Z): (" + str("{:.2f}".format(media_x_total_laser)) + ", " + str("{:.2f}".format(media_y_total_laser)) + ", " + str("{:.2f}".format(media_z_total_laser)) + ")"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Radiacion (X, Y, Z): (" + str("{:.2f}".format(media_x_total_radiacion)) + ", " + str("{:.2f}".format(media_y_total_radiacion)) + ", " +\
                    str("{:.2f}".format(media_z_total_radiacion)) + ")"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " + str("{:.2f}".format(distancia3D_pixeles * pixelsizemm)) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia Componentes 2D Laser-Radiacion (X, Y, Z): (" + str("{:.2f}".format(x)) + ", " + str("{:.2f}".format(y)) + ", " + str("{:.2f}".format(z)) + ") pixeles, (" +\
                    str("{:.2f}".format(x * pixelsizemm)) + ", " + str("{:.2f}".format(y * pixelsizemm)) + ", " + str("{:.2f}".format(z * pixelsizemm)) + ") mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = cadx + " " + str("{:.2f}".format(abs(x * pixelsizemm))) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = cady + " " + str("{:.2f}".format(abs(y * pixelsizemm))) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = cadz + " " + str("{:.2f}".format(abs(z * pixelsizemm))) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

        else:
            if z is None:
                linea = "Laser (X, Y, ---): (" + str("{:.2f}".format(media_x_total_laser)) + ", " + str(media_y_total_laser) + ", ---)"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

                linea = "Radiacion (X, Y, ---): (" + str("{:.2f}".format(media_x_total_radiacion)) + ", " + str(media_y_total_radiacion) + ", ---)"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

                distancia3D_pixeles = np.sqrt(np.power(x, 2) + np.power(y, 2))
                linea = "Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " +\
                        str("{:.2f}".format(distancia3D_pixeles * pixelsizemm)) + " mm"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

                linea = "Distancia Componentes 2D Laser-Radiacion (X, Y, ---): (" + str("{:.2f}".format(x)) + ", " + str("{:.2f}".format(y)) +\
                        ", ---) pixeles, (" + str("{:.2f}".format(x * pixelsizemm)) + ", " + str("{:.2f}".format(y * pixelsizemm)) + ", ---) mm"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

                linea = cadx + " " + str("{:.2f}".format(abs(x * pixelsizemm))) + " mm"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

                linea = cady + " " + str("{:.2f}".format(abs(y * pixelsizemm))) + " mm"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

            else:
                if x is None:
                    linea = "Laser (---, Y, Z): (---, " + str("{:.2f}".format(media_y_total_laser)) + ", " + str("{:.2f}".format(media_z_total_laser)) + ")"
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

                    linea = "Radiacion (---, Y, Z): (---, " + str("{:.2f}".format(media_y_total_radiacion)) + ", " + str("{:.2f}".format(media_z_total_radiacion)) + ")"
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

                    distancia3D_pixeles = np.sqrt(np.power(y, 2) + np.power(z, 2))
                    linea = "Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " +\
                            str("{:.2f}".format(distancia3D_pixeles * pixelsizemm)) + " mm"
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

                    linea = "Distancia Componentes 2D Laser-Radiacion (---, Y, Z): (---, " + str("{:.2f}".format(y)) + ", " +\
                            str("{:.2f}".format(z)) + ") pixeles, (---, " + str("{:.2f}".format(y * pixelsizemm)) + ", " +\
                            str("{:.2f}".format(y * pixelsizemm, z)) + ") mm"
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

                    linea = cady + " " + str("{:.2f}".format(abs(y * pixelsizemm))) + " mm"
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

                    linea = cadz + " " + str("{:.2f}".format(abs(z * pixelsizemm))) + " mm"
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

        # Genera imagenes crucetas
        # Gantry
        ds = dicom.dcmread(Objeto_ppal[0].nombre_fichero)
        array = ds.pixel_array

        if len(centro_laser_crucetas_gantry) !=0:
            _array_g = Dibuja_cruceta_en_array(array, centro_laser_crucetas_gantry, centro_radiacion_crucetas_gantry, 3, 1, (255, 0, 0), (0, 255, 0), False).array3D
            plt.clf()
            f = plt.figure()
            shape = _array_g.shape
            y0 = int(shape[0]/2) - 20
            y1 = int(shape[0]/2) + 20
            x0 = int(shape[1]/2) - 20
            x1 = int(shape[1]/2) + 20
            plt.title("Gantry")
            plt.grid()
            plt.xlabel("X/Z (pixel)")
            plt.ylabel("Y (pixel)")
            plt.imshow(_array_g[y0:y1, x0:x1, :], extent=[x0, x1, y1, y0])
            plt.savefig("Gantry.png")

            im = Image("Gantry.png", 6 * inch, 6 * inch)
            Story.append(im)
            Story.append(Spacer(1, 25))
            linea = "Laser (Rojo), Radiacion (Verde)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

        if len(centro_laser_crucetas_colimador) !=0:
            _array_c = Dibuja_cruceta_en_array(array, centro_laser_crucetas_colimador, centro_radiacion_crucetas_colimador, 3, 1, (255, 0, 0), (0, 255, 0), False).array3D
            plt.clf()
            f = plt.figure()
            shape = _array_c.shape
            y0 = int(shape[0]/2) - 20
            y1 = int(shape[0]/2) + 20
            x0 = int(shape[1]/2) - 20
            x1 = int(shape[1]/2) + 20
            plt.title("Colimador")
            plt.grid()
            plt.xlabel("X (pixel)")
            plt.ylabel("Y (pixel)")
            plt.imshow(_array_c[y0:y1, x0:x1, :], extent=[x0, x1, y1, y0])
            plt.savefig("Colimador.png")
            im = Image("Colimador.png", 6 * inch, 6 * inch)
            Story.append(im)
            Story.append(Spacer(1, 25))
            linea = "Laser (Rojo), Radiacion (Verde)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

        if len(centro_laser_crucetas_mesa) !=0:
            _array_m = Dibuja_cruceta_en_array(array, centro_laser_crucetas_mesa, centro_radiacion_crucetas_mesa, 3, 1, (255, 0, 0), (0, 255, 0), False).array3D
            plt.clf()
            f = plt.figure()
            shape = _array_m.shape
            y0 = int(shape[0]/2) - 20
            y1 = int(shape[0]/2) + 20
            x0 = int(shape[1]/2) - 20
            x1 = int(shape[1]/2) + 20
            plt.title("Mesa")
            plt.grid()
            plt.xlabel("X (pixel)")
            plt.ylabel("Y (pixel)")
            plt.imshow(_array_m[y0:y1, x0:x1, :], extent=[x0, x1, y1, y0])
            plt.savefig("Mesa.png")
            im = Image("Mesa.png", 6 * inch, 6 * inch)
            Story.append(im)
            Story.append(Spacer(1, 25))
            linea = "Laser (Rojo), Radiacion (Verde)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

        doc.build(Story)

class Dibuja_cruceta_en_array:
    def __init__(self, _array, puntos_1, puntos_2, longitud, ancho, color_1, color_2, Flag):
        array = np.copy(_array)
        shape = array.shape

        if len(shape) == 3:
            if Flag == True:
                self.array3D = np.copy(array).astype(np.float)
            else:
                self.array3D = np.ones((shape[0], shape[1], shape[2]))*255
        else:
            if Flag == True:
                self.array3D = np.zeros((shape[0], shape[1], 3)).astype(np.float)
                for i in range(3):
                    self.array3D[:, :, i] = np.copy(array).astype(np.float)
            else:
                self.array3D = np.ones((shape[0], shape[1], 3)) * 255

        if Flag == True:
            for i in range(3):
                self.array3D[:, :, i] = self.array3D[:, :, i]/(2**16-1)

        shape = self.array3D.shape

        for m in range(len(puntos_1)):
            i_izd = puntos_1[m][0] - longitud
            if i_izd < 0:
                i_izd = 0
            i_dch = puntos_1[m][0] + longitud
            if i_dch >= shape[1]:
                i_dch = shape[1] - 1

            i_up = puntos_1[m][1] - longitud
            if i_up < 0:
                i_up = 0
            i_down = puntos_1[m][1] + longitud
            if i_down >= shape[0]:
                i_down = shape[0] - 1

            for i in range(i_izd, i_dch):
                for j in range(puntos_1[m][1] - ancho, puntos_1[m][1] + ancho):
                    for k in range(3):
                        self.array3D[j, i, k] = color_1[k]
            for i in range(i_up, i_down):
                for j in range(puntos_1[m][0] - ancho, puntos_1[m][0] + ancho):
                    for k in range(3):
                        self.array3D[i, j, k] = color_1[k]

        for m in range(len(puntos_2)):
            i_izd = puntos_2[m][0] - longitud
            if i_izd < 0:
                i_izd = 0
            i_dch = puntos_2[m][0] + longitud
            if i_dch >= shape[1]:
                i_dch = shape[1] - 1

            i_up = puntos_2[m][1] - longitud
            if i_up < 0:
                i_up = 0
            i_down = puntos_2[m][1] + longitud
            if i_down >= shape[0]:
                i_down = shape[0] - 1

            for i in range(int(i_izd), int(i_dch)):
                for j in range(int(puntos_2[m][1] - ancho), int(puntos_2[m][1] + ancho)):
                    for k in range(3):
                        self.array3D[j, i, k] = color_2[k]
            for i in range(int(i_up), int(i_down)):
                for j in range(int(puntos_2[m][0] - ancho), int(puntos_2[m][0] + ancho)):
                    for k in range(3):
                        self.array3D[i, j, k] = color_2[k]

# Ejecucion del Script
#Ball_bearing()