"""Import a USDA FoodData Central CSV dataset into `foods` and `food_portions`.

Usage (from backend/, with the venv active):

    python -m scripts.import_usda ../data/sr_legacy
    python -m scripts.import_usda ../data/foundation

Takes a directory rather than hardcoding a dataset, so the same script loads
Branded Foods later. Idempotent: re-running upserts on (source, external_id),
so a corrected dataset can be re-imported without duplicating rows.
"""

import argparse
import asyncio
import csv
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal
from app.models.food import Food, FoodPortion

# USDA ships nutrients tall (one row per nutrient per food); our schema stores them
# wide. These are nutrient.csv ids.
NUTRIENT_COLUMNS = {
    1003: "protein_per_100g",
    1004: "fat_per_100g",
    1005: "carbs_per_100g",
    1079: "fiber_per_100g",
    1093: "sodium_mg_per_100g",
    2000: "sugar_per_100g",
}

# Energy needs a fallback chain. Only 135 of 436 Foundation foods report nutrient
# 1008; the rest give Atwater-derived values. Specific factors are more accurate
# than general, so they win when both exist.
ENERGY_NUTRIENTS = (1008, 2048, 2047)

# Rows in food.csv that are actual foods. The Foundation download also contains
# ~77k lab sub-samples and acquisition records, which are provenance, not food.
FOOD_DATA_TYPES = {"foundation_food", "sr_legacy_food", "branded_food"}

ALL_NUTRIENT_IDS = set(NUTRIENT_COLUMNS) | set(ENERGY_NUTRIENTS)

# A multi-row INSERT ... VALUES requires every row to carry the same keys, and most
# foods are missing at least one nutrient. Rows are squared off against this list
# before insert so absent nutrients become explicit nulls.
FOOD_FIELDS = (
    "source",
    "external_id",
    "data_type",
    "food_name",
    "calories_per_100g",
    *NUTRIENT_COLUMNS.values(),
    "default_serving_g",
)

BATCH_SIZE = 500


def find_csv(dataset_dir: Path, name: str) -> Path:
    """Locate a CSV. The zips extract to a nested, release-dated folder."""
    matches = list(dataset_dir.rglob(name))
    if not matches:
        raise FileNotFoundError(f"{name} not found under {dataset_dir}")
    return matches[0]


def to_decimal(raw: str) -> Decimal | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        return Decimal(raw)
    except ArithmeticError:
        return None


def format_amount(amount: Decimal | None) -> str:
    """1.000 -> "1", 0.500 -> "0.5"."""
    if amount is None:
        return ""
    normalized = amount.normalize()
    return format(normalized, "f")


def build_portion_description(
    amount: Decimal | None, unit: str | None, portion_description: str, modifier: str
) -> str:
    """Turn USDA's four loosely-used fields into one label a person can read.

    measure_unit_id 9999 means "undetermined", in which case the human-readable
    text lives in modifier or portion_description instead.
    """
    detail = (modifier or portion_description or "").strip()

    if unit and unit != "undetermined":
        label = f"{format_amount(amount)} {unit}".strip()
        return f"{label}, {detail}" if detail else label

    base = detail or "serving"
    if amount is not None and amount != 1:
        return f"{format_amount(amount)} x {base}"
    return base


