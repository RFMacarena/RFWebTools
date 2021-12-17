import os
import pydicom as dicom
import cv2
from skimage.feature import canny
import matplotlib.pyplot as plt
import numpy as np
from skimage.transform import hough_line, hough_line_peaks
from skimage.transform import hough_circle, hough_circle_peaks
import math
import sys
import time
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


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


# Definición de objeto recta a partir de un par de puntos
class Recta:
    def __init__(self):
        self.P0 = None
        self.P1 = None


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
        prod_esc = VAx * VBx + VAy * VBy

        # Coseno del angulo que forman ambos vectores
        coseno = prod_esc / (mod_A * mod_B)

        # Estudia paralelismo
        if abs(round(coseno, 4)) == 1:  # No hay corte o está muy alejado de la zona de interés
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


class Get_cortes_rectas:
    def __init__(self, rectas):
        self.corte01 = Corte_dos_rectas(rectas[0].P0, rectas[0].P1, rectas[1].P0, rectas[1].P1).corte
        self.corte02 = Corte_dos_rectas(rectas[0].P0, rectas[0].P1, rectas[2].P0, rectas[2].P1).corte
        self.corte03 = Corte_dos_rectas(rectas[0].P0, rectas[0].P1, rectas[3].P0, rectas[3].P1).corte
        self.corte12 = Corte_dos_rectas(rectas[1].P0, rectas[1].P1, rectas[2].P0, rectas[2].P1).corte
        self.corte13 = Corte_dos_rectas(rectas[1].P0, rectas[1].P1, rectas[3].P0, rectas[3].P1).corte
        self.corte23 = Corte_dos_rectas(rectas[2].P0, rectas[2].P1, rectas[3].P0, rectas[3].P1).corte


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


class Get_rectas_diagonales:
    def __init__(self, cortes, fuera_de_rango):
        self.puntos_cortes_validos = []
        self.punto_0_recta_diagonal_0 = None
        self.punto_1_recta_diagonal_0 = None
        self.punto_0_recta_diagonal_1 = None
        self.punto_1_recta_diagonal_1 = None

        if cortes.corte01[0] != None and abs(cortes.corte01[0]) < fuera_de_rango and cortes.corte01[1] != None and abs(
                cortes.corte01[1]) < fuera_de_rango:
            self.puntos_cortes_validos.append(cortes.corte01)
        if cortes.corte02[0] != None and abs(cortes.corte02[0]) < fuera_de_rango and cortes.corte02[1] != None and abs(
                cortes.corte02[1]) < fuera_de_rango:
            self.puntos_cortes_validos.append(cortes.corte02)
        if cortes.corte03[0] is not None and abs(cortes.corte03[0]) < fuera_de_rango and cortes.corte03[
            1] is not None and abs(cortes.corte03[1]) < fuera_de_rango:
            self.puntos_cortes_validos.append(cortes.corte03)
        if cortes.corte12[0] is not None and abs(cortes.corte12[0]) < fuera_de_rango and cortes.corte12[
            1] is not None and abs(cortes.corte12[1]) < fuera_de_rango:
            self.puntos_cortes_validos.append(cortes.corte12)
        if cortes.corte13[0] is not None and abs(cortes.corte13[0]) < fuera_de_rango and cortes.corte13[
            1] is not None and abs(cortes.corte13[1]) < fuera_de_rango:
            self.puntos_cortes_validos.append(cortes.corte13)
        if cortes.corte23[0] is not None and abs(cortes.corte23[0]) < fuera_de_rango and cortes.corte23[
            1] is not None and abs(cortes.corte23[1]) < fuera_de_rango:
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


# Clase donde se define
# Estructura basica de las imagenes dcm a procesar
class Imagen:
    def __init__(self):
        self.fichero = ""
        self.matriz_orig = None
        self.rows = ""
        self.columns = ""
        self.pixelsizemm = ""
        self.matriz_mediana = ""
        self.procesed_array = ""
        self.edges = []
        self.imagen_para_informe = ""

        # Rectas del campo de radiacion
        self.rectas = []
        for i in range(4):
            self.rectas.append(Recta())

        # Par de rectas diagonales del campo de radiacion
        self.diagonales = []
        for i in range(2):
            self.diagonales.append(Recta())

        # Centro del campo de radiacion en pixeles
        self.centro_radiacion_pixeles = ""

        # Centro del circulo de la esfera radiopaca que define la interseccion de los laseres
        self.centro_circulo_pixeles = ""
        self.radio_pixel = ""


# Lee el fichero de texto que contiene los nombres de los ficheros de imagenes.
#       Obtiene cada uno de los nombres de los ficheros dcm.
#       Verifica que exista cada uno de ellos.
#       Crea el array de clases imagenes.
#       Calcula centros de radiacion y laser

