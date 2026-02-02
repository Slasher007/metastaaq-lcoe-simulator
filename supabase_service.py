"""
Supabase Service Module for MetaSTAAQ Dashboard
Handles database operations for spot price data
"""

import os
import pandas as pd
from typing import Optional, List
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️ Supabase module not installed. Run: pip install supabase")


class SupabaseService:
    """Service class for Supabase database operations"""
    
    def __init__(self, use_service_role: bool = False):
        """
        Initialize Supabase client from environment variables
        
        Args:
            use_service_role: If True, use SUPABASE_SERVICE_ROLE_KEY instead of ANON_KEY
        """
        self.client: Optional[Client] = None
        self.is_connected = False
        
        if not SUPABASE_AVAILABLE:
            print("⚠️ Supabase library not available")
            return
            
        supabase_url = os.getenv('SUPABASE_URL')
        
        if use_service_role:
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            key_name = "SUPABASE_SERVICE_ROLE_KEY"
        else:
            supabase_key = os.getenv('SUPABASE_ANON_KEY')
            key_name = "SUPABASE_ANON_KEY"
        
        if not supabase_url or not supabase_key:
            print("⚠️ Supabase credentials not found in environment variables")
            print(f"   Set SUPABASE_URL and {key_name} in your .env file")
            return
            
        try:
            self.client = create_client(supabase_url, supabase_key)
            self.is_connected = True
            role_msg = " (Service Role)" if use_service_role else ""
            print(f"✅ Connected to Supabase{role_msg}")
        except Exception as e:
            print(f"❌ Failed to connect to Supabase: {e}")
            self.is_connected = False
    
    def load_spot_prices(
        self, 
        years: Optional[List[int]] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Load spot price data from Supabase
        
        Args:
            years: Optional list of years to filter by
            limit: Optional limit on number of records
            
        Returns:
            DataFrame with spot price data matching CSV format:
            - Date, Heure, Mois, Jours, Prix, Annee
        """
        if not self.is_connected or not self.client:
            raise ConnectionError("Not connected to Supabase")
        
        try:
            # Build query
            query = self.client.table('spot_prices').select('*')
            
            # Add year filter if specified
            if years:
                query = query.in_('year', years)
            
            # Order by date and hour
            query = query.order('date', desc=False).order('hour', desc=False)
            
            # Add limit if specified
            if limit:
                query = query.limit(limit)
            
            # Execute query
            response = query.execute()
            
            if not response.data:
                return pd.DataFrame(columns=['Date', 'Heure', 'Mois', 'Jours', 'Prix', 'Annee'])
            
            # Convert to DataFrame
            df = pd.DataFrame(response.data)
            
            # Rename columns to match existing CSV format
            column_mapping = {
                'date': 'Date',
                'hour': 'Heure',
                'month': 'Mois',
                'day_of_week': 'Jours',
                'price': 'Prix',
                'year': 'Annee'
            }
            df = df.rename(columns=column_mapping)
            
            # Select only the columns matching CSV format
            csv_columns = ['Date', 'Heure', 'Mois', 'Jours', 'Prix', 'Annee']
            df = df[[col for col in csv_columns if col in df.columns]]
            
            print(f"✅ Loaded {len(df)} spot price records from Supabase")
            return df
            
        except Exception as e:
            print(f"❌ Error loading spot prices from Supabase: {e}")
            raise
    
    def insert_spot_prices(self, df: pd.DataFrame) -> bool:
        """
        Insert spot price data into Supabase
        
        Args:
            df: DataFrame with columns matching CSV format:
                Date, Heure, Mois, Jours, Prix, Annee
                
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected or not self.client:
            raise ConnectionError("Not connected to Supabase")
        
        try:
            # Map DataFrame columns to database columns
            column_mapping = {
                'Date': 'date',
                'Heure': 'hour',
                'Mois': 'month',
                'Jours': 'day_of_week',
                'Prix': 'price',
                'Annee': 'year'
            }
            
            # Filter to include only columns we want to insert
            columns_to_keep = [col for col in column_mapping.keys() if col in df.columns]
            df_cleaned = df[columns_to_keep].copy()
            
            # Prepare data for insertion
            db_df = df_cleaned.rename(columns=column_mapping)
            
            # Ensure dates are strings to avoid serialization issues
            if 'date' in db_df.columns:
                db_df['date'] = db_df['date'].astype(str)
            
            # Convert to list of dictionaries
            records = db_df.to_dict('records')
            
            # Insert in batches (Supabase has limits on batch size)
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                # Use upsert to handle duplicates
                response = self.client.table('spot_prices').upsert(
                    batch,
                    on_conflict='date,hour'
                ).execute()
                
                total_inserted += len(batch)
                print(f"📤 Inserted batch {i//batch_size + 1}: {len(batch)} records")
            
            print(f"✅ Successfully inserted/updated {total_inserted} records")
            return True
            
        except Exception as e:
            print(f"❌ Error inserting spot prices: {e}")
            return False
    
    def get_available_years(self) -> List[int]:
        """
        Get list of available years in the database
        
        Returns:
            List of years with data
        """
        if not self.is_connected or not self.client:
            return []
        
        try:
            response = self.client.table('spot_prices').select('year').execute()
            
            if response.data:
                years = sorted(set(record['year'] for record in response.data))
                return years
            return []
            
        except Exception as e:
            print(f"❌ Error fetching available years: {e}")
            return []
    
    def get_data_stats(self) -> dict:
        """
        Get statistics about the spot price data
        
        Returns:
            Dictionary with data statistics
        """
        if not self.is_connected or not self.client:
            return {}
        
        try:
            # Get count
            count_response = self.client.table('spot_prices').select('*', count='exact').execute()
            
            # Get min/max dates
            min_date_response = self.client.table('spot_prices').select('date').order('date').limit(1).execute()
            max_date_response = self.client.table('spot_prices').select('date').order('date', desc=True).limit(1).execute()
            
            # Get available years
            years = self.get_available_years()
            
            return {
                'total_records': count_response.count if hasattr(count_response, 'count') else len(count_response.data),
                'min_date': min_date_response.data[0]['date'] if min_date_response.data else None,
                'max_date': max_date_response.data[0]['date'] if max_date_response.data else None,
                'years': years
            }
            
        except Exception as e:
            print(f"❌ Error fetching data stats: {e}")
            return {}


# Singleton instance
_supabase_service: Optional[SupabaseService] = None


def get_supabase_service(use_service_role: bool = False) -> SupabaseService:
    """
    Get or create Supabase service singleton
    
    Args:
        use_service_role: If True, initialize with service role key (only works on first init)
    """
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService(use_service_role=use_service_role)
    return _supabase_service


def load_spot_data_from_supabase(years: Optional[List[int]] = None) -> pd.DataFrame:
    """
    Convenience function to load spot data from Supabase
    Falls back to CSV if Supabase is not available
    
    Args:
        years: Optional list of years to filter
        
    Returns:
        DataFrame with spot price data
    """
    service = get_supabase_service()
    
    if service.is_connected:
        try:
            return service.load_spot_prices(years=years)
        except Exception as e:
            print(f"⚠️ Failed to load from Supabase: {e}")
            print("⚠️ Falling back to CSV file")
    
    # Fallback to CSV
    from config import DEFAULT_DATA_FILE
    print(f"📁 Loading data from CSV: {DEFAULT_DATA_FILE}")
    return pd.read_csv(DEFAULT_DATA_FILE)
