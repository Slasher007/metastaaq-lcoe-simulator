# Supabase Integration for MetaSTAAQ

This document explains how to set up and use Supabase to store spot price data for the MetaSTAAQ dashboard.

## Prerequisites

1. A Supabase account (free tier available at [supabase.com](https://supabase.com))
2. Python packages: `supabase` and `python-dotenv`

## Quick Start

### 1. Install Dependencies

```bash
pip install supabase python-dotenv
```

Or update all requirements:

```bash
pip install -r requirements.txt
```

### 2. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click "New Project"
3. Choose an organization and name your project
4. Wait for the project to be created (1-2 minutes)

### 3. Run the Migration

1. In your Supabase dashboard, go to **SQL Editor**
2. Click "New query"
3. Copy the contents of `supabase/migrations/20260202_create_spot_prices_table.sql`
4. Paste into the SQL editor
5. Click "Run" to execute the migration

This creates the `spot_prices` table with:
- Columns: `id`, `date`, `hour`, `month`, `day_of_week`, `price`, `year`, `created_at`, `updated_at`
- Indexes for optimized querying
- Row Level Security (RLS) policies for secure access

### 4. Configure Environment Variables

1. In Supabase, go to **Settings > API**
2. Copy your **Project URL** and **anon/public key**
3. Create a `.env` file in the project root:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
```

> ⚠️ Never commit your `.env` file to version control!

### 5. Import Existing CSV Data

If you have existing spot price data in CSV format, import it to Supabase:

```bash
# Preview the import (dry run)
python scripts/import_csv_to_supabase.py --dry-run

# Run the actual import
python scripts/import_csv_to_supabase.py
```

By default, this imports from `data/donnees_prix_spot_processed_2020_2025.csv`. To use a different file:

```bash
python scripts/import_csv_to_supabase.py --csv-file path/to/your/file.csv
```

## RLS Policies

Row Level Security is enabled with the following policies:

| Policy Name | Role | Operation | Description |
|------------|------|-----------|-------------|
| `authenticated_read_spot_prices` | authenticated | SELECT | Logged-in users can read all data |
| `anon_read_spot_prices` | anon | SELECT | Anonymous users can read all data (for public dashboards) |
| `service_role_full_access_spot_prices` | service_role | ALL | Full access for data ingestion scripts |

## Usage in Dashboard

The dashboard automatically tries to load data from Supabase. If unsuccessful, it falls back to the CSV file.

### How it works:

1. On startup, the dashboard checks for Supabase credentials in environment variables
2. If connected, data is loaded from the `spot_prices` table
3. If Supabase is unavailable or empty, the CSV fallback is used
4. A status message in the sidebar indicates the data source

### Manual CSV Mode

To force CSV-only mode (skip Supabase):

```python
# In your code
data_content = load_data_file(DEFAULT_DATA_FILE, use_supabase=False)
```

## Database Schema

```sql
spot_prices (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    hour INTEGER NOT NULL (0-23),
    month VARCHAR(20) NOT NULL,
    day_of_week VARCHAR(20) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    year INTEGER NOT NULL,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    UNIQUE(date, hour)
)
```

### Indexes

- `idx_spot_prices_date` - For date filtering
- `idx_spot_prices_year` - For year filtering
- `idx_spot_prices_month` - For month filtering
- `idx_spot_prices_year_month` - For combined year/month queries
- `idx_spot_prices_date_range` - For date range queries (descending)

## Troubleshooting

### Connection Errors

1. Verify your `.env` file exists and contains valid credentials
2. Check that `SUPABASE_URL` includes `https://`
3. Ensure RLS policies are correctly applied

### Data Import Fails

1. Check that the CSV format matches expected columns: `Date, Heure, Mois, Jours, Prix, Annee`
2. Verify the migration was run successfully
3. Check Supabase dashboard logs for errors

### Missing Data

1. Run the import script to populate the database
2. Check the data stats: `python -c "from supabase_service import get_supabase_service; print(get_supabase_service().get_data_stats())"`

## API Reference

### SupabaseService Class

```python
from supabase_service import get_supabase_service

service = get_supabase_service()

# Load spot prices
df = service.load_spot_prices(years=[2024, 2025])

# Insert new data
service.insert_spot_prices(df)

# Get available years
years = service.get_available_years()

# Get data statistics
stats = service.get_data_stats()
```

### Convenience Function

```python
from supabase_service import load_spot_data_from_supabase

# Load all data
df = load_spot_data_from_supabase()

# Load specific years
df = load_spot_data_from_supabase(years=[2024, 2025])
```