class Read_arguments:
    def __init__(self, im_dic, sigma, low, high):
        self.imagenes = []
        lista_ficheros = []
        lista_tipos = []

        # Crea la lista de los ficheros dcm
        try:
            # Prepara el array de imagenes
            for tipo, ds in im_dic.items():
                print(tipo)
                imagen = Imagen()

                rdh = Read_Dicom_Header(ds)

                imagen.rows = rdh.rows
                imagen.columns = rdh.columns
                # Para las imagenes de G90 y G180 hace un flip del eje "x" del flat panel.
                # Solo en estos dos casos se invierte el eje del flat panel respecto de un sistema de ejes de la sala.
                if tipo != 'G90' and tipo != 'G180':
                    imagen.matriz_orig = ds.pixel_array
                else:
                    imagen.matriz_orig = np.fliplr(ds.pixel_array)
                imagen.pixelsizemm = rdh.pizel_size_iso_mm



                # Aplica filtro de mediana 3x3
                imagen.matriz_mediana = cv2.medianBlur(imagen.matriz_orig, 3)

                matriz = imagen.matriz_mediana / 256
                imagen.procesed_array = matriz.astype(int)

                imagen.edges = canny(imagen.procesed_array, sigma=sigma, low_threshold=low, high_threshold=high)
                # plt.plot()
                # plt.imshow(self.imagenes[i].edges)
                # plt.show()

                # Rectas que definen el campo de radiacion
                # Precision de 0.5 grados.
                tested_angles = np.linspace(-np.pi / 2, np.pi / 2, 720, endpoint=False)
                h, theta, d = hough_line(imagen.edges, theta=tested_angles)
                row1, col1 = imagen.edges.shape
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
                    if n_rectas < 4:
                        imagen.rectas[n_rectas].P0 = Punto_0
                        imagen.rectas[n_rectas].P1 = Punto_1
                    else:
                        break
                    n_rectas += 1

                # Busca las diagonales del campo de radiacion
                if n_rectas == 4:
                    gc = Get_cortes_rectas(imagen.rectas)
                    """
                    print("Cortes:")
                    print("0 y 1: " + str(gc.corte01))
                    print("0 y 2: " + str(gc.corte02))
                    print("0 y 3: " + str(gc.corte03))
                    print("1 y 2: " + str(gc.corte12))
                    print("1 y 3: " + str(gc.corte13))
                    print("2 y 3: " + str(gc.corte23))
                    """
                    gd = Get_rectas_diagonales(gc, imagen.rows)
                    """
                    print("Puntos de la diagonal 0:")
                    print(str(gd.punto_0_recta_diagonal_0) + " y " + str(gd.punto_1_recta_diagonal_0))
                    print("Puntos de la diagonal 1:")
                    print(str(gd.punto_0_recta_diagonal_1) + " y " + str(gd.punto_1_recta_diagonal_1))
                    """
                    imagen.diagonales[0].P0 = gd.punto_0_recta_diagonal_0
                    imagen.diagonales[0].P1 = gd.punto_1_recta_diagonal_0
                    imagen.diagonales[1].P0 = gd.punto_0_recta_diagonal_1
                    imagen.diagonales[1].P1 = gd.punto_1_recta_diagonal_1

                    # Corte de las diagonales
                    cdr = Corte_dos_rectas(gd.punto_0_recta_diagonal_0, gd.punto_1_recta_diagonal_0,
                                           gd.punto_0_recta_diagonal_1, gd.punto_1_recta_diagonal_1)
                    imagen.centro_radiacion_pixeles = cdr.corte
                    # print("Centro de radiacion: " + str(self.imagenes[i].centro_radiacion_pixeles))
                else:
                    print("Error!!! Nº de rectas detectadas para campo de radiacion en imagen " +
                          imagen.fichero + " distinto a 4(" + str(n_rectas) + ")!!!")
                    sys.exit()

                # Continua con la deteccion del circulo
                hough_radii = np.arange(5, 20, 2)
                hough_res = hough_circle(imagen.edges, hough_radii)

                # Busca solo un circulo
                accums, cx, cy, radii = hough_circle_peaks(hough_res, hough_radii, total_num_peaks=1)
                if len(cx) == 0:  # No encuentra un circulo
                    print(
                        "Error!!! Circulo no detectado en " + imagen.fichero + " !!! Modifica el umbral maximo del filtro de Canny.")
                    sys.exit()
                else:
                    imagen.centro_circulo_pixeles = (cx[0], cy[0])
                    imagen.radio_pixel = radii[0]

                # Crea imagen para informe con las transformadas de hough
                imagen.imagen_para_informe = imagen.fichero[0:len(imagen.fichero) - 4] + ".png"
                image = np.copy(imagen.procesed_array)
                print(f'Centro pixel: {imagen.centro_circulo_pixeles}')
                #plt.imshow(imagen)
                #plt.show()
                self.zoom_i = 275
                self.zoom_f = 775
                # Añade Circulo
                cv2.circle(image, imagen.centro_circulo_pixeles,
                           imagen.radio_pixel, (0, 0, 255), 1)

                # Añade Centro circulo
                Pa = (imagen.centro_circulo_pixeles[0] - 2,
                      imagen.centro_circulo_pixeles[1])
                Pb = (imagen.centro_circulo_pixeles[0] + 2,
                      imagen.centro_circulo_pixeles[1])
                Pc = (imagen.centro_circulo_pixeles[0],
                      imagen.centro_circulo_pixeles[1] - 2)
                Pd = (imagen.centro_circulo_pixeles[0],
                      imagen.centro_circulo_pixeles[1] + 2)
                cv2.line(image, Pa, Pb, (0, 0, 255), 1)
                cv2.line(image, Pc, Pd, (0, 0, 255), 1)

                # Añade Rectas
                for j in range(4):
                    P0 = (int(imagen.rectas[j].P0[0]),
                          int(imagen.rectas[j].P0[1]))
                    P1 = (int(imagen.rectas[j].P1[0]),
                          int(imagen.rectas[j].P1[1]))
                    cv2.line(image, P0, P1, (0, 0, 255), 1)

                # Añade Diagonales
                for j in range(2):
                    P0 = (int(imagen.diagonales[j].P0[0]),
                          int(imagen.diagonales[j].P0[1]))
                    P1 = (int(imagen.diagonales[j].P1[0]),
                          int(imagen.diagonales[j].P1[1]))
                    cv2.line(image, P0, P1, (0, 0, 255), 1)

                img_8bytes = (image).astype('uint8')
                cv2.imwrite(imagen.imagen_para_informe, img_8bytes[self.zoom_i:self.zoom_f, self.zoom_i:self.zoom_f])
                self.imagenes.append(imagen)

        except IOError:
            print("Error!!! El fichero con los nombres de las imagenes no existe!!!")
            sys.exit()


