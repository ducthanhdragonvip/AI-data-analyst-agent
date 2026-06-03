import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.core.config import get_settings
from src.core.models import Dataset
from src.modules.data.loaders.database_introspection import INTERNAL_TABLES, quote_identifier
from src.modules.data.loaders.dataset_profile import profile_dataframe
from src.modules.data.loaders.tabular import read_tabular_file


def sanitize_table_name(name: str) -> str:
    stem = Path(name).stem.lower()
    sanitized = re.sub(r"[^a-z0-9_]+", "_", stem).strip("_") or "dataset"
    if sanitized[0].isdigit():
        sanitized = f"dataset_{sanitized}"
    return f"uploaded_{sanitized}"[:120]


class DatasetService:
    def __init__(
        self,
        session: AsyncSession,
        upload_dir: Path | None = None,
        business_store=None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.upload_dir = upload_dir or self.settings.upload_dir
        self.business_store = business_store

    async def list_datasets(self) -> list[Dataset]:
        result = await self.session.execute(select(Dataset).order_by(Dataset.created_at.desc()))
        return list(result.scalars())

    async def ingest_upload(self, file_name: str, content: bytes) -> Dataset:
        if not file_name.lower().endswith(".csv"):
            raise ValueError("Only CSV uploads are supported")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        upload_path = self.upload_dir / Path(file_name).name
        upload_path.write_bytes(content)
        frame = read_tabular_file(upload_path)
        profile = profile_dataframe(frame)
        dataset = Dataset(
            source_type="upload",
            display_name=upload_path.name,
            table_schema=None,
            table_name=None,
            file_name=upload_path.name,
            row_count=profile["row_count"],
            profile=profile,
        )
        self.session.add(dataset)
        await self.session.flush()
        return dataset

    async def import_upload_to_database(self, dataset_id: int) -> Dataset | None:
        dataset = await self.session.get(Dataset, dataset_id)
        if not dataset:
            return None
        if dataset.source_type != "upload":
            raise ValueError("Only uploaded files can be saved to the database")
        if dataset.table_name:
            return dataset
        if not dataset.file_name:
            raise ValueError("Uploaded dataset is missing its source file")

        upload_path = self.upload_dir / dataset.file_name
        if not upload_path.exists():
            raise ValueError("Uploaded source file is missing")
        frame = read_tabular_file(upload_path)
        table_name = await self._unique_table_name(sanitize_table_name(dataset.file_name))
        engine = create_engine(self.settings.sync_database_url, pool_pre_ping=True)
        frame.to_sql(table_name, engine, schema="public", if_exists="replace", index=False)

        dataset.table_schema = "public"
        dataset.table_name = table_name
        dataset.row_count = len(frame)
        dataset.profile = profile_dataframe(frame)
        await self.session.flush()
        return dataset

    async def refresh_postgres_tables(self) -> list[Dataset]:
        engine = create_engine(self.settings.sync_database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            table_names = [
                row[0]
                for row in conn.execute(
                    text(
                        "select table_name from information_schema.tables "
                        "where table_schema = 'public' and table_type = 'BASE TABLE'"
                    )
                )
            ]

        registered: list[Dataset] = []
        for table_name in table_names:
            if table_name in INTERNAL_TABLES:
                continue
            existing = await self._get_by_table("public", table_name)
            if existing:
                registered.append(existing)
                continue
            with engine.connect() as conn:
                count = int(conn.execute(text(f'SELECT count(*) FROM public.{quote_identifier(table_name)}')).scalar_one())
                sample = pd.read_sql_query(text(f'SELECT * FROM public.{quote_identifier(table_name)} LIMIT 1000'), conn)
            profile = profile_dataframe(sample)
            profile["row_count"] = count
            dataset = Dataset(
                source_type="postgres",
                display_name=table_name,
                table_schema="public",
                table_name=table_name,
                file_name=None,
                row_count=count,
                profile=profile,
            )
            self.session.add(dataset)
            await self.session.flush()
            registered.append(dataset)
        return registered

    async def delete_dataset(self, dataset_id: int) -> bool:
        dataset = await self.session.get(Dataset, dataset_id)
        if not dataset:
            return False
        if dataset.source_type == "upload" and dataset.file_name:
            (self.upload_dir / dataset.file_name).unlink(missing_ok=True)
            if dataset.table_schema and dataset.table_name:
                self._drop_uploaded_table(dataset.table_schema, dataset.table_name)
        await self.session.delete(dataset)
        return True

    async def _get_by_table(self, schema: str, table_name: str) -> Dataset | None:
        result = await self.session.execute(
            select(Dataset).where(Dataset.table_schema == schema, Dataset.table_name == table_name)
        )
        return result.scalar_one_or_none()

    async def _unique_table_name(self, base: str) -> str:
        table_name = base
        suffix = 2
        while await self._get_by_table("public", table_name):
            table_name = f"{base}_{suffix}"
            suffix += 1
        return table_name

    def _drop_uploaded_table(self, schema: str, table_name: str) -> None:
        engine = create_engine(self.settings.sync_database_url, pool_pre_ping=True)
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {quote_identifier(schema)}.{quote_identifier(table_name)}"))
