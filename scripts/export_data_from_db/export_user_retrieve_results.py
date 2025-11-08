#!/usr/bin/env python3
"""
导出 user_retrieve_results 全量数据，并基于 retrieve_ids/top_k_ids 汇总论文元数据。

输出：
1. JSONL，每行包含 user_name/query/date/retrieved_ids/top_k_ids
2. TSV，每行格式：arxivID \t title . abstract
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence, Set, Tuple

import sqlalchemy as sa
import yaml
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

LOGGER = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    user_db_url: str
    metadata_db_url: str





def load_database_config(config_path: Path) -> DatabaseConfig:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fp:
        config = yaml.safe_load(fp)

    try:
        user_db = config["USER_DB"]
        metadata_db = config["INDEX_SERVICE"]["metadata_db"]
    except KeyError as exc:
        raise KeyError(f"Missing expected configuration section: {exc}") from exc

    user_db_url = (
        "postgresql+psycopg2://"
        f"{user_db['db_user']}:{user_db['db_password']}"
        f"@{user_db['db_host']}:{user_db['db_port']}/{user_db['db_name']}"
    )
    metadata_db_url = metadata_db["db_url"]
    return DatabaseConfig(user_db_url=user_db_url, metadata_db_url=metadata_db_url)


def build_session_factory(db_url: str) -> sessionmaker:
    engine: Engine = sa.create_engine(db_url, future=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def fetch_user_retrieve_results(
    session_factory: sessionmaker, limit: int | None
) -> List[dict]:
    with session_factory() as session:  # type: Session
        query = sa.text(
            """
            SELECT
                username,
                query,
                search_strategy,
                recommendation_date,
                retrieve_ids,
                top_k_ids
            FROM user_retrieve_results
            ORDER BY recommendation_date ASC, id ASC
            """
        )
        if limit:
            query = query.execution_options(postgresql_limit=limit)
        result = session.execute(query)
        rows = result.fetchall()

    records = []
    for row in rows[: limit if limit else None]:
        retrieved_ids = _ensure_list(row.retrieve_ids)
        top_k_ids = _ensure_list(row.top_k_ids)
        records.append(
            {
                "user_name": row.username,
                "query": row.query,
                "search_strategy": row.search_strategy,
                "date": _format_datetime(row.recommendation_date),
                "retrieved_ids": retrieved_ids,
                "top_k_ids": top_k_ids,
            }
        )
    return records


def _ensure_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _format_datetime(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone().isoformat()
    return str(value)


def collect_unique_ids(records: Sequence[dict]) -> Set[str]:
    ids: Set[str] = set()
    for record in records:
        ids.update(_normalize_ids(record["retrieved_ids"]))
        ids.update(_normalize_ids(record["top_k_ids"]))
    return ids


def _normalize_ids(ids: Iterable[str]) -> List[str]:
    normalized = []
    for item in ids:
        if not item:
            continue
        normalized.append(str(item).strip())
    return normalized


def fetch_paper_metadata(
    session_factory: sessionmaker, doc_ids: Sequence[str]
) -> Tuple[List[Tuple[str, str, str]], Set[str]]:
    missing_ids: Set[str] = set()
    if not doc_ids:
        return [], missing_ids

    with session_factory() as session:  # type: Session
        query = sa.text(
            """
            SELECT doc_id, title, abstract
            FROM papers
            WHERE doc_id = ANY(:doc_ids)
            """
        )
        result = session.execute(query, {"doc_ids": list(doc_ids)})
        rows = result.fetchall()


    print(len(rows))
    found = {(row.doc_id, row.title or "", row.abstract or "") for row in rows}
    fetched_ids = {row[0] for row in found}
    missing_ids = set(doc_ids) - fetched_ids
    return list(found), missing_ids


def write_user_results(path: Path, records: Sequence[dict]) -> None:
    with path.open("w", encoding="utf-8") as fp:
        for record in records:
            fp.write(json.dumps(record, ensure_ascii=False))
            fp.write("\n")


def write_paper_metadata(
    path: Path, metadata_rows: Sequence[Tuple[str, str, str]], missing_ids: Set[str]
) -> None:

    with path.open("w", encoding="utf-8") as fp:
        cnt=0
        for doc_id, title, abstract in sorted(metadata_rows, key=lambda x: x[0]):
            title=title.replace("\n", " ")
            abstract=abstract.replace("\n", " ")
            line = f"{doc_id}\t{title.strip()} . {abstract.strip()}"
            fp.write(line)
            fp.write("\n")
            cnt+=1
        print(cnt)
        if missing_ids:
            fp.write("# Missing metadata for the following IDs:\n")
            for doc_id in sorted(missing_ids):
                fp.write(f"# {doc_id}\n")


    

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Export user retrieve results and associated paper metadata."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default='app_config.yaml',
        help="Path to app_config.yaml (default: backend/configs/app_config.yaml)",
    )
    parser.add_argument(
        "--user-output",
        type=Path,
        default=Path("export_user_retrieve_results.jsonl"),
        help="Output path for user retrieve results JSONL file.",
    )
    parser.add_argument(
        "--paper-output",
        type=Path,
        default=Path("arxiv_metadata.tsv"),
        help="Output path for aggregated paper metadata TSV file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit of records to export from user_retrieve_results.",
    )
    
    args = parser.parse_args()

    try:
        db_config = load_database_config(args.config)
    except Exception as exc:
        LOGGER.error("Failed to load configuration: %s", exc)
        sys.exit(1)

    LOGGER.info("Using user DB: %s", db_config.user_db_url)
    LOGGER.info("Using metadata DB: %s", db_config.metadata_db_url)

    try:
        user_session_factory = build_session_factory(db_config.user_db_url)
        metadata_session_factory = build_session_factory(db_config.metadata_db_url)
    except Exception as exc:
        LOGGER.error("Failed to initialize database connections: %s", exc)
        sys.exit(1)

    LOGGER.info("Fetching user retrieve results...")
    user_records = fetch_user_retrieve_results(user_session_factory, args.limit)
    LOGGER.info("Retrieved %s records", len(user_records))

    LOGGER.info("Writing user retrieve results to %s", args.user_output)
    write_user_results(args.user_output, user_records)

    unique_ids = collect_unique_ids(user_records)
    LOGGER.info("Collected %s unique arxiv IDs", len(unique_ids))

    LOGGER.info("Fetching paper metadata...")
    metadata_rows, missing_ids = fetch_paper_metadata(metadata_session_factory, sorted(unique_ids))
    LOGGER.info("Fetched metadata for %s IDs; %s missing", len(metadata_rows), len(missing_ids))

    LOGGER.info("Writing paper metadata to %s", args.paper_output)
    write_paper_metadata(args.paper_output, metadata_rows, missing_ids)

    LOGGER.info("Export completed successfully.")

