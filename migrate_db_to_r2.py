"""
DRS v3 Migration Utility: Move files from D1 database fallback to Cloudflare R2 bucket.
Run this script AFTER adding your R2 credentials to the .env file.
"""

import os
import asyncio
from core.utils.db import execute_query
from core.utils import r2

async def migrate():
    # Verify R2 is configured
    if not r2.is_cloud_mode():
        print("Error: R2 credentials are not fully configured in your .env file.")
        print("Please configure CF_R2_ACCOUNT_ID, CF_R2_ACCESS_KEY_ID, CF_R2_SECRET_ACCESS_KEY, and CF_R2_BUCKET first.")
        return

    print("Fetching files from database fallback...")
    
    # Query D1/SQLite for all emulated files
    rows = await execute_query("SELECT key, content_text, content_blob, mime_type FROM r2_emulated_files")
    
    if not rows:
        print("No files found in the database fallback table to migrate.")
        return

    print(f"Found {len(rows)} files. Starting migration to Cloudflare R2...")

    # We will temporarily bypass is_cloud_mode detection in the write calls
    # by using the boto3 client directly to write to R2
    s3 = r2._get_s3_client()
    bucket = r2.CF_R2_BUCKET

    success_count = 0
    for row in rows:
        key = row["key"]
        mime = row["mime_type"] or "application/octet-stream"
        
        print(f"Migrating: {key} ({mime})...")
        try:
            if row["content_text"] is not None:
                body = row["content_text"].encode("utf-8")
            else:
                body = row["content_blob"]
                
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType=mime
            )
            success_count += 1
            print(f"✓ Successfully migrated: {key}")
        except Exception as e:
            print(f"✗ Failed to migrate {key}: {e}")

    print(f"\nMigration complete: Successfully copied {success_count}/{len(rows)} files to Cloudflare R2!")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(migrate())
