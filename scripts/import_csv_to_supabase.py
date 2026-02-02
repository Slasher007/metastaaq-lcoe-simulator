"""
Script to import existing CSV spot price data into Supabase

Usage:
    python scripts/import_csv_to_supabase.py [--csv-file PATH]

This script reads the existing spot price CSV file and imports it into the
Supabase database. It uses upsert to avoid duplicate entries.
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv not installed. Using system environment variables.")

import pandas as pd
from supabase_service import get_supabase_service


def main():
    parser = argparse.ArgumentParser(description='Import CSV spot prices into Supabase')
    parser.add_argument(
        '--csv-file', 
        type=str,
        default='donnees_prix_spot_FR_2021_2025_month_12.csv',
        help='Path to the CSV file containing spot price data'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview data without importing'
    )
    
    args = parser.parse_args()
    
    # Check if CSV file exists
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        # Try from project root
        csv_path = Path(__file__).parent.parent / args.csv_file
        
    if not csv_path.exists():
        print(f"❌ CSV file not found: {args.csv_file}")
        sys.exit(1)
    
    print(f"📂 Loading CSV file: {csv_path}")
    
    # Load CSV
    df = pd.read_csv(csv_path)
    print(f"📊 Found {len(df)} records in CSV")
    
    # Handle new CSV format
    if 'DateTime' in df.columns and 'Prix_EUR_MWh' in df.columns:
        print("🔄 Detected new CSV format (DateTime, Prix_EUR_MWh)")
        
        # Convert DateTime to datetime objects
        df['dt'] = pd.to_datetime(df['DateTime'], utc=True)
        # Convert to Paris time (assuming input is UTC or handle offsets correctly)
        # If the input already has offsets (e.g. +01:00), pandas handles it.
        # We want local time for day/hour logic usually, or keep UTC? 
        # The previous data seemed to be local. Let's convert to Europe/Paris to be safe/consistent
        try:
             df['dt'] = df['dt'].dt.tz_convert('Europe/Paris')
        except TypeError:
             df['dt'] = df['dt'].dt.tz_localize('UTC').dt.tz_convert('Europe/Paris')
             
        # Create required columns
        df['Date'] = df['dt'].dt.date
        df['Heure'] = df['dt'].dt.hour
        # Map month number to French name if needed, or keep English/Number. 
        # The schema uses VARCHAR for month. Previous data had 'July'.
        # Let's use English names to be consistent with previous 'July'.
        df['Mois'] = df['dt'].dt.month_name()
        df['Jours'] = df['dt'].dt.day_name()
        df['Prix'] = df['Prix_EUR_MWh']
        df['Annee'] = df['dt'].dt.year
        
    print(f"📅 Date range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"📆 Years: {sorted(df['Annee'].unique())}")
    
    # Preview data
    print("\n📋 Data preview:")
    print(df[['Date', 'Heure', 'Prix']].head(10).to_string())
    print(f"\nColumns: {list(df.columns)}")
    
    if args.dry_run:
        print("\n🔍 Dry run mode - no data imported")
        return
    
    # Get Supabase service with admin privileges (needed for insert)
    service = get_supabase_service(use_service_role=True)
    
    if not service.is_connected:
        print("\n❌ Cannot connect to Supabase. Check your .env configuration:")
        print("   - SUPABASE_URL should be set")
        print("   - SUPABASE_SERVICE_ROLE_KEY should be set")
        sys.exit(1)
    
    # Truncate table before import
    print("\n🧹 Truncating 'spot_prices' table...")
    try:
        service.client.table('spot_prices').delete().neq('id', -1).execute() # Delete all rows
        print("✅ Table truncated successfully")
    except Exception as e:
        print(f"⚠️ Warning: Could not truncate table: {e}")
        # Continue anyway as upsert might handle it, or user might want to add
    
    # Deduplicate data
    print("🧹 Checking for duplicates...")
    initial_count = len(df)
    df = df.drop_duplicates(subset=['Date', 'Heure'])
    final_count = len(df)
    if initial_count > final_count:
        print(f"⚠️ Removed {initial_count - final_count} duplicate records")
    
    # Import data
    print(f"\n🚀 Starting import of {len(df)} records...")
    
    success = service.insert_spot_prices(df)
    
    if success:
        print("\n✅ Import completed successfully!")
        
        # Show stats
        stats = service.get_data_stats()
        print(f"\n📊 Database Statistics:")
        print(f"   Total records: {stats.get('total_records', 'N/A')}")
        print(f"   Date range: {stats.get('min_date', 'N/A')} to {stats.get('max_date', 'N/A')}")
        print(f"   Years: {stats.get('years', [])}")
    else:
        print("\n❌ Import failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