class Read_arguments_from_txt:
    def __init__(self, file, sigma, low, high):
        self.imagenes = []
        lista_ficheros = []
        lista_tipos = []

        # Crea la lista de los ficheros dcm
        try:
            with open(file) as f:
                buffer = f.readlines()
                for i in buffer:
                    cad = i.strip()
                    pos = cad.find(':')
                    lista_tipos.append(cad[0:pos])
                    cad = cad[pos + 1:]
                    cad = cad.strip()
                    lista_ficheros.append(cad)
                # print(lista_tipos)
                # print(lista_ficheros)

                # Chequea que existan todos los ficheros dcm con la posibilidad de que no exista C90 para APEX
                for i in range(len(lista_ficheros)):
                    if os.path.exists(lista_ficheros[i]) == False and lista_tipos[
                        i] != "G0_C90_M0":  # APEX no admite giro de colimador de 90º
                        print("Error!!! No existe el fichero de imagen \"" + lista_tipos[i] + "\"")
                        sys.exit()

                # Prepara el array de imagenes
                for i in range(len(buffer)):
                    self.imagenes.append(Imagen())  # Inicializa objeto clase imagen
                    self.imagenes[i].fichero = lista_ficheros[i]
                    if os.path.exists(lista_ficheros[i]) == False and lista_tipos[i] == "G0_C90_M0":  # APEX
                        continue

                    print("Procesando imagen " + self.imagenes[i].fichero + " ...")

                    ds = dicom.dcmread(self.imagenes[i].fichero)
                    rdh = Read_Dicom_Header(ds)

                    self.imagenes[i].rows = rdh.rows
                    self.imagenes[i].columns = rdh.columns
                    # Para las imagenes de G90 y G180 hace un flip del eje "x" del flat panel.
                    # Solo en estos dos casos se invierte el eje del flat panel respecto de un sistema de ejes de la sala.
                    if i != 1 and i != 2:
                        self.imagenes[i].matriz_orig = ds.pixel_array
                    else:
                        self.imagenes[i].matriz_orig = np.fliplr(ds.pixel_array)
                    self.imagenes[i].pixelsizemm = rdh.pizel_size_iso_mm

                    # Aplica filtro de mediana 3x3
                    self.imagenes[i].matriz_mediana = cv2.medianBlur(self.imagenes[i].matriz_orig, 3)

                    matriz = self.imagenes[i].matriz_mediana / 256
                    self.imagenes[i].procesed_array = matriz.astype(int)

                    self.imagenes[i].edges = canny(self.imagenes[i].procesed_array, sigma=sigma, low_threshold=low,
                                                   high_threshold=high)
                    # plt.plot()
                    # plt.imshow(self.imagenes[i].edges)
                    # plt.show()

                    # Rectas que definen el campo de radiacion
                    # Precision de 0.5 grados.
                    tested_angles = np.linspace(-np.pi / 2, np.pi / 2, 720, endpoint=False)
                    h, theta, d = hough_line(self.imagenes[i].edges, theta=tested_angles)
                    row1, col1 = self.imagenes[i].edges.shape
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
                        if n_rectas < 4:
                            self.imagenes[i].rectas[n_rectas].P0 = Punto_0
                            self.imagenes[i].rectas[n_rectas].P1 = Punto_1
                        else:
                            break
                        n_rectas += 1

                    # Busca las diagonales del campo de radiacion
                    if n_rectas == 4:
                        gc = Get_cortes_rectas(self.imagenes[i].rectas)
                        """
                        print("Cortes:")
                        print("0 y 1: " + str(gc.corte01))
                        print("0 y 2: " + str(gc.corte02))
                        print("0 y 3: " + str(gc.corte03))
                        print("1 y 2: " + str(gc.corte12))
                        print("1 y 3: " + str(gc.corte13))
                        print("2 y 3: " + str(gc.corte23))
                        """
                        gd = Get_rectas_diagonales(gc, self.imagenes[i].rows)
                        """
                        print("Puntos de la diagonal 0:")
                        print(str(gd.punto_0_recta_diagonal_0) + " y " + str(gd.punto_1_recta_diagonal_0))
                        print("Puntos de la diagonal 1:")
                        print(str(gd.punto_0_recta_diagonal_1) + " y " + str(gd.punto_1_recta_diagonal_1))
                        """
                        self.imagenes[i].diagonales[0].P0 = gd.punto_0_recta_diagonal_0
                        self.imagenes[i].diagonales[0].P1 = gd.punto_1_recta_diagonal_0
                        self.imagenes[i].diagonales[1].P0 = gd.punto_0_recta_diagonal_1
                        self.imagenes[i].diagonales[1].P1 = gd.punto_1_recta_diagonal_1

                        # Corte de las diagonales
                        cdr = Corte_dos_rectas(gd.punto_0_recta_diagonal_0, gd.punto_1_recta_diagonal_0,
                                               gd.punto_0_recta_diagonal_1, gd.punto_1_recta_diagonal_1)
                        self.imagenes[i].centro_radiacion_pixeles = cdr.corte
                        # print("Centro de radiacion: " + str(self.imagenes[i].centro_radiacion_pixeles))
                    else:
                        print("Error!!! Nº de rectas detectadas para campo de radiacion en imagen " +
                              self.imagenes[i].fichero + " distinto a 4(" + str(n_rectas) + ")!!!")
                        sys.exit()

                    # Continua con la deteccion del circulo
                    hough_radii = np.arange(5, 20, 2)
                    hough_res = hough_circle(self.imagenes[i].edges, hough_radii)

                    # Busca solo un circulo
                    accums, cx, cy, radii = hough_circle_peaks(hough_res, hough_radii, total_num_peaks=1)
                    if len(cx) == 0:  # No encuentra un circulo
                        print("Error!!! Circulo no detectado en " + self.imagenes[
                            i].fichero + " !!! Modifica el umbral maximo del filtro de Canny.")
                        sys.exit()
                    else:
                        self.imagenes[i].centro_circulo_pixeles = (cx[0], cy[0])
                        self.imagenes[i].radio_pixel = radii[0]

                    # Crea imagen para informe con las transformadas de hough
                    self.imagenes[i].imagen_para_informe = self.imagenes[i].fichero[
                                                           0:len(self.imagenes[i].fichero) - 4] + ".png"
                    imagen = np.copy(self.imagenes[i].procesed_array)
                    self.zoom_i = 275
                    self.zoom_f = 775
                    # Añade Circulo
                    cv2.circle(imagen, self.imagenes[i].centro_circulo_pixeles,
                               self.imagenes[i].radio_pixel, (0, 0, 255), 1)

                    # Añade Centro circulo
                    Pa = (self.imagenes[i].centro_circulo_pixeles[0] - 2,
                          self.imagenes[i].centro_circulo_pixeles[1])
                    Pb = (self.imagenes[i].centro_circulo_pixeles[0] + 2,
                          self.imagenes[i].centro_circulo_pixeles[1])
                    Pc = (self.imagenes[i].centro_circulo_pixeles[0],
                          self.imagenes[i].centro_circulo_pixeles[1] - 2)
                    Pd = (self.imagenes[i].centro_circulo_pixeles[0],
                          self.imagenes[i].centro_circulo_pixeles[1] + 2)
                    cv2.line(imagen, Pa, Pb, (0, 0, 255), 1)
                    cv2.line(imagen, Pc, Pd, (0, 0, 255), 1)

                    # Añade Rectas
                    for j in range(4):
                        P0 = (int(self.imagenes[i].rectas[j].P0[0]),
                              int(self.imagenes[i].rectas[j].P0[1]))
                        P1 = (int(self.imagenes[i].rectas[j].P1[0]),
                              int(self.imagenes[i].rectas[j].P1[1]))
                        cv2.line(imagen, P0, P1, (0, 0, 255), 1)

                    # Añade Diagonales
                    for j in range(2):
                        P0 = (int(self.imagenes[i].diagonales[j].P0[0]),
                              int(self.imagenes[i].diagonales[j].P0[1]))
                        P1 = (int(self.imagenes[i].diagonales[j].P1[0]),
                              int(self.imagenes[i].diagonales[j].P1[1]))
                        cv2.line(imagen, P0, P1, (0, 0, 255), 1)

                    img_8bytes = (imagen).astype('uint8')
                    cv2.imwrite(self.imagenes[i].imagen_para_informe,
                                img_8bytes[self.zoom_i:self.zoom_f, self.zoom_i:self.zoom_f])

        except IOError:
            print("Error!!! El fichero con los nombres de las imagenes no existe!!!")
            sys.exit()


class Read_Dicom_Header:
    def __init__(self, ds):
        self.rows = ds.get("Rows")
        self.columns = ds.get("Columns")
        self.distancia_foco_panel_mm = ds.get("RTImageSID")
        pizel_size_real_mm = ds.get("ImagePlanePixelSpacing")[0]
        radiation_machine_sad = ds.get("RadiationMachineSAD")
        self.pizel_size_iso_mm = (radiation_machine_sad / self.distancia_foco_panel_mm) * pizel_size_real_mm


class Get_Laser:
    def __init__(self, imagenes):
        # Crea el objeto Laser 3D. Hay tres, uno para gantry (0), colimador (1) y mesa (2)
        self.laser3D = []
        for i in range(3):
            self.laser3D.append(Laser())

        # Laser 3D considerando todas las imagenes en forma conjunta
        self.X_total_laser = []
        self.Y_total_laser = []
        self.Z_total_laser = []

        # De las imagenes de gantry
        self.OK_gantry = True
        for i in range(4):
            if imagenes[i].matriz_orig is None:
                self.OK_gantry = False
                break
        if self.OK_gantry == True:
            self.laser3D[0].X = []
            self.laser3D[0].Y = []
            self.laser3D[0].Z = []
            self.laser3D[0].X.append(imagenes[0].centro_circulo_pixeles[0])
            self.laser3D[0].Y.append(imagenes[0].centro_circulo_pixeles[1])
            self.laser3D[0].Z.append(imagenes[1].centro_circulo_pixeles[0])
            self.laser3D[0].Y.append(imagenes[1].centro_circulo_pixeles[1])
            self.laser3D[0].X.append(imagenes[2].centro_circulo_pixeles[0])
            self.laser3D[0].Y.append(imagenes[2].centro_circulo_pixeles[1])
            self.laser3D[0].Z.append(imagenes[3].centro_circulo_pixeles[0])
            self.laser3D[0].Y.append(imagenes[3].centro_circulo_pixeles[1])
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
        lista = [0, 4, 5, 6]  # Colimador 0, 90, 180 y 270
        for i in lista:
            if imagenes[i].matriz_orig is None and i != 4:  # El APEX no admite giro de colimador a 90º !!!
                self.OK_colimador = False
                break
        if self.OK_colimador == True:
            self.laser3D[1].X = []
            self.laser3D[1].Y = []
            self.laser3D[1].X.append(imagenes[lista[0]].centro_circulo_pixeles[0])
            self.laser3D[1].Y.append(imagenes[lista[0]].centro_circulo_pixeles[1])
            if imagenes[lista[1]].matriz_orig is not None:
                self.laser3D[1].X.append(imagenes[lista[1]].centro_circulo_pixeles[0])
                self.laser3D[1].Y.append(imagenes[lista[1]].centro_circulo_pixeles[1])
            self.laser3D[1].X.append(imagenes[lista[2]].centro_circulo_pixeles[0])
            self.laser3D[1].Y.append(imagenes[lista[2]].centro_circulo_pixeles[1])
            self.laser3D[1].X.append(imagenes[lista[3]].centro_circulo_pixeles[0])
            self.laser3D[1].Y.append(imagenes[lista[3]].centro_circulo_pixeles[1])
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
        self.OK_mesa = True
        lista = [0, 7, 8]  # Mesa 0, 90 y 270
        for i in lista:
            if imagenes[i].matriz_orig is None:
                self.OK_mesa = False
                break
        if self.OK_mesa == True:
            self.laser3D[2].X = []
            self.laser3D[2].Y = []
            self.laser3D[2].X.append(imagenes[lista[0]].centro_circulo_pixeles[0])
            self.laser3D[2].Y.append(imagenes[lista[0]].centro_circulo_pixeles[1])
            self.laser3D[2].X.append(imagenes[lista[1]].centro_circulo_pixeles[0])
            self.laser3D[2].Y.append(imagenes[lista[1]].centro_circulo_pixeles[1])
            self.laser3D[2].X.append(imagenes[lista[2]].centro_circulo_pixeles[0])
            self.laser3D[2].Y.append(imagenes[lista[2]].centro_circulo_pixeles[1])
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


