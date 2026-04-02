import logging
import asyncpg
import os
from urllib.parse import urlparse, unquote, quote

logger = logging.getLogger(__name__)
pool = None

def fix_database_url(url):
    if not url:
        return url
    parsed = urlparse(url)
    password = unquote(parsed.password or '')
    host = parsed.hostname
    port = parsed.port or 5432
    if host and 'db.' in host and '.supabase.co' in host:
        project_ref = host.replace('db.', '').replace('.supabase.co', '')
        pooler_host = 'aws-0-ap-northeast-1.pooler.supabase.com'
        port = 6543
        user = f'postgres.{project_ref}'
        encoded_pw = quote(password, safe='')
        new_url = f'postgresql://{user}:{encoded_pw}@{pooler_host}:{port}/{parsed.path.lstrip("/")}'
        logger.info(f'Converted to pooler URL: {pooler_host}:{port}')
        return new_url
    encoded_pw = quote(password, safe='')
    user = parsed.username or 'postgres'
    db_name = parsed.path.lstrip('/') or 'postgres'
    return f'postgresql://{user}:{encoded_pw}@{host}:{port}/{db_name}'