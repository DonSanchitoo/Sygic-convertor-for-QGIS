# sygic_convertor/Shape_csv_avant_sygic.py
import importlib.util
import os

from PyQt5.QtWidgets import QInputDialog, QMessageBox
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsVectorFileWriter,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsWkbTypes
)
from qgis.utils import iface

# Étape 1 : Sélection de la couche point
layer = iface.activeLayer()
if not layer or layer.geometryType() != QgsWkbTypes.PointGeometry:
    raise Exception("Veuillez sélectionner une couche de points active.")

# Nouvelle contrainte : max 50 entités
if layer.featureCount() > 50:
    raise Exception("La couche ne doit pas contenir plus de 50 points.")

# Étape 2 : Reprojection en EPSG:4326
crs_dest = QgsCoordinateReferenceSystem("EPSG:4326")
transform_context = QgsProject.instance().transformContext()
reprojected_layer = QgsVectorLayer("Point?crs=EPSG:4326", "reproj_points", "memory")
reprojected_layer.startEditing()
for feat in layer.getFeatures():
    geom = feat.geometry()
    geom.transform(QgsCoordinateTransform(layer.crs(), crs_dest, transform_context))
    f = QgsFeature()
    f.setGeometry(geom)
    reprojected_layer.addFeature(f)
reprojected_layer.commitChanges()

# Étape 3 : Supprimer tous les champs et créer id, x, y
reprojected_layer.startEditing()
for field in reprojected_layer.fields():
    reprojected_layer.deleteAttribute(reprojected_layer.fields().indexFromName(field.name()))
reprojected_layer.addAttribute(QgsField("id", QVariant.Int))
reprojected_layer.addAttribute(QgsField("x", QVariant.Double))
reprojected_layer.addAttribute(QgsField("y", QVariant.Double))
reprojected_layer.commitChanges()

# Étape 4 : Afficher la liste des points avec index et coordonnées
feat_list = list(reprojected_layer.getFeatures())
print("Liste des points disponibles :")
for f in feat_list:
    p = f.geometry().asPoint()
    print(f"Index interne: {f.id()}, Coordonnées: ({p.x():.6f}, {p.y():.6f})")

# Étape 5 : Demander ID=0 et ID=max
def ask_for_point(prompt):
    ids = [f.id() for f in feat_list]
    id_str_list = [str(fid) for fid in ids]
    id_selected, ok = QInputDialog.getItem(None, "Sélection du point", prompt, id_str_list, 0, False)
    if ok:
        return int(id_selected)
    else:
        raise Exception("Sélection annulée par l'utilisateur")

id0_idx = ask_for_point("Choisissez l'index du point pour ID=0")
idmax_idx = ask_for_point("Choisissez l'index du point pour ID=max")

# Étape 6 : Assigner les IDs et remplir x, y
reprojected_layer.startEditing()
n = len(feat_list)
current_id = 1
for feat in feat_list:
    geom = feat.geometry().asPoint()
    feat['x'] = geom.x()
    feat['y'] = geom.y()
    if feat.id() == id0_idx:
        feat['id'] = 0
    elif feat.id() == idmax_idx:
        feat['id'] = n - 1
    else:
        feat['id'] = -1
    reprojected_layer.updateFeature(feat)

# Remplir les IDs intermédiaires
for feat in reprojected_layer.getFeatures():
    if feat['id'] == -1:
        feat['id'] = current_id
        current_id += 1
        reprojected_layer.updateFeature(feat)

reprojected_layer.commitChanges()

# Étape 7 : Export CSV
path = layer.source()
folder = os.path.dirname(path)
csv_path = os.path.join(folder, os.path.splitext(os.path.basename(path))[0] + "_points.csv")

options = QgsVectorFileWriter.SaveVectorOptions()
options.driverName = "CSV"
options.fileEncoding = "UTF-8"

QgsVectorFileWriter.writeAsVectorFormatV2(reprojected_layer, csv_path, QgsProject.instance().transformContext(), options)
print(f"CSV créé : {csv_path}")


# -------------------------------
# Étape 8 : Demander le suffix_name à l'utilisateur
suffix_name, ok = QInputDialog.getText(None, "Nom du trajet", "Entrez le suffixe à utiliser :")
if not (ok and suffix_name.strip()):
    raise Exception("Opération annulée : aucun suffixe fourni.")
suffix_name = suffix_name.strip()

# Étape 9 : Créer un dossier de sortie propre et lancer API_ORS_QGIS.py
from datetime import date
week_num = date.today().isocalendar().week
today_str = date.today().strftime("%d%m%Y")
output_dir = os.path.join(os.path.dirname(layer.source()), f"trajet_Semaine_{week_num:02d}_{today_str}_{suffix_name}")
os.makedirs(output_dir, exist_ok=True)

csv_path_new = os.path.join(output_dir, os.path.basename(csv_path))
os.replace(csv_path, csv_path_new)

# Étape 10 : Exécution du script API_ORS_QGIS.py dans le même processus QGIS
plugin_dir = os.path.dirname(__file__)
api_script_path = os.path.join(plugin_dir, "API_ORS_QGIS.py")

if not os.path.exists(api_script_path):
    raise FileNotFoundError(f"Script non trouvé : {api_script_path}")

spec = importlib.util.spec_from_file_location("api_ors", api_script_path)
api_ors = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_ors)

try:
    api_ors.main_from_qgis(csv_path_new, suffix_name)
    QMessageBox.information(None, "Succès", f"Trajet généré avec succès et ajouté à QGIS.\n\nDossier : {output_dir}")
except Exception as e:
    QMessageBox.critical(None, "Erreur", f"Erreur pendant l'exécution de API_ORS_QGIS.py :\n{e}")

