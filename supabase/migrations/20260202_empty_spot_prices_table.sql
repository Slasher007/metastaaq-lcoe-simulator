-- Migration: Empty spot_prices table (Keep structure)
-- Created: 2026-02-02
-- Description: Removes all records from spot_prices table but keeps the table structure and columns

TRUNCATE TABLE public.spot_prices;
