# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SygicConvertorDialog
 Fenêtre du plugin Mattew Sygic Convertor for QGIS
***************************************************************************/
"""

import os
import runpy

from PyQt5.QtGui import QDesktopServices
from qgis.PyQt import QtWidgets, QtGui, QtCore
from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QLabel, QMessageBox, QMenuBar, QAction
)
from qgis.utils import iface


class SygicConvertorDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Mattew Sygic Convertor for QGIS")
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QMenuBar {
                background-color: #e9ecef;
                border: none;
                padding: 4px;
            }
            QMenuBar::item {
                padding: 4px 12px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background: #0078D7;
                color: white;
                border-radius: 4px;
            }
            QPushButton {
                font-weight: bold;
                font-size: 15px;
                border-radius: 6px;
                padding: 10px;
            }
            QPushButton#btn_run {
                background-color: #0078D7;
                color: white;
            }
            QPushButton#btn_run:hover {
                background-color: #005fa3;
            }
            QPushButton#btn_run:pressed {
                background-color: #004f8c;
            }
            QPushButton#btn_cancel {
                background-color: #d9534f;
                color: white;
            }
            QPushButton#btn_cancel:hover {
                background-color: #c9302c;
            }
        """)

        # === Layout principal ===
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)

        # === Barre de menus ===
        menubar = QtWidgets.QMenuBar()

        # --- Chemins des icônes ---
        plugin_dir = os.path.dirname(__file__)
        icon_prep = QtGui.QIcon(os.path.join(plugin_dir, "logo1.png"))
        icon_help = QtGui.QIcon(os.path.join(plugin_dir, "logo2.png"))
        icon_about = QtGui.QIcon(os.path.join(plugin_dir, "logo3.png"))

        # --- Menus principaux ---
        outils_menu = menubar.addMenu("Outils OGP")
        aide_menu = menubar.addMenu("Aide")
        apropos_menu = menubar.addMenu("À propos")

        # --- Sous-menus avec icônes ---
        prep_action = QtWidgets.QAction(icon_prep, "Préparation shape", self)
        prep_action.triggered.connect(self.run_preparation_shape)
        outils_menu.addAction(prep_action)

        action_aide = QtWidgets.QAction(icon_help, "Afficher l’aide (pdf)", self)
        action_aide.triggered.connect(self.show_help)
        aide_menu.addAction(action_aide)

        action_apropos = QtWidgets.QAction(icon_about, "À propos du plugin", self)
        action_apropos.triggered.connect(self.show_about)
        apropos_menu.addAction(action_apropos)

        # --- Ajout de la barre au layout ---
        main_layout.setMenuBar(menubar)

        # === Logo ===
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        logo_label = QtWidgets.QLabel()
        logo_label.setAlignment(QtCore.Qt.AlignCenter)

        if os.path.exists(logo_path):
            pixmap = QtGui.QPixmap(logo_path)
            # Agrandi un peu : largeur max 300 px
            logo_label.setPixmap(pixmap.scaledToWidth(350, QtCore.Qt.SmoothTransformation))
        else:
            logo_label.setText("Logo non trouvé : logo.png")

        main_layout.addWidget(logo_label)
        main_layout.addSpacing(30)

        # === Bouton Run ===
        self.btn_run = QtWidgets.QPushButton("Run Mattew Sygic Convertor for QGIS")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.setFixedHeight(45)
        main_layout.addWidget(self.btn_run, alignment=QtCore.Qt.AlignCenter)

        # === Bouton Annuler ===
        self.btn_cancel = QtWidgets.QPushButton("Annuler")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.setFixedHeight(35)
        main_layout.addWidget(self.btn_cancel, alignment=QtCore.Qt.AlignCenter)

        # === Connexions ===
        self.btn_run.clicked.connect(self.launch_convertor)
        self.btn_cancel.clicked.connect(self.reject)

        self.setLayout(main_layout)

    # === Méthode : exécution du script principal ===
    def launch_convertor(self):
        from qgis.PyQt.QtWidgets import QMessageBox

        script_path = os.path.join(os.path.dirname(__file__), "Shape_csv_avant_sygic.py")

        if not os.path.exists(script_path):
            QMessageBox.critical(self, "Erreur", f"Script introuvable : {script_path}")
            return

        # Désactiver le bouton pour éviter double clic
        self.btn_run.setEnabled(False)
        self.btn_run.setText("Exécution en cours...")

        QtWidgets.QApplication.processEvents()

        try:
            runpy.run_path(script_path, run_name="__main__")
            QMessageBox.information(self, "Succès", "Le convertisseur a été exécuté avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur d’exécution", str(e))
        finally:
            self.btn_run.setEnabled(True)
            self.btn_run.setText("Run Mattew Sygic Convertor for QGIS")

    def run_preparation_shape(self):
        """Lancer le script Shapefile_collecte.py"""
        from qgis.utils import iface  # Import ici

        script_path = os.path.join(os.path.dirname(__file__), "Shapefile_collecte.py")

        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.critical(self, "Erreur", f"Script introuvable : {script_path}")
            return

        try:
            # Fournir iface dans le namespace d’exécution
            runpy.run_path(script_path, run_name="__main__", init_globals={"iface": iface})
            QtWidgets.QMessageBox.information(self, "Succès",
                                              "Le script 'Préparation shape' a été exécuté avec succès.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erreur d'exécution", str(e))

    # === Méthode : afficher Aide ===
    def show_help(self):
        pdf_path = os.path.join(os.path.dirname(__file__), "aide.pdf")

        if not os.path.exists(pdf_path):
            QtWidgets.QMessageBox.warning(self, "Aide non trouvée", f"Le fichier d’aide est introuvable :\n{pdf_path}")
            return

        # Ouvrir le PDF avec le lecteur par défaut du système
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(pdf_path))

    # === Méthode : afficher À propos ===
    def show_about(self):
        QtWidgets.QMessageBox.information(
            self,
            "À propos",
            "<b>Mattew Sygic Convertor for QGIS</b><br>"
            "Version : 1.0.0<br>"
            "Auteur : <b>Matteo Sanchez / E-SI</b><br>"
            "Email : <i>matteo.sanchez@e-si.fr</i><br><br>"
            "Ce plugin génère un itinéraire optimisé pour Sygic Navigation à partir d'une couche de points QGIS."
        )
