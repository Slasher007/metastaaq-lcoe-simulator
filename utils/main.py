#!/usr/bin/env python3
"""
Script principal pour MetaSTAAQ - Téléchargement et traitement des données
Télécharge les données PVGIS et ENTSO-E sur 5 ans et les traite
"""

import os
import sys
from datetime import datetime

# Import des modules locaux
try:
    from utils.spot_price_download import download_spot_price_data
    from utils.spot_price_data_processing import process_prix_spot
    
    def update_config_with_latest_file(new_filename):
        """Update config.py with the newest processed file name"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            with open(config_path, 'w', encoding='utf-8') as f:
                for line in lines:
                    if 'DEFAULT_DATA_FILE =' in line:
                        f.write(f"DEFAULT_DATA_FILE = '{new_filename}'\n")
                    else:
                        f.write(line)
            print(f"📝 config.py mis à jour avec: {new_filename}")
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour de config.py: {e}")

except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    sys.exit(1)


    


if __name__ == "__main__":

    # Coordonnées de Meaux (77)
    LATITUDE_MEAUX = 48.96
    LONGITUDE_MEAUX = 2.88
    #print(f"📍 Localisation: Meaux (Lat: {LATITUDE_MEAUX}, Lon: {LONGITUDE_MEAUX})")
    
    # Téléchargement des données de prix spot
    api_key = os.getenv('ENTSOE_API_TOKEN', "9d9b8840-56e2-4993-9385-47cfe2b8183f")
    annee_debut = 2021
    annee_fin = 2025
    mois_fin = 12
    pays_code = 'FR'
    
    print(f"🚀 Démarrage du téléchargement des prix spot ({annee_debut}-{annee_fin})...")
    fichier_prix = download_spot_price_data(api_key, annee_debut, annee_fin, mois_fin, pays_code)
    
    if fichier_prix:
        print(f"✅ Données téléchargées dans: {fichier_prix}")
        print("🔄 Lancement du traitement des données...")
        processed_file = process_prix_spot(fichier_prix)
        
        if processed_file:
            update_config_with_latest_file(processed_file)
            print(f"✅ Configuration mise à jour. Redémarrez le dashboard si nécessaire.")
    else:
        print("❌ Échec du téléchargement des données de prix spot.")