# Calcula la posicion 3D del centro de radiacion para gantry, colimador, mesa y combinada
class Get_centro_radiacion:
    def __init__(self, imagenes):
        # Crea el objeto Radiacion 3D, uno para gantry (0), colimador (1) y mesa (2)
        self.radiacion3D = []
        for i in range(3):
            self.radiacion3D.append(Radiacion())

        # Centro de radiacion 3D considerando todas las imagenes en forma conjunta
        self.X_total_radiacion = []
        self.Y_total_radiacion = []
        self.Z_total_radiacion = []

        # De las imagenes de gantry
        self.OK_gantry = True
        for i in range(4):
            if imagenes[i].matriz_orig is None:
                self.OK_gantry = False
                break
        if self.OK_gantry == True:
            self.radiacion3D[0].X = []
            self.radiacion3D[0].Y = []
            self.radiacion3D[0].Z = []
            self.radiacion3D[0].X.append(imagenes[0].centro_radiacion_pixeles[0])
            self.radiacion3D[0].Y.append(imagenes[0].centro_radiacion_pixeles[1])
            self.radiacion3D[0].Z.append(imagenes[1].centro_radiacion_pixeles[0])
            self.radiacion3D[0].Y.append(imagenes[1].centro_radiacion_pixeles[1])
            self.radiacion3D[0].X.append(imagenes[2].centro_radiacion_pixeles[0])
            self.radiacion3D[0].Y.append(imagenes[2].centro_radiacion_pixeles[1])
            self.radiacion3D[0].Z.append(imagenes[3].centro_radiacion_pixeles[0])
            self.radiacion3D[0].Y.append(imagenes[3].centro_radiacion_pixeles[1])
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
        lista = [0, 4, 5, 6]
        for i in lista:
            if imagenes[i].matriz_orig is None and i != 4:  # El APEX no admite giro de colimador a 90º !!!:
                self.OK_colimador = False
                break
        if self.OK_colimador == True:
            self.radiacion3D[1].X = []
            self.radiacion3D[1].Y = []
            self.radiacion3D[1].X.append(imagenes[lista[0]].centro_radiacion_pixeles[0])
            self.radiacion3D[1].Y.append(imagenes[lista[0]].centro_radiacion_pixeles[1])
            if imagenes[lista[1]].matriz_orig is not None:
                self.radiacion3D[1].X.append(imagenes[lista[1]].centro_radiacion_pixeles[0])
                self.radiacion3D[1].Y.append(imagenes[lista[1]].centro_radiacion_pixeles[1])
            self.radiacion3D[1].X.append(imagenes[lista[2]].centro_radiacion_pixeles[0])
            self.radiacion3D[1].Y.append(imagenes[lista[2]].centro_radiacion_pixeles[1])
            self.radiacion3D[1].X.append(imagenes[lista[3]].centro_radiacion_pixeles[0])
            self.radiacion3D[1].Y.append(imagenes[lista[3]].centro_radiacion_pixeles[1])
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
        lista = [0, 7, 8]
        for i in lista:
            if imagenes[i].matriz_orig is None:
                self.OK_mesa = False
                break
        if self.OK_mesa == True:
            self.radiacion3D[2].X = []
            self.radiacion3D[2].Y = []
            self.radiacion3D[2].X.append(imagenes[lista[0]].centro_radiacion_pixeles[0])
            self.radiacion3D[2].Y.append(imagenes[lista[0]].centro_radiacion_pixeles[1])
            self.radiacion3D[2].X.append(imagenes[lista[1]].centro_radiacion_pixeles[0])
            self.radiacion3D[2].Y.append(imagenes[lista[1]].centro_radiacion_pixeles[1])
            self.radiacion3D[2].X.append(imagenes[lista[2]].centro_radiacion_pixeles[0])
            self.radiacion3D[2].Y.append(imagenes[lista[2]].centro_radiacion_pixeles[1])
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


