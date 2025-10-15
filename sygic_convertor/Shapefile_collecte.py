# sygic_convertor/Shapefile_collecte.py
from PyQt5.QtCore import QVariant, QDate
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QDialogButtonBox
)
from qgis.core import QgsField

layer = iface.activeLayer()
if not layer:
    raise Exception("Aucune couche active sélectionnée.")

if not layer.isEditable():
    layer.startEditing()

# Étape 1 : Sélection des champs à supprimer
class FieldRemovalDialog(QDialog):
    def __init__(self, fields):
        super().__init__()
        self.setWindowTitle("Sélection des champs à supprimer")
        self.layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        for field in fields:
            item = QListWidgetItem(field.name())
            self.list_widget.addItem(item)
        self.layout.addWidget(QLabel("Sélectionnez les champs à supprimer :"))
        self.layout.addWidget(self.list_widget)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        self.button_box.accepted.connect(self.accept)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

    def selected_fields(self):
        return [item.text() for item in self.list_widget.selectedItems()]

fields = layer.fields()
dialog = FieldRemovalDialog(fields)
if not dialog.exec_():
    raise Exception("Opération annulée")

fields_to_remove = dialog.selected_fields()
for field_name in fields_to_remove:
    layer.deleteAttribute(layer.fields().indexOf(field_name))
layer.updateFields()

# Ajout des nouveaux champs
new_fields = {
    "date_mesur": QVariant.String,
    "source": QVariant.String,
    "type_oa": QVariant.String,
    "info_comp": QVariant.String,
    "hauteur_d": QVariant.Double,
    "hauteur_g": QVariant.Double, 
    "traiter": QVariant.Bool
}

for name, field_type in new_fields.items():
    layer.addAttribute(QgsField(name, field_type))
layer.updateFields()

# Récupération des index des champs source pour hauteur_d et hauteur_g
idx_hauteur_dr = layer.fields().indexOf("Hauteur Dr")
idx_hauteur_gr = layer.fields().indexOf("Hauteur Ga")
idx_date_mesur = layer.fields().indexOf("date_mesur")
idx_source = layer.fields().indexOf("source")
idx_type_oa = layer.fields().indexOf("type_oa")
idx_info_comp = layer.fields().indexOf("info_comp")
idx_hauteur_d = layer.fields().indexOf("hauteur_d")
idx_hauteur_g = layer.fields().indexOf("hauteur_g")
idx_traiter = layer.fields().indexOf("traiter")

# Mise à jour des entités
today = QDate.currentDate().toString("dd/MM/yyyy")

for feature in layer.getFeatures():
    fid = feature.id()
    updates = {
        idx_date_mesur: today,
        idx_source: "Valentin",
        idx_type_oa: "pont",
        idx_info_comp: "OGP",
        
    }
    updates[idx_traiter] = False
    

    try:
        val_dr = feature[idx_hauteur_dr]
        updates[idx_hauteur_d] = round(float(val_dr) / 100, 2) if val_dr is not None else None
    except:
        updates[idx_hauteur_d] = None

    try:
        val_gr = feature[idx_hauteur_gr]
        updates[idx_hauteur_g] = round(float(val_gr) / 100, 2) if val_gr is not None else None
    except:
        updates[idx_hauteur_g] = None

    layer.changeAttributeValues(fid, updates)

# Suppression des champs "Hauteur Dr" et "Hauteur Gr"
for field_name in ["Hauteur Dr", "Hauteur Ga"]:
    idx = layer.fields().indexOf(field_name)
    if idx != -1:
        layer.deleteAttribute(idx)

layer.updateFields()
layer.commitChanges()
iface.messageBar().pushSuccess("Succès", "La couche a été mise à jour avec les valeurs par défaut et les champs supprimés.")