import os
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def import_products_from_csv(self, file_path, store_id):
    try:
        import pandas as pd
        from apps.vendors.models import Store
        from apps.categories.models import Category
        from apps.products.models import Product
        from core.utils import generate_unique_slug

        store = Store.objects.get(pk=store_id)
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        required_cols = {'name', 'price', 'stock'}
        if not required_cols.issubset(set(df.columns)):
            raise ValueError(f"Colonnes requises manquantes: {required_cols - set(df.columns)}")

        created_count = 0
        errors = []
        for idx, row in df.iterrows():
            try:
                name = str(row['name']).strip()
                price = float(row['price'])
                stock = int(row['stock'])
                if not name or price <= 0:
                    errors.append(f"Ligne {idx + 2}: données invalides")
                    continue
                category = None
                if 'category' in row and pd.notna(row['category']):
                    category = Category.objects.filter(name__iexact=str(row['category'])).first()
                slug = generate_unique_slug(Product, name)
                product, created = Product.objects.get_or_create(
                    store=store,
                    sku=str(row.get('sku', '')).strip() if pd.notna(row.get('sku')) else '',
                    defaults={
                        'name': name,
                        'slug': slug,
                        'price': price,
                        'stock': stock,
                        'category': category,
                        'description': str(row.get('description', '')),
                        'short_description': str(row.get('short_description', '')),
                        'compare_price': float(row['compare_price']) if pd.notna(row.get('compare_price')) else None,
                    }
                )
                if created:
                    created_count += 1
            except Exception as e:
                errors.append(f"Ligne {idx + 2}: {str(e)}")

        return {
            'status': 'completed',
            'created': created_count,
            'total': len(df),
            'errors': errors[:20],
        }
    except Exception as exc:
        logger.error(f"Import products error: {exc}")
        raise self.retry(exc=exc, countdown=60)
    finally:
        try:
            os.unlink(file_path)
        except Exception:
            pass
