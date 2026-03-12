-- Add vc_impression column to public_reports table
-- This stores the VC First Impression Simulator data (slide-level rejection signals)
ALTER TABLE public_reports ADD COLUMN IF NOT EXISTS vc_impression JSONB DEFAULT '[]'::jsonb;
