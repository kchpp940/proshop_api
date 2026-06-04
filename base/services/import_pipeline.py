import csv
import io
import json
from collections import defaultdict

from django.db import transaction

from .row_result import RowResult
from base.models import SubCategory, Product


REQUIRED_FIELDS = ['name', 'price', 'brand', 'category']


def normalize_product_name(name):
    if not name:
        return ''
    return str(name).strip().lower()


def parse_file(file, file_format):
    raw = file.read()

    if isinstance(raw, bytes):
        raw = raw.decode('utf-8-sig')

    if file_format == 'csv':
        return _parse_csv(raw)
    elif file_format == 'json':
        return _parse_json(raw)
    else:
        raise ValueError(f"Unsupported file format: {file_format}")


def _parse_csv(content):
    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for i, row in enumerate(reader, start=1):
        row['_row_number'] = i
        rows.append(row)
    return rows


def _parse_json(content):
    data = json.loads(content)
    if isinstance(data, dict):
        data = [data]
    rows = []
    for i, item in enumerate(data, start=1):
        if isinstance(item, dict):
            item['_row_number'] = i
            rows.append(item)
    return rows


def validate_row(raw_row):
    row_number = raw_row.get('_row_number', 0)
    errors = []

    for field_name in REQUIRED_FIELDS:
        value = raw_row.get(field_name)
        if value is None or (isinstance(value, str) and value.strip() == ''):
            errors.append(f"Missing required field: {field_name}")

    price_raw = raw_row.get('price')
    if price_raw is not None and price_raw != '':
        try:
            float(price_raw)
        except (ValueError, TypeError):
            errors.append("Invalid price: must be a number")

    count_raw = raw_row.get('countInStock')
    if count_raw is not None and count_raw != '':
        try:
            int(count_raw)
        except (ValueError, TypeError):
            errors.append("Invalid countInStock: must be an integer")

    image_raw = raw_row.get('image')
    if image_raw is not None and isinstance(image_raw, str) and len(image_raw) > 200:
        errors.append("image exceeds 200 characters")

    name = _str_field(raw_row, 'name')
    if name and len(name) > 200:
        errors.append("name exceeds 200 characters")
    brand = _str_field(raw_row, 'brand')
    if brand and len(brand) > 200:
        errors.append("brand exceeds 200 characters")

    result = RowResult(
        row_number=row_number,
        status='failed' if errors else 'valid',
        product_name=name or '',
        errors=errors,
    )

    return result


def resolve_categories_batch(raw_rows):
    slug_to_row = {}
    for raw_row in raw_rows:
        slug = _str_field(raw_row, 'category')
        if slug:
            slug_to_row.setdefault(slug, []).append(raw_row)

    existing_slugs = set(
        SubCategory.objects.filter(slug__in=slug_to_row.keys())
        .values_list('slug', flat=True)
    )

    slug_to_category = {
        sc.slug: sc for sc in
        SubCategory.objects.filter(slug__in=slug_to_row.keys())
    }

    return slug_to_category, existing_slugs


def check_duplicate_batch(product_names):
    normalized_set = {normalize_product_name(n) for n in product_names if n}
    existing_map = {}
    if not normalized_set:
        return existing_map
    for p in Product.objects.all():
        key = normalize_product_name(p.name)
        if key in normalized_set:
            existing_map[key] = p
    return existing_map


