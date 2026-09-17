"""
One-time backfill: syncs cast/crew for every content item currently in the
database that doesn't have it yet (most items, since only a small test batch
got credits during Phase 5 testing). Run manually: python -m app.tasks.backfill_credits
"""

from app.database.supabase_client import get_supabase_client
from app.services.content_service import ContentSyncService


def backfill_credits() -> None:
    client = get_supabase_client()
    service = ContentSyncService(max_retries=5)

    content_rows = client.table("content").select("id, external_id, content_type").execute()
    total = len(content_rows.data)
    print(f"Backfilling credits for {total} items...")

    succeeded = 0
    failed = 0
    for i, row in enumerate(content_rows.data):
        try:
            service._link_cast_and_crew(row["id"], row["external_id"], row["content_type"])
            succeeded += 1
        except Exception as exc:
            failed += 1
            print(f"  Failed for content_id={row['id']}: {exc}")

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{total}")

    print(f"Backfill complete. Succeeded: {succeeded}, Failed: {failed}")


if __name__ == "__main__":
    backfill_credits()