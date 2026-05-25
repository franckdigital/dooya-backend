from celery import shared_task


@shared_task(name='audit.compute_monthly_snapshots')
def compute_monthly_snapshots_task():
    """
    Runs on the 1st of each month (via Celery beat) to snapshot the previous month's KPIs.
    Also generates global + per-store snapshots and triggers KPI alerts.
    """
    from datetime import date
    from .services import save_monthly_snapshot

    today = date.today()
    # Snapshot the previous month
    if today.month == 1:
        year, month = today.year - 1, 12
    else:
        year, month = today.year, today.month - 1

    # Global snapshot
    save_monthly_snapshot(year, month, store=None)

    # Per-store snapshots
    from apps.vendors.models import Store
    for store in Store.objects.filter(is_active=True):
        try:
            save_monthly_snapshot(year, month, store=store)
        except Exception:
            pass

    return f'Snapshots computed for {year}/{month:02d}'


@shared_task(name='audit.compute_current_month_snapshot')
def compute_current_month_snapshot_task(year=None, month=None, store_id=None):
    """On-demand task to (re)compute snapshot for any month."""
    from datetime import date
    from .services import save_monthly_snapshot

    if year is None or month is None:
        today = date.today()
        year, month = today.year, today.month

    store = None
    if store_id:
        from apps.vendors.models import Store
        try:
            store = Store.objects.get(pk=store_id)
        except Store.DoesNotExist:
            pass

    snapshot = save_monthly_snapshot(year, month, store=store)
    return f'Snapshot saved: {snapshot}'