def preflight_validate_batch(raw_rows):
    results_by_row = {}
    context_by_row = {}

    for raw_row in raw_rows:
        result = validate_row(raw_row)
        results_by_row[result.row_number] = result
        context_by_row[result.row_number] = {
            'raw_row': raw_row,
            'sub_category': None,
            'existing': None,
        }

    name_occurrences = defaultdict(list)
    for raw_row in raw_rows:
        rn = raw_row.get('_row_number', 0)
        if results_by_row[rn].status == 'failed':
            continue
        norm_name = normalize_product_name(_str_field(raw_row, 'name'))
        name_occurrences[norm_name].append(rn)

    for norm_name, row_numbers in name_occurrences.items():
        if len(row_numbers) > 1:
            for rn in row_numbers:
                r = results_by_row[rn]
                r.errors.append(
                    f"Duplicate product name in file (rows {', '.join(map(str, row_numbers))})"
                )
                r.status = 'failed'

    slug_to_category, existing_slugs = resolve_categories_batch(raw_rows)
    for raw_row in raw_rows:
        rn = raw_row.get('_row_number', 0)
        r = results_by_row[rn]
        if r.status == 'failed':
            continue
        slug = _str_field(raw_row, 'category')
        if slug not in existing_slugs:
            r.errors.append(f"Category slug not found: {slug}")
            r.status = 'failed'
        else:
            context_by_row[rn]['sub_category'] = slug_to_category[slug]

    valid_names = []
    for raw_row in raw_rows:
        rn = raw_row.get('_row_number', 0)
        if results_by_row[rn].status != 'failed':
            valid_names.append(_str_field(raw_row, 'name'))

    existing_map = check_duplicate_batch(valid_names)
    for raw_row in raw_rows:
        rn = raw_row.get('_row_number', 0)
        r = results_by_row[rn]
        if r.status == 'failed':
            continue
        norm_name = normalize_product_name(r.product_name)
        existing = existing_map.get(norm_name)
        if existing:
            r.warnings.append(
                f"Product with name '{r.product_name}' already exists (id={existing._id}), will update"
            )
            r.status = 'update'
            context_by_row[rn]['existing'] = existing
        else:
            r.status = 'create'

    all_valid = all(r.status != 'failed' for r in results_by_row.values())

    ordered_results = [
        results_by_row[rr.get('_row_number', 0)] for rr in raw_rows
    ]
    ordered_context = [
        context_by_row[rr.get('_row_number', 0)] for rr in raw_rows
    ]

    return all_valid, ordered_results, ordered_context


def upsert_product(raw_row, result, sub_category, existing, user):
    if result.status == 'failed':
        return result

    name = _str_field(raw_row, 'name')
    price = _decimal_field(raw_row, 'price')
    brand = _str_field(raw_row, 'brand')
    description = _str_field(raw_row, 'description')
    count_in_stock = _int_field(raw_row, 'countInStock')
    image = _str_field(raw_row, 'image')

    if result.status == 'update' and existing:
        existing.name = name
        existing.price = price if price is not None else existing.price
        existing.brand = brand or existing.brand
        existing.category = sub_category
        existing.description = description or existing.description
        if count_in_stock is not None:
            existing.countInStock = count_in_stock
        if image:
            existing.image = image
        existing.save()
        result.product_id = existing._id
        result.status = 'updated'
    else:
        product = Product.objects.create(
            user=user,
            name=name,
            price=price or 0,
            brand=brand or '',
            category=sub_category,
            description=description or '',
            countInStock=count_in_stock or 0,
            image=image or 'placeholder.png',
        )
        result.product_id = product._id
        result.status = 'created'

    return result


def write_import_summary(task, results):
    task.total_rows = len(results)
    task.created_count = sum(1 for r in results if r.status == 'created')
    task.updated_count = sum(1 for r in results if r.status == 'updated')
    task.skipped_count = sum(1 for r in results if r.status == 'skipped')
    task.failed_count = sum(1 for r in results if r.status == 'failed')

    from django.utils import timezone
    if task.status != 'failed':
        if task.failed_count > 0 and task.created_count == 0 and task.updated_count == 0:
            task.status = 'failed'
        else:
            task.status = 'completed'
    task.finished_at = timezone.now()
    task.save()

    return task


def finalize_task(task, results, status=None, error_message=None):
    if status:
        task.status = status
    if error_message:
        task.error_message = error_message
    task = write_import_summary(task, results)
    return task


def run_pipeline(file, file_format, user):
    from base.models import ImportTask

    task = ImportTask.objects.create(
        created_by=user,
        file_name=getattr(file, 'name', ''),
        file_format=file_format,
        status='processing',
    )

    try:
        raw_rows = parse_file(file, file_format)
    except Exception as e:
        task = finalize_task(
            task, [],
            status='failed',
            error_message=f"File parse error: {str(e)}",
        )
        return task, []

    preflight_ok, results, contexts = preflight_validate_batch(raw_rows)

    if not preflight_ok:
        task = finalize_task(task, results)
        return task, results

    try:
        with transaction.atomic():
            for i in range(len(raw_rows)):
                result = results[i]
                ctx = contexts[i]
                result = upsert_product(
                    ctx['raw_row'],
                    result,
                    ctx['sub_category'],
                    ctx['existing'],
                    user,
                )
                results[i] = result
            task = write_import_summary(task, results)
    except Exception as e:
        task = finalize_task(
            task, results,
            status='failed',
            error_message=f"Transaction error: {str(e)}",
        )
        return task, results

    return task, results


def _str_field(row, key):
    value = row.get(key)
    if value is None:
        return ''
    return str(value).strip()


def _decimal_field(row, key):
    value = row.get(key)
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _int_field(row, key):
    value = row.get(key)
    if value is None or value == '':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
