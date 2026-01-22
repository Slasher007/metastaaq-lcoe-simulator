from entsoe import EntsoePandasClient
import pandas as pd
from datetime import datetime
import os

def download_spot_price_data(api_key, annee_debut=2021, annee_fin=2025, mois_fin=9, pays_code='FR'):
    """
    Télécharge les données historiques des prix spot de l'électricité pour analyse détaillée
    des puissances disponibles par tranche horaire (2021-2025).
    
    Args:
        api_key: Clé API ENTSO-E
        annee_debut: Année de début (défaut: 2021)
        annee_fin: Année de fin (défaut: 2025)
        mois_fin: Mois de fin pour la dernière année
        pays_code: Code pays (défaut: 'FR')
    
    Returns:
        str: Nom du fichier CSV généré avec les analyses détaillées
    """
    print(f"🔍 TÉLÉCHARGEMENT DÉTAILLÉ DES PRIX SPOT HISTORIQUES")
    print(f"📅 Période: {annee_debut} - {mois_fin:02d}/{annee_fin}")
    print("="*60)
    
    if not api_key or api_key == "VOTRE_CLE_API_ENTSOE_ICI":
        print("❌ Erreur : Clé API ENTSO-E non configurée.")
        print("📋 Instructions : https://transparencyplatform.zendesk.com/hc/en-us/articles/12845911031188-How-to-get-security-token")
        return None
    
    try:
        client = EntsoePandasClient(api_key=api_key)
        
        # Définir les dates précises
        start_date = datetime(annee_debut, 1, 1)
        
        import calendar
        last_day = calendar.monthrange(annee_fin, mois_fin)[1]
        end_date = datetime(annee_fin, mois_fin, last_day)
        
        print(f"📅 Période exacte: {start_date.strftime('%Y-%m-%d')} à {end_date.strftime('%Y-%m-%d')}")
        
        # Conversion au format ENTSO-E
        start_ts = pd.Timestamp(start_date, tz='Europe/Brussels')
        end_ts = pd.Timestamp(end_date, tz='Europe/Brussels')
        
        print("🔄 Téléchargement des prix spot depuis ENTSO-E...")
        prices = client.query_day_ahead_prices(pays_code, start=start_ts, end=end_ts)
        
        # Créer le DataFrame principal
        df = pd.DataFrame(prices, columns=['Prix_EUR_MWh'])
        df.index.name = 'DateTime'
        
        print(f"✅ {len(df):,} points de données téléchargés")
       
        
        # Sauvegarder le fichier enrichi
        nom_fichier = f'donnees_prix_spot_{pays_code}_{annee_debut}_{annee_fin}_month_{mois_fin}.csv'
        df.to_csv(nom_fichier)
        
        
        return nom_fichier
        
    except Exception as e:
        print(f"❌ Erreur lors du téléchargement: {e}")
        import traceback
        traceback.print_exc()
        return None