def load_foods(dataset_dir: Path) -> dict[str, dict]:
    """fdc_id -> partial food row, for real foods only."""
    foods: dict[str, dict] = {}
    with find_csv(dataset_dir, "food.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["data_type"] not in FOOD_DATA_TYPES:
                continue
            foods[row["fdc_id"]] = {
                "source": "usda",
                "external_id": row["fdc_id"],
                "data_type": row["data_type"],
                "food_name": row["description"],
            }
    return foods


def apply_nutrients(dataset_dir: Path, foods: dict[str, dict]) -> None:
    """Stream food_nutrient.csv and pivot the nutrients we care about onto foods."""
    energy: dict[str, dict[int, Decimal]] = {}

    with find_csv(dataset_dir, "food_nutrient.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        for row in csv.DictReader(handle):
            fdc_id = row["fdc_id"]
            food = foods.get(fdc_id)
            if food is None:
                continue

            try:
                nutrient_id = int(row["nutrient_id"])
            except ValueError:
                continue
            if nutrient_id not in ALL_NUTRIENT_IDS:
                continue

            amount = to_decimal(row["amount"])
            if amount is None:
                continue

            if nutrient_id in NUTRIENT_COLUMNS:
                food[NUTRIENT_COLUMNS[nutrient_id]] = amount
            else:
                energy.setdefault(fdc_id, {})[nutrient_id] = amount

    for fdc_id, by_nutrient in energy.items():
        for nutrient_id in ENERGY_NUTRIENTS:
            if nutrient_id in by_nutrient:
                foods[fdc_id]["calories_per_100g"] = by_nutrient[nutrient_id]
                break


def load_portions(dataset_dir: Path, known_fdc_ids: set[str]) -> dict[str, list[dict]]:
    """fdc_id -> portion rows, ordered by USDA's sequence number."""
    units: dict[str, str] = {}
    with find_csv(dataset_dir, "measure_unit.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        for row in csv.DictReader(handle):
            units[row["id"]] = row["name"]

    portions: dict[str, list[dict]] = {}
    with find_csv(dataset_dir, "food_portion.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        for row in csv.DictReader(handle):
            fdc_id = row["fdc_id"]
            if fdc_id not in known_fdc_ids:
                continue

            gram_weight = to_decimal(row["gram_weight"])
            if gram_weight is None or gram_weight <= 0:
                continue

            amount = to_decimal(row["amount"])
            unit = units.get(row["measure_unit_id"])
            seq_raw = row.get("seq_num", "").strip()

            portions.setdefault(fdc_id, []).append(
                {
                    "external_id": row["id"],
                    "amount": amount,
                    "unit": None if unit == "undetermined" else unit,
                    "modifier": row.get("modifier") or None,
                    "description": build_portion_description(
                        amount, unit, row.get("portion_description", ""), row.get("modifier", "")
                    ),
                    "gram_weight": gram_weight,
                    "seq_num": int(seq_raw) if seq_raw.isdigit() else None,
                }
            )

    for rows in portions.values():
        rows.sort(key=lambda r: (r["seq_num"] is None, r["seq_num"] or 0))
    return portions


async def upsert_foods(session, food_rows: list[dict]) -> None:
    for start in range(0, len(food_rows), BATCH_SIZE):
        batch = food_rows[start : start + BATCH_SIZE]
        statement = insert(Food).values(batch)
        await session.execute(
            statement.on_conflict_do_update(
                constraint="uq_foods_source_external_id",
                set_={
                    column: statement.excluded[column]
                    for column in batch[0]
                    if column not in ("source", "external_id")
                },
            )
        )
    await session.commit()


async def upsert_portions(session, portion_rows: list[dict]) -> None:
    for start in range(0, len(portion_rows), BATCH_SIZE):
        batch = portion_rows[start : start + BATCH_SIZE]
        statement = insert(FoodPortion).values(batch)
        await session.execute(
            statement.on_conflict_do_update(
                constraint="uq_food_portions_food_external",
                set_={
                    column: statement.excluded[column]
                    for column in batch[0]
                    if column not in ("food_id", "external_id")
                },
            )
        )
    await session.commit()


async def run(dataset_dir: Path) -> None:
    print(f"Reading {dataset_dir}")
    foods = load_foods(dataset_dir)
    print(f"  {len(foods):,} foods")

    apply_nutrients(dataset_dir, foods)
    with_calories = sum(1 for f in foods.values() if "calories_per_100g" in f)
    print(f"  {with_calories:,} with calories")

    portions_by_fdc = load_portions(dataset_dir, set(foods))
    print(f"  {sum(len(v) for v in portions_by_fdc.values()):,} portions")

    # A food's default serving is its first-sequenced portion — USDA orders them
    # with the most conventional measure first.
    for fdc_id, rows in portions_by_fdc.items():
        if rows:
            foods[fdc_id]["default_serving_g"] = rows[0]["gram_weight"]

    food_rows = [{field: food.get(field) for field in FOOD_FIELDS} for food in foods.values()]

    async with SessionLocal() as session:
        await upsert_foods(session, food_rows)

        # Portions reference foods.id, which is only known after the upsert.
        result = await session.execute(
            select(Food.external_id, Food.id).where(Food.source == "usda")
        )
        food_id_by_external = dict(result.all())

        portion_rows = [
            {**portion, "food_id": food_id_by_external[fdc_id]}
            for fdc_id, rows in portions_by_fdc.items()
            if fdc_id in food_id_by_external
            for portion in rows
        ]
        await upsert_portions(session, portion_rows)

    print(f"Imported {len(foods):,} foods and {len(portion_rows):,} portions.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path, help="Directory holding the USDA CSVs")
    args = parser.parse_args()

    if not args.dataset_dir.is_dir():
        print(f"Not a directory: {args.dataset_dir}", file=sys.stderr)
        return 1

    asyncio.run(run(args.dataset_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