class Evaluacion:
    def __init__(self, imagenes, laser, radiacion):
        Tolerancia_mm_diferencia_1D = 0.7
        Tolerancia_mm_diferencia_3D = 1.0
        pixel_size_mm = imagenes[0].pixelsizemm

        if laser.OK_gantry == True and radiacion.OK_gantry == True:
            self.x_gantry = laser.laser3D[0].Pos3D_media[0] - radiacion.radiacion3D[0].Pos3D_media[0]
            if abs(self.x_gantry * pixel_size_mm) > Tolerancia_mm_diferencia_1D:
                print("Excedida Tolerancia 1D en \'X' para diferencia entre laser y radiacion en gantry: " + str(
                    self.x_gantry * pixel_size_mm) + " !!!")
            self.y_gantry = laser.laser3D[0].Pos3D_media[1] - radiacion.radiacion3D[0].Pos3D_media[1]
            if abs(self.y_gantry * pixel_size_mm) > Tolerancia_mm_diferencia_1D:
                print("Excedida Tolerancia 1D en \'Y' para diferencia entre laser y radiacion en gantry: " + str(
                    self.y_gantry * pixel_size_mm) + " !!!")
            self.z_gantry = laser.laser3D[0].Pos3D_media[2] - radiacion.radiacion3D[0].Pos3D_media[2]
            if abs(self.z_gantry * pixel_size_mm) > Tolerancia_mm_diferencia_1D:
                print("Excedida Tolerancia 1D en \'Z' para diferencia entre laser y radiacion en gantry: " + str(
                    self.z_gantry * pixel_size_mm) + " !!!")
            self.distancia3D_pixeles_gantry = np.sqrt(
                np.power(self.x_gantry, 2) + np.power(self.y_gantry, 2) + np.power(self.z_gantry, 2))
            if abs(self.distancia3D_pixeles_gantry * pixel_size_mm) > Tolerancia_mm_diferencia_3D:
                print("Excedida Tolerancia 3D para diferencia entre laser y radiacion en gantry: " + str(
                    self.distancia3D_pixeles_gantry * pixel_size_mm) + " !!!")

        if laser.OK_colimador == True and radiacion.OK_colimador:
            self.x_colimador = laser.laser3D[1].Pos3D_media[0] - radiacion.radiacion3D[1].Pos3D_media[0]
            if abs(self.x_colimador * pixel_size_mm) > Tolerancia_mm_diferencia_1D:
                print("Excedida Tolerancia 1D en \'X' para diferencia entre laser y radiacion en colimador: " + str(
                    self.x_colimador * pixel_size_mm) + " !!!")
            self.y_colimador = laser.laser3D[1].Pos3D_media[1] - radiacion.radiacion3D[1].Pos3D_media[1]
            if abs(self.y_colimador * pixel_size_mm) > Tolerancia_mm_diferencia_1D:
                print("Excedida Tolerancia 1D en \'Y' para diferencia entre laser y radiacion en colimador: " + str(
                    self.y_colimador * pixel_size_mm) + " !!!")
            self.distancia3D_pixeles_colimador = np.sqrt(np.power(self.x_colimador, 2) + np.power(self.y_colimador, 2))
            if abs(self.distancia3D_pixeles_colimador * pixel_size_mm) > Tolerancia_mm_diferencia_3D:
                print("Excedida Tolerancia 3D para diferencia entre laser y radiacion en colimador: " + str(
                    self.distancia3D_pixeles_colimador * pixel_size_mm) + " !!!")

        if laser.OK_mesa == True and radiacion.OK_mesa == True:
            self.x_mesa = laser.laser3D[2].Pos3D_media[0] - radiacion.radiacion3D[2].Pos3D_media[0]
            if abs(self.x_mesa * pixel_size_mm) > Tolerancia_mm_diferencia_1D:
                print("Excedida Tolerancia 1D en \'X' para diferencia entre laser y radiacion en mesa: " + str(
                    self.x_mesa * pixel_size_mm) + " !!!")
            self.y_mesa = laser.laser3D[2].Pos3D_media[1] - radiacion.radiacion3D[2].Pos3D_media[1]
            if abs(self.y_mesa * pixel_size_mm) > Tolerancia_mm_diferencia_1D:
                print("Excedida Tolerancia 1D en \'Y' para diferencia entre laser y radiacion en mesa: " + str(
                    self.y_mesa * pixel_size_mm) + " !!!")
            self.distancia3D_pixeles_mesa = np.sqrt(np.power(self.x_mesa, 2) + np.power(self.y_mesa, 2))
            if abs(self.distancia3D_pixeles_mesa * pixel_size_mm) > Tolerancia_mm_diferencia_3D:
                print("Excedida Tolerancia 3D para diferencia entre laser y radiacion en mesa: " + str(
                    self.distancia3D_pixeles_mesa * pixel_size_mm) + " !!!")

        # Global. Todas las imagenes en conjunto
        if laser.media_x_total_laser is not None and radiacion.media_x_total_radiacion is not None:
            self.x_global = laser.media_x_total_laser - radiacion.media_x_total_radiacion
            if abs(self.x_global * pixel_size_mm) > Tolerancia_mm_diferencia_1D:
                print("Excedida Tolerancia 1D en \'X' para diferencia entre laser y radiacion en global: " + str(
                    self.x_global * pixel_size_mm) + " !!!")
        else:
            self.x_global = None

        if laser.media_y_total_laser is not None and radiacion.media_y_total_radiacion is not None:
            self.y_global = laser.media_y_total_laser - radiacion.media_y_total_radiacion
            if abs(self.y_global * pixel_size_mm) > Tolerancia_mm_diferencia_1D:
                print("Excedida Tolerancia 1D en \'Y' para diferencia entre laser y radiacion en global: " + str(
                    self.y_global * pixel_size_mm) + " !!!")
        else:
            self.y_global = None

        if laser.media_z_total_laser is not None and radiacion.media_z_total_radiacion is not None:
            self.z_global = laser.media_z_total_laser - radiacion.media_z_total_radiacion
            if abs(self.z_global * pixel_size_mm) > Tolerancia_mm_diferencia_1D:
                print("Excedida Tolerancia 1D en \'Z' para diferencia entre laser y radiacion en global: " + str(
                    self.z_global * pixel_size_mm) + " !!!")
        else:
            self.z_global = None

        if self.x_global is not None and self.y_global is not None and self.z_global is not None:
            self.distancia3D_pixeles_global = np.sqrt(
                np.power(self.x_global, 2) + np.power(self.y_global, 2) + np.power(self.z_global, 2))
            if abs(self.distancia3D_pixeles_global * pixel_size_mm) > Tolerancia_mm_diferencia_3D:
                print("Excedida Tolerancia 3D para diferencia entre laser y radiacion en global: " + str(
                    self.distancia3D_pixeles_global * pixel_size_mm) + " !!!")
        else:
            if self.z_global is None:
                self.distancia3D_pixeles_global = np.sqrt(np.power(self.x_global, 2) + np.power(self.y_global, 2))
                if abs(self.distancia3D_pixeles_global * pixel_size_mm) > Tolerancia_mm_diferencia_3D:
                    print("Excedida Tolerancia 3D para diferencia entre laser y radiacion en global: " + str(
                        self.distancia3D_pixeles_global * pixel_size_mm) + " !!!")


class Dibuja_cruceta_en_array:
    def __init__(self, _array, puntos_1, puntos_2, longitud, ancho, color_1, color_2, Flag):
        array = np.copy(_array)
        shape = array.shape

        if len(shape) == 3:
            if Flag == True:
                self.array3D = np.copy(array).astype(np.float)
            else:
                self.array3D = np.ones((shape[0], shape[1], shape[2])) * 255
        else:
            if Flag == True:
                self.array3D = np.zeros((shape[0], shape[1], 3)).astype(np.float)
                for i in range(3):
                    self.array3D[:, :, i] = np.copy(array).astype(np.float)
            else:
                self.array3D = np.ones((shape[0], shape[1], 3)) * 255

        if Flag == True:
            for i in range(3):
                self.array3D[:, :, i] = self.array3D[:, :, i] / (2 ** 16 - 1)

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


