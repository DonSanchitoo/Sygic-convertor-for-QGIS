# sygic_convertor/API_ORS_QGIS.py
import csv
import datetime
import json
import os
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree

import polyline
import requests

# -------------------------------
# Clé API
API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjdjMTJiZWMzNmFjNTQ2ODJiZjAzYmZmNGEyNzI5YWNmIiwiaCI6Im11cm11cjY0In0="
API_URL = "https://api.openrouteservice.org/optimization"
HEADERS = {
    "Authorization": API_KEY,
    "Content-Type": "application/json"
}

# Lecture du fichier CSV
def read_csv(csv_path):
    points = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            points.append({
                "id": int(row["id"]),
                "x": float(row["x"]),
                "y": float(row["y"])
            })
    return points

# Construction de la requête JSON
def build_payload(points):
    ids = [p["id"] for p in points]
    start_point = next(p for p in points if p["id"] == 0)
    end_point = next(p for p in points if p["id"] == max(ids))

    jobs = []
    for point in points:
        if point["id"] == 0 or point["id"] == max(ids):
            continue
        job = {
            "id": point["id"],
            "service": 1,
            "delivery": [1],
            "location": [point["x"], point["y"]],
        }
        jobs.append(job)

    vehicle = {
        "id": 1,
        "profile": "driving-car",
        "start": [start_point["x"], start_point["y"]],
        "end": [end_point["x"], end_point["y"]],
        "capacity": [9999],
    }

    payload = {
        "jobs": jobs,
        "vehicles": [vehicle],
        "options": {"g": True}
    }

    return payload

def send_request(payload):
    response = requests.post(API_URL, headers=HEADERS, json=payload)
    if response.status_code != 200:
        print(f"Erreur API : {response.status_code}")
        print(response.text)
        sys.exit(1)
    return response.json()

# Calcul du numéro de semaine et de la date
def get_date_and_week():
    """
    Retourne :
      - la date du jour au format JJMMAAAA
      - le numéro de semaine ISO (français : lundi = premier jour)
        => Semaine_01 à Semaine_52
    """
    today = datetime.date.today()
    date_str = today.strftime("%d%m%Y")
    week_num = today.isocalendar().week
    return date_str, f"Semaine_{week_num:02d}"

# Enregistrement du JSON brut
def save_response(response_data, output_dir):
    date_str, week_str = get_date_and_week()
    output_path = Path(output_dir) / f"Result_API_ORS_{week_str}_{date_str}.json"
    with open(output_path, "w") as f:
        json.dump(response_data, f, indent=2)
    print(f"Réponse enregistrée dans : {output_path}")
    return output_path

# Extraction et conversion GeoJSON
def convert_to_geojson(response_data, output_dir):
    date_str, week_str = get_date_and_week()
    geojson_path = Path(output_dir) / f"GeometryWay_{week_str}_{date_str}.geojson"

    features = []
    routes = response_data.get("routes", [])
    if not routes:
        print("Aucune route trouvée dans la réponse.")
        return None

    for route in routes:
        geometry = route.get("geometry")
        if geometry:
            coords = polyline.decode(geometry)
            geojson_coords = [[lon, lat] for lat, lon in coords]
            feature = {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": geojson_coords},
                "properties": {
                    "vehicle_id": route.get("vehicle"),
                    "distance": route.get("distance"),
                    "duration": route.get("duration")
                }
            }
            features.append(feature)

    geojson_data = {"type": "FeatureCollection", "features": features}
    with open(geojson_path, "w") as f:
        json.dump(geojson_data, f, indent=2)
    print(f"GeoJSON enregistré dans : {geojson_path}")
    return geojson_path

# Conversion GeoJSON → KML
def convert_geojson_to_kml(geojson_path):
    date_str, week_str = get_date_and_week()
    kml_path = geojson_path.parent / f"GeometryWay_{week_str}_{date_str}.kml"

    with open(geojson_path) as f:
        geojson_data = json.load(f)

    kml = Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    document = SubElement(kml, "Document")

    for feature in geojson_data["features"]:
        placemark = SubElement(document, "Placemark")
        SubElement(placemark, "name").text = f"Vehicle {feature['properties'].get('vehicle_id', '')}"
        linestring = SubElement(placemark, "LineString")
        coords = SubElement(linestring, "coordinates")
        coord_text = " ".join([f"{lon},{lat},0" for lon, lat in feature["geometry"]["coordinates"]])
        coords.text = coord_text

    ElementTree(kml).write(kml_path, encoding="utf-8", xml_declaration=True)
    print(f"KML enregistré dans : {kml_path}")
    return kml_path

# Extraction des coordonnées depuis le KML
def extract_coordinates_from_kml(kml_file_path):
    tree = ET.parse(kml_file_path)
    root = tree.getroot()
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    coordinates = root.find('.//kml:LineString/kml:coordinates', ns)
    if coordinates is None:
        raise ValueError("No LineString coordinates found in the KML file.")
    coord_pairs = coordinates.text.strip().split()
    points = []
    for pair in coord_pairs:
        lon, lat = map(float, pair.split(',')[:2])
        points.append({"x": lon * 100000, "y": lat * 100000})
    return points

