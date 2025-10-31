from supabase import create_client
from config import settings

# Initialize Supabase client (simple configuration)
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
