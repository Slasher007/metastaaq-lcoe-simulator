-- Migration: Create spot_prices table for storing electricity spot price data
-- Created: 2026-02-02
-- Description: Table to store hourly electricity spot prices from the French market

-- Create the spot_prices table
CREATE TABLE IF NOT EXISTS public.spot_prices (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
    month VARCHAR(20) NOT NULL,
    day_of_week VARCHAR(20) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    year INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint to prevent duplicate entries for the same date/hour
    CONSTRAINT unique_date_hour UNIQUE (date, hour)
);

-- Create indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_spot_prices_date ON public.spot_prices(date);
CREATE INDEX IF NOT EXISTS idx_spot_prices_year ON public.spot_prices(year);
CREATE INDEX IF NOT EXISTS idx_spot_prices_month ON public.spot_prices(month);
CREATE INDEX IF NOT EXISTS idx_spot_prices_year_month ON public.spot_prices(year, month);
CREATE INDEX IF NOT EXISTS idx_spot_prices_date_range ON public.spot_prices(date DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.spot_prices ENABLE ROW LEVEL SECURITY;

-- Create RLS policies

-- Policy: Allow authenticated users to read all data
CREATE POLICY "authenticated_read_spot_prices" 
    ON public.spot_prices 
    FOR SELECT 
    TO authenticated 
    USING (true);

-- Policy: Allow anonymous users to read all data (for public dashboards)
CREATE POLICY "anon_read_spot_prices" 
    ON public.spot_prices 
    FOR SELECT 
    TO anon 
    USING (true);

-- Policy: Allow service role to perform all operations (for data ingestion)
CREATE POLICY "service_role_full_access_spot_prices" 
    ON public.spot_prices 
    FOR ALL 
    TO service_role 
    USING (true)
    WITH CHECK (true);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_spot_prices_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic updated_at
DROP TRIGGER IF EXISTS trigger_spot_prices_updated_at ON public.spot_prices;
CREATE TRIGGER trigger_spot_prices_updated_at
    BEFORE UPDATE ON public.spot_prices
    FOR EACH ROW
    EXECUTE FUNCTION public.update_spot_prices_updated_at();

-- Add comments for documentation
COMMENT ON TABLE public.spot_prices IS 'Hourly electricity spot prices from the French market';
COMMENT ON COLUMN public.spot_prices.date IS 'Date of the price record (YYYY-MM-DD)';
COMMENT ON COLUMN public.spot_prices.hour IS 'Hour of the day (0-23)';
COMMENT ON COLUMN public.spot_prices.month IS 'Month name in English (e.g., January, February)';
COMMENT ON COLUMN public.spot_prices.day_of_week IS 'Day of week name in English (e.g., Monday, Tuesday)';
COMMENT ON COLUMN public.spot_prices.price IS 'Electricity price in EUR/MWh';
COMMENT ON COLUMN public.spot_prices.year IS 'Year of the price record';