class Genera_Informe:
    def __init__(self, output_path, array, imagenes, laser, radiacion):
        centro_laser_crucetas_gantry = []
        centro_radiacion_crucetas_gantry = []
        centro_laser_crucetas_colimador = []
        centro_radiacion_crucetas_colimador = []
        centro_laser_crucetas_mesa = []
        centro_radiacion_crucetas_mesa = []

        cadena_0 = (time.strftime("%d/%m/%y")).replace("/", "_")
        filename_out = output_path + "Informe_Ball_Bearing_" + cadena_0 + ".pdf"
        print("¡¡¡Se va a crear Informe de test W/L : " + filename_out + "!!!")

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

        linea = "Tamaño Pixel (mm): " + str(
            imagenes[0].pixelsizemm)  # Todas las imagenes deben tener el mismo tamaño de pixel
        ptext = '<font size="10">' + linea + '</font>'
        Story.append(Paragraph(ptext, styles["Normal"]))
        Story.append(Spacer(1, 25))

        plt.clf()
        f = plt.figure()
        if laser.OK_gantry and radiacion.OK_gantry == True:
            linea = "Gantry:"
            ptext = '<font size="15">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 25))

            for i in range(0, 4):
                linea = str(imagenes[i].fichero)
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

                im = Image(imagenes[i].imagen_para_informe, 2 * inch, 2 * inch)
                Story.append(im)
                Story.append(Spacer(1, 12))
                Story.append(Spacer(1, 12))

            Story.append(Spacer(1, 5))
            linea = "Laser X, Y, Z:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 5))

            linea = "... 0: (" + str(imagenes[0].centro_circulo_pixeles[0]) + ", " + str(
                imagenes[0].centro_circulo_pixeles[1]) + \
                    ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "..90: (---, " + str(imagenes[1].centro_circulo_pixeles[1]) + ", " + str(
                imagenes[1].centro_circulo_pixeles[0]) + ")"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".180: (" + str(imagenes[2].centro_circulo_pixeles[0]) + ", " + str(
                imagenes[2].centro_circulo_pixeles[1]) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".270: (---, " + str(imagenes[3].centro_circulo_pixeles[1]) + ", " + str(
                imagenes[3].centro_circulo_pixeles[0]) + ")"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = "Radiacion X, Y, Z:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 5))

            linea = "... 0: (" + str("{:.2f}".format(imagenes[0].centro_radiacion_pixeles[0])) + ", " + \
                    str("{:.2f}".format(imagenes[0].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "..90: (---, " + str("{:.2f}".format(imagenes[1].centro_radiacion_pixeles[1])) + ", " + \
                    str("{:.2f}".format(imagenes[1].centro_radiacion_pixeles[0])) + ")"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".180: (" + str("{:.2f}".format(imagenes[2].centro_radiacion_pixeles[0])) + ", " + \
                    str("{:.2f}".format(imagenes[2].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".270: (---, " + str("{:.2f}".format(imagenes[3].centro_radiacion_pixeles[1])) + ", " + \
                    str("{:.2f}".format(imagenes[3].centro_radiacion_pixeles[0])) + ")"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = "Posicion 3D Laser: (" + str("{:.2f}".format(laser.laser3D[0].Pos3D_media[0])) + ", " + str(
                "{:.2f}".format(laser.laser3D[0].Pos3D_media[1])) + ", " + str(
                "{:.2f}".format(laser.laser3D[0].Pos3D_media[2])) + ") pixeles"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Posicion 3D Radiacion: (" + str(
                "{:.2f}".format(radiacion.radiacion3D[0].Pos3D_media[0])) + ", " + str(
                "{:.2f}".format(radiacion.radiacion3D[0].Pos3D_media[1])) + ", " + str(
                "{:.2f}".format(radiacion.radiacion3D[0].Pos3D_media[2])) + ") pixeles"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            dif_x = laser.laser3D[0].Pos3D_media[0] - radiacion.radiacion3D[0].Pos3D_media[0]
            dif_y = laser.laser3D[0].Pos3D_media[1] - radiacion.radiacion3D[0].Pos3D_media[1]
            dif_z = laser.laser3D[0].Pos3D_media[2] - radiacion.radiacion3D[0].Pos3D_media[2]
            distancia3D_pixeles = np.sqrt(np.power(dif_x, 2) + np.power(dif_y, 2) + np.power(dif_z, 2))
            distancia3D_mm = distancia3D_pixeles * imagenes[0].pixelsizemm

            Story.append(Spacer(1, 5))
            linea = "Solo Gantry:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " + \
                    str("{:.2f}".format(distancia3D_mm)) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia Componentes 2D Laser-Radiacion (X, Y, Z): (" + str("{:.2f}".format(dif_x)) + ", " + str(
                "{:.2f}".format(dif_y)) + ", " + \
                    str("{:.2f}".format(dif_z)) + ") pixeles, (" + str(
                "{:.2f}".format(dif_x * imagenes[0].pixelsizemm)) + ", " + str(
                "{:.2f}".format(dif_y * imagenes[0].pixelsizemm)) + \
                    ", " + str("{:.2f}".format(dif_z * imagenes[0].pixelsizemm)) + ") mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            # Genera Grafica. Gantry, Colimador y Mesa
            _abcisas = [0, 90, 180, 270]
            _x_o_z_dif = []
            _y_dif = []
            for i in range(0, 4):
                _x_o_z_dif.append(float(
                    imagenes[i].centro_circulo_pixeles[0] - imagenes[i].centro_radiacion_pixeles[
                        0]) * imagenes[i].pixelsizemm)
                _y_dif.append(float(imagenes[i].centro_circulo_pixeles[1] - imagenes[i].centro_radiacion_pixeles[
                    1]) * imagenes[i].pixelsizemm)
                centro_laser_crucetas_gantry.append(imagenes[i].centro_circulo_pixeles)
                centro_radiacion_crucetas_gantry.append(imagenes[i].centro_radiacion_pixeles)

            plt.subplot(131)
            plt.title("Gantry")
            plt.grid()
            plt.xlabel("º")
            plt.ylabel("mm")
            plt.plot(_abcisas, _x_o_z_dif, label="X/Z")
            plt.plot(_abcisas, _y_dif, label="Y")
            plt.legend(["X/Z", "Y"])

        if laser.OK_colimador == True and radiacion.OK_colimador == True:
            Story.append(Spacer(1, 25))
            linea = "Colimador:"
            ptext = '<font size="15">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 25))

            lista = [0, 4, 5, 6]
            for i in lista:
                if imagenes[i].matriz_orig is not None:
                    linea = str(imagenes[i].fichero)
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

                    im = Image(imagenes[i].imagen_para_informe, 2 * inch, 2 * inch)
                    Story.append(im)
                    Story.append(Spacer(1, 12))
                    Story.append(Spacer(1, 12))

            Story.append(Spacer(1, 5))
            linea = "Laser X, Y, Z:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 5))

            linea = "... 0: (" + str(imagenes[lista[0]].centro_circulo_pixeles[0]) + ", " + str(
                imagenes[lista[0]].centro_circulo_pixeles[1]) + \
                    ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            if imagenes[lista[1]].matriz_orig is not None:
                linea = "..90: (" + str(imagenes[lista[1]].centro_circulo_pixeles[0]) + ", " + str(
                    imagenes[lista[1]].centro_circulo_pixeles[1]) + ", ---)"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".180: (" + str(imagenes[lista[2]].centro_circulo_pixeles[0]) + ", " + str(
                imagenes[lista[2]].centro_circulo_pixeles[1]) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".270: (" + str(imagenes[lista[3]].centro_circulo_pixeles[0]) + ", " + str(
                imagenes[lista[3]].centro_circulo_pixeles[1]) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = "Radiacion X, Y, Z:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 5))

            linea = "... 0: (" + str("{:.2f}".format(imagenes[lista[0]].centro_radiacion_pixeles[0])) + ", " + \
                    str("{:.2f}".format(imagenes[lista[0]].centro_radiacion_pixeles[1])) + ",---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            if imagenes[lista[1]].matriz_orig is not None:
                linea = "..90: (" + str("{:.2f}".format(imagenes[lista[1]].centro_radiacion_pixeles[0])) + ", " + \
                        str("{:.2f}".format(imagenes[lista[1]].centro_radiacion_pixeles[1])) + ", ---)"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".180: (" + str("{:.2f}".format(imagenes[lista[2]].centro_radiacion_pixeles[0])) + ", " + \
                    str("{:.2f}".format(imagenes[lista[2]].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".270: (" + str("{:.2f}".format(imagenes[lista[3]].centro_radiacion_pixeles[0])) + ", " + \
                    str("{:.2f}".format(imagenes[lista[3]].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))

            linea = "Posicion 3D Laser: (" + str("{:.2f}".format(laser.laser3D[1].Pos3D_media[0])) + ", " + str(
                "{:.2f}".format(laser.laser3D[1].Pos3D_media[1])) + \
                    ", ---) pixeles"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Posicion 3D Radiacion: (" + str("{:.2f}".format(radiacion.radiacion3D[1].Pos3D_media[0])) + ", " + \
                    str("{:.2f}".format(radiacion.radiacion3D[1].Pos3D_media[1])) + ", ---) pixeles"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            dif_x = laser.laser3D[1].Pos3D_media[0] - radiacion.radiacion3D[1].Pos3D_media[0]
            dif_y = laser.laser3D[1].Pos3D_media[1] - radiacion.radiacion3D[1].Pos3D_media[1]
            distancia3D_pixeles = np.sqrt(np.power(dif_x, 2) + np.power(dif_y, 2))
            distancia3D_mm = distancia3D_pixeles * imagenes[0].pixelsizemm

            Story.append(Spacer(1, 5))
            linea = "Solo Colimador:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " + str(
                str("{:.2f}".format(distancia3D_mm))) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia Componentes 2D Laser-Radiacion (X, Y, Z): (" + str("{:.2f}".format(dif_x)) + ", " + \
                    str("{:.2f}".format(dif_y)) + ", ---) pixeles, (" + str(
                "{:.2f}".format(dif_x * imagenes[0].pixelsizemm)) + \
                    ", " + str("{:.2f}".format(dif_y * imagenes[0].pixelsizemm)) + ", ---) mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            # Genera Grafica Colimador
            _abcisas = [0, 90, 180, 270]
            _x_dif = []
            _y_dif = []
            lista = [0, 4, 5, 6]
            for i in lista:
                if i != 4:
                    _x_dif.append(
                        float(imagenes[i].centro_circulo_pixeles[0] - imagenes[i].centro_radiacion_pixeles[0]) *
                        imagenes[i].pixelsizemm)
                    _y_dif.append(
                        float(imagenes[i].centro_circulo_pixeles[1] - imagenes[i].centro_radiacion_pixeles[1]) *
                        imagenes[i].pixelsizemm)
                    centro_laser_crucetas_colimador.append(imagenes[i].centro_circulo_pixeles)
                    centro_radiacion_crucetas_colimador.append(imagenes[i].centro_radiacion_pixeles)
                else:
                    if imagenes[lista[1]].matriz_orig is not None:
                        _x_dif.append(
                            float(imagenes[i].centro_circulo_pixeles[0] - imagenes[i].centro_radiacion_pixeles[0]) *
                            imagenes[i].pixelsizemm)
                        _y_dif.append(
                            float(imagenes[i].centro_circulo_pixeles[1] - imagenes[i].centro_radiacion_pixeles[1]) *
                            imagenes[i].pixelsizemm)
                        centro_laser_crucetas_colimador.append(imagenes[i].centro_circulo_pixeles)
                        centro_radiacion_crucetas_colimador.append(imagenes[i].centro_radiacion_pixeles)
                    else:
                        _abcisas = [0, 180, 270]

            plt.subplot(132)
            plt.title("Colimador")
            plt.grid()
            plt.xlabel("º")
            plt.plot(_abcisas, _x_dif, label="X")
            plt.plot(_abcisas, _y_dif, label="Y")
            plt.legend(["X", "Y"])

        if laser.OK_mesa == True and radiacion.OK_mesa == True:
            Story.append(Spacer(1, 25))
            linea = "Mesa:"
            ptext = '<font size="15">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 25))

            lista = [0, 7, 8]
            for i in lista:
                linea = str(imagenes[i].fichero)
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

                im = Image(imagenes[i].imagen_para_informe, 2 * inch, 2 * inch)
                Story.append(im)
                Story.append(Spacer(1, 12))
                Story.append(Spacer(1, 12))

            Story.append(Spacer(1, 5))
            linea = "Laser X, Y, Z:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 5))

            linea = "... 0: (" + str(imagenes[lista[0]].centro_circulo_pixeles[0]) + ", " + str(
                imagenes[lista[0]].centro_circulo_pixeles[1]) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "..90: (" + str(imagenes[lista[1]].centro_circulo_pixeles[0]) + ", " + str(
                imagenes[lista[1]].centro_circulo_pixeles[1]) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".270: (" + str(imagenes[lista[2]].centro_circulo_pixeles[0]) + ", " + str(
                imagenes[lista[2]].centro_circulo_pixeles[1]) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = "Radiacion X, Y, Z:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))
            Story.append(Spacer(1, 5))

            linea = "... 0: (" + str("{:.2f}".format(imagenes[lista[0]].centro_radiacion_pixeles[0])) + ", " + \
                    str("{:.2f}".format(imagenes[lista[0]].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "..90: (" + str("{:.2f}".format(imagenes[lista[1]].centro_radiacion_pixeles[0])) + ", " + \
                    str("{:.2f}".format(imagenes[lista[1]].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = ".270: (" + str("{:.2f}".format(imagenes[lista[2]].centro_radiacion_pixeles[0])) + ", " + \
                    str("{:.2f}".format(imagenes[lista[2]].centro_radiacion_pixeles[1])) + ", ---)"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))

            linea = "Posicion 3D Laser: (" + str("{:.2f}".format(laser.laser3D[2].Pos3D_media[0])) + ", " + \
                    str("{:.2f}".format(laser.laser3D[2].Pos3D_media[1])) + ", ---) pixeles"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Posicion 3D Radiacion: (" + str("{:.2f}".format(radiacion.radiacion3D[2].Pos3D_media[0])) + \
                    ", " + str("{:.2f}".format(radiacion.radiacion3D[2].Pos3D_media[1])) + ", ---) pixeles"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            dif_x = laser.laser3D[2].Pos3D_media[0] - radiacion.radiacion3D[2].Pos3D_media[0]
            dif_y = laser.laser3D[2].Pos3D_media[1] - radiacion.radiacion3D[2].Pos3D_media[1]
            distancia3D_pixeles = np.sqrt(np.power(dif_x, 2) + np.power(dif_y, 2))
            distancia3D_mm = distancia3D_pixeles * imagenes[0].pixelsizemm

            Story.append(Spacer(1, 5))
            linea = "Solo Mesa:"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " + \
                    str("{:.2f}".format(distancia3D_mm)) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia Componentes 2D Laser-Radiacion (X, Y, Z): (" + str("{:.2f}".format(dif_x)) + ", " + \
                    str("{:.2f}".format(dif_y)) + \
                    ", ---) pixeles, (" + str("{:.2f}".format(dif_x * imagenes[0].pixelsizemm)) + ", " + str(
                "{:.2f}".format(dif_y * imagenes[0].pixelsizemm)) + ", ---) mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            # Genera Grafica Mesa
            _abcisas = [0, 90, 270]
            _x_dif = []
            _y_dif = []
            lista = [0, 7, 8]
            for i in lista:
                _x_dif.append(
                    float(imagenes[i].centro_circulo_pixeles[0] - imagenes[i].centro_radiacion_pixeles[0]) * imagenes[
                        0].pixelsizemm)
                _y_dif.append(
                    float(imagenes[i].centro_circulo_pixeles[1] - imagenes[i].centro_radiacion_pixeles[1]) * imagenes[
                        0].pixelsizemm)
                centro_laser_crucetas_mesa.append(imagenes[i].centro_circulo_pixeles)
                centro_radiacion_crucetas_mesa.append(imagenes[i].centro_radiacion_pixeles)

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

        if laser.media_x_total_laser is not None and radiacion.media_x_total_radiacion is not None:
            x = laser.media_x_total_laser - radiacion.media_x_total_radiacion
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

        if laser.media_y_total_laser is not None and radiacion.media_y_total_radiacion is not None:
            y = laser.media_y_total_laser - radiacion.media_y_total_radiacion
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

        if laser.media_z_total_laser is not None and radiacion.media_z_total_radiacion is not None:
            z = laser.media_z_total_laser - radiacion.media_z_total_radiacion
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
            linea = "Laser (X, Y, Z): (" + str("{:.2f}".format(laser.media_x_total_laser)) + ", " + str(
                "{:.2f}".format(laser.media_y_total_laser)) + ", " + str(
                "{:.2f}".format(laser.media_z_total_laser)) + ")"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Radiacion (X, Y, Z): (" + str("{:.2f}".format(radiacion.media_x_total_radiacion)) + ", " + str(
                "{:.2f}".format(radiacion.media_y_total_radiacion)) + ", " + \
                    str("{:.2f}".format(radiacion.media_z_total_radiacion)) + ")"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " + str(
                "{:.2f}".format(distancia3D_pixeles * imagenes[0].pixelsizemm)) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = "Distancia Componentes 2D Laser-Radiacion (X, Y, Z): (" + str("{:.2f}".format(x)) + ", " + str(
                "{:.2f}".format(y)) + ", " + str("{:.2f}".format(z)) + ") pixeles, (" + \
                    str("{:.2f}".format(x * imagenes[0].pixelsizemm)) + ", " + str(
                "{:.2f}".format(y * imagenes[0].pixelsizemm)) + ", " + str(
                "{:.2f}".format(z * imagenes[0].pixelsizemm)) + ") mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            Story.append(Spacer(1, 5))
            linea = cadx + " " + str("{:.2f}".format(abs(x * imagenes[0].pixelsizemm))) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = cady + " " + str("{:.2f}".format(abs(y * imagenes[0].pixelsizemm))) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

            linea = cadz + " " + str("{:.2f}".format(abs(z * imagenes[0].pixelsizemm))) + " mm"
            ptext = '<font size="10">' + linea + '</font>'
            Story.append(Paragraph(ptext, styles["Normal"]))

        else:
            if z is None:
                linea = "Laser (X, Y, ---): (" + str("{:.2f}".format(laser.media_x_total_laser)) + ", " + str(
                    laser.media_y_total_laser) + ", ---)"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

                linea = "Radiacion (X, Y, ---): (" + str(
                    "{:.2f}".format(radiacion.media_x_total_radiacion)) + ", " + str(
                    radiacion.media_y_total_radiacion) + ", ---)"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

                distancia3D_pixeles = np.sqrt(np.power(x, 2) + np.power(y, 2))
                linea = "Distancia 3D Laser-Radiacion: " + str("{:.2f}".format(distancia3D_pixeles)) + " pixeles, " + \
                        str("{:.2f}".format(distancia3D_pixeles * imagenes[0].pixelsizemm)) + " mm"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

                linea = "Distancia Componentes 2D Laser-Radiacion (X, Y, ---): (" + str(
                    "{:.2f}".format(x)) + ", " + str("{:.2f}".format(y)) + \
                        ", ---) pixeles, (" + str("{:.2f}".format(x * imagenes[0].pixelsizemm)) + ", " + str(
                    "{:.2f}".format(y * imagenes[0].pixelsizemm)) + ", ---) mm"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

                linea = cadx + " " + str("{:.2f}".format(abs(x * imagenes[0].pixelsizemm))) + " mm"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

                linea = cady + " " + str("{:.2f}".format(abs(y * imagenes[0].pixelsizemm))) + " mm"
                ptext = '<font size="10">' + linea + '</font>'
                Story.append(Paragraph(ptext, styles["Normal"]))

            else:
                if x is None:
                    linea = "Laser (---, Y, Z): (---, " + str("{:.2f}".format(laser.media_y_total_laser)) + ", " + str(
                        "{:.2f}".format(laser.media_z_total_laser)) + ")"
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

                    linea = "Radiacion (---, Y, Z): (---, " + str(
                        "{:.2f}".format(radiacion.media_y_total_radiacion)) + ", " + str(
                        "{:.2f}".format(radiacion.media_z_total_radiacion)) + ")"
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

                    distancia3D_pixeles = np.sqrt(np.power(y, 2) + np.power(z, 2))
                    linea = "Distancia 3D Laser-Radiacion: " + str(
                        "{:.2f}".format(distancia3D_pixeles)) + " pixeles, " + \
                            str("{:.2f}".format(distancia3D_pixeles * imagenes[0].pixelsizemm)) + " mm"
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

                    linea = "Distancia Componentes 2D Laser-Radiacion (---, Y, Z): (---, " + str(
                        "{:.2f}".format(y)) + ", " + \
                            str("{:.2f}".format(z)) + ") pixeles, (---, " + str(
                        "{:.2f}".format(y * imagenes[0].pixelsizemm)) + ", " + \
                            str("{:.2f}".format(y * imagenes[0].pixelsizemm, z)) + ") mm"
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

                    linea = cady + " " + str("{:.2f}".format(abs(y * imagenes[0].pixelsizemm))) + " mm"
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

                    linea = cadz + " " + str("{:.2f}".format(abs(z * imagenes[0].pixelsizemm))) + " mm"
                    ptext = '<font size="10">' + linea + '</font>'
                    Story.append(Paragraph(ptext, styles["Normal"]))

        # Genera imagenes crucetas
        # Gantry

        if len(centro_laser_crucetas_gantry) != 0:
            _array_g = Dibuja_cruceta_en_array(array, centro_laser_crucetas_gantry, centro_radiacion_crucetas_gantry, 3,
                                               1, (255, 0, 0), (0, 255, 0), False).array3D
            plt.clf()
            f = plt.figure()
            shape = _array_g.shape
            y0 = int(shape[0] / 2) - 20
            y1 = int(shape[0] / 2) + 20
            x0 = int(shape[1] / 2) - 20
            x1 = int(shape[1] / 2) + 20
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

        if len(centro_laser_crucetas_colimador) != 0:
            _array_c = Dibuja_cruceta_en_array(array, centro_laser_crucetas_colimador,
                                               centro_radiacion_crucetas_colimador, 3, 1, (255, 0, 0), (0, 255, 0),
                                               False).array3D
            plt.clf()
            f = plt.figure()
            shape = _array_c.shape
            y0 = int(shape[0] / 2) - 20
            y1 = int(shape[0] / 2) + 20
            x0 = int(shape[1] / 2) - 20
            x1 = int(shape[1] / 2) + 20
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

        if len(centro_laser_crucetas_mesa) != 0:
            _array_m = Dibuja_cruceta_en_array(array, centro_laser_crucetas_mesa, centro_radiacion_crucetas_mesa, 3, 1,
                                               (255, 0, 0), (0, 255, 0), False).array3D
            plt.clf()
            f = plt.figure()
            shape = _array_m.shape
            y0 = int(shape[0] / 2) - 20
            y1 = int(shape[0] / 2) + 20
            x0 = int(shape[1] / 2) - 20
            x1 = int(shape[1] / 2) + 20
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


# Lee de un fichero de texto los nombres de los ficheros de entrada
class Ppal:
    def __init__(self):
        self.argument_file = "Nombres_ficheros_winston_Lutz.txt"
        self.output_path = "./"
        sigma = 2
        low = 5
        high = 30

        # Lee nombres de los ficheros del fichero de argumentos self.argument_file y genera el array de "imagenes"
        # Tambien las analiza y obtiene centro de radiacion y centro de los laseres.
        ra = Read_arguments(self.argument_file, sigma, low, high)

        # Calcula la posicion 3D del laser para gantry, colimador, mesa y todo combinado
        print("Evaluando posicion laseres ...")
        gl = Get_Laser(ra.imagenes)

        # Calcula la posicion 3D del centro de radiacion para gantry, colimador, mesa y todo combinado
        print("Evaluando posicion centro radiacion ...")
        gc = Get_centro_radiacion(ra.imagenes)

        # Evaluacion de resultados
        print("Evaluando de resultados ...")
        ge = Evaluacion(ra.imagenes, gl, gc)

        # Generacion de Informe
        Genera_Informe(self.output_path, ra.imagenes, gl, gc)