# Création du JSON final
def convert_kml_to_custom_json(kml_file_path, name_suffix):
    date_str, week_str = get_date_and_week()
    points = extract_coordinates_from_kml(kml_file_path)
    name = f"Trajet_{week_str}_{date_str}_{name_suffix}"
    output_file_path = kml_file_path.parent / f"{name}.json"
    json_data = {
        "polygon": {"lineString": {"points": points}},
        "stations": [
            {"polyIdx": 0, "waypointType": "START"},
            {"polyIdx": len(points)-1, "waypointType": "DEST"}
        ],
        "name": name
    }

    with open(output_file_path, "w") as json_file:
        json.dump(json_data, json_file, separators=(',', ':'))
    print(f"Fichier '{output_file_path.name}' créé avec succès.")
    return output_file_path, name

# Ouvre Outlook + le dossier contenant le fichier
def open_outlook_and_folder(file_path, subject):
    try:
        subject_encoded = urllib.parse.quote(subject)
        subprocess.run(["start", f"mailto:?subject={subject_encoded}"], shell=True)
        print("Outlook ouvert avec le sujet pré-rempli.")
    except Exception as e:
        print(f"Erreur lors de l'ouverture d'Outlook : {e}")

# Création du dossier de sortie
def create_output_folder(name_suffix):
    date_str, week_str = get_date_and_week()
    folder_name = f"trajet_{week_str}_{date_str}_{name_suffix}"
    output_dir = Path(folder_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

# Fonction principale
def main():
    if len(sys.argv) != 3:
        print("Usage: python API_ORS.py <chemin/vers/fichier.csv> <Nom>")
        sys.exit(1)

    csv_path = sys.argv[1]
    name_suffix = sys.argv[2]
    output_dir = Path(csv_path).parent

    points = read_csv(f"{csv_path}")
    payload = build_payload(points)
    response_data = send_request(payload)
    save_response(response_data, output_dir)

    geojson_path = convert_to_geojson(response_data, output_dir)
    if geojson_path:
        kml_path = convert_geojson_to_kml(geojson_path)
        final_json_path, name = convert_kml_to_custom_json(kml_path, name_suffix)

        # --- ICI : ouverture dans QGIS avec style ---
        try:
            from qgis.core import QgsVectorLayer, QgsProject

            if geojson_path and geojson_path.exists():
                layer = QgsVectorLayer(str(geojson_path), "Trajet_ORS", "ogr")
                if not layer.isValid():
                    print("La couche GeoJSON n’a pas pu être chargée.")
                else:
                    style_path = Path(__file__).parent / "OGP_trajet_vrai.qml"
                    if style_path.exists():
                        layer.loadNamedStyle(str(style_path))
                        layer.triggerRepaint()
                        print(f"Style appliqué : {style_path.name}")
                    else:
                        print(f"Style QML introuvable : {style_path}")

                    QgsProject.instance().addMapLayer(layer)
                    print("Couche ajoutée dans QGIS.")
            else:
                print("Aucun GeoJSON à charger dans QGIS.")
        except Exception as e:
            print(f"Erreur lors du chargement dans QGIS : {e}")

        # --- Ouverture du dossier ---
        try:
            os.startfile(output_dir)
            print(f"Dossier ouvert : {output_dir}")
        except Exception as e:
            print(f"Impossible d’ouvrir le dossier : {e}")


def main_from_qgis(csv_path, name_suffix):
    points = read_csv(csv_path)
    payload = build_payload(points)
    response_data = send_request(payload)

    output_dir = Path(csv_path).parent
    save_response(response_data, output_dir)
    geojson_path = convert_to_geojson(response_data, output_dir)

    if geojson_path:
        kml_path = convert_geojson_to_kml(geojson_path)
        final_json_path, name = convert_kml_to_custom_json(kml_path, name_suffix)

        # --- Charger le GeoJSON et appliquer le style dans QGIS ---
        from qgis.core import QgsVectorLayer, QgsProject
        style_path = Path(__file__).parent / "OGP_trajet_vrai.qml"

        layer = QgsVectorLayer(str(geojson_path), "Trajet_ORS", "ogr")
        if layer.isValid():
            if style_path.exists():
                layer.loadNamedStyle(str(style_path))
            QgsProject.instance().addMapLayer(layer)
            print("Couche ajoutée dans QGIS avec style.")
        else:
            print("La couche GeoJSON n’a pas pu être chargée.")
        try:
            os.startfile(output_dir)
            print(f"Dossier ouvert : {output_dir}")
        except Exception as e:
            print(f"Impossible d’ouvrir le dossier : {e}")

if __name__ == "__main__":
    main()


