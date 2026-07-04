"""
BalanceLog Pro - Database Manager

SQLite database manager with WAL mode, indexed queries, connection pooling,
and parameterized query safety. Handles all CRUD operations for balancing records.
"""

import sqlite3
import threading
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
from collections import Counter

from .models import BalancingRecord, SearchFilter, DailySummary


class DatabaseManager:
    """
    Thread-safe SQLite database manager for balancing records.

    Uses WAL mode for concurrent read access and parameterized queries
    to prevent SQL injection. All operations are atomic.
    """

    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path
        self._local = threading.local()

    def set_path(self, db_path: Path) -> None:
        """Set or change database path (creates parent dirs)."""
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            if self._db_path is None:
                raise RuntimeError("Database path not set. Call set_path() first.")
            self._local.conn = sqlite3.connect(
                str(self._db_path),
                timeout=5.0,
                check_same_thread=False,
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    # ─────────────────────────────────────────────────────────
    # Schema
    # ─────────────────────────────────────────────────────────
    def init_db(self) -> None:
        """Create tables and indexes if they don't exist."""
        conn = self._get_connection()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS balancing_records (
                id                          INTEGER PRIMARY KEY AUTOINCREMENT,
                date                        TEXT NOT NULL,
                time                        TEXT NOT NULL,
                punching_number             TEXT NOT NULL DEFAULT '',
                tube_length                 REAL NOT NULL DEFAULT 0.0,
                shaft_type                  TEXT NOT NULL DEFAULT 'Unknown',
                initial_zero_degree         REAL NOT NULL DEFAULT 0.0,
                initial_left_value          REAL NOT NULL DEFAULT 0.0,
                initial_left_angle          REAL NOT NULL DEFAULT 0.0,
                initial_right_value         REAL NOT NULL DEFAULT 0.0,
                initial_right_angle         REAL NOT NULL DEFAULT 0.0,
                weight_addition_left        REAL NOT NULL DEFAULT 0.0,
                weight_addition_right       REAL NOT NULL DEFAULT 0.0,
                after_correction_zero_degree REAL NOT NULL DEFAULT 0.0,
                after_correction_left       REAL NOT NULL DEFAULT 0.0,
                after_correction_right      REAL NOT NULL DEFAULT 0.0,
                screenshot_path             TEXT NOT NULL DEFAULT '',
                ocr_confidence              REAL NOT NULL DEFAULT 0.0,
                operator_notes              TEXT NOT NULL DEFAULT '',
                created_at                  TEXT NOT NULL,
                updated_at                  TEXT NOT NULL,
                is_validated                INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_date
                ON balancing_records(date);
            CREATE INDEX IF NOT EXISTS idx_punching_number
                ON balancing_records(punching_number);
            CREATE INDEX IF NOT EXISTS idx_tube_length
                ON balancing_records(tube_length);
            CREATE INDEX IF NOT EXISTS idx_shaft_type
                ON balancing_records(shaft_type);
            CREATE INDEX IF NOT EXISTS idx_date_time
                ON balancing_records(date, time);

            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            );
        """)
        # Insert schema version if not present
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        if row is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (1,))
        conn.commit()

    # ─────────────────────────────────────────────────────────
    # Insert
    # ─────────────────────────────────────────────────────────
    def insert_record(self, record: BalancingRecord) -> int:
        """Insert a new balancing record. Returns the new record ID."""
        now = datetime.now().isoformat()
        if not record.created_at:
            record.created_at = now
        record.updated_at = now

        conn = self._get_connection()
        with self._lock:
            cursor = conn.execute("""
                INSERT INTO balancing_records (
                    date, time, punching_number, tube_length, shaft_type,
                    initial_zero_degree, initial_left_value, initial_left_angle,
                    initial_right_value, initial_right_angle,
                    weight_addition_left, weight_addition_right,
                    after_correction_zero_degree, after_correction_left,
                    after_correction_right,
                    screenshot_path, ocr_confidence, operator_notes,
                    created_at, updated_at, is_validated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.date, record.time, record.punching_number,
                record.tube_length, record.shaft_type,
                record.initial_zero_degree, record.initial_left_value,
                record.initial_left_angle, record.initial_right_value,
                record.initial_right_angle,
                record.weight_addition_left, record.weight_addition_right,
                record.after_correction_zero_degree,
                record.after_correction_left, record.after_correction_right,
                record.screenshot_path, record.ocr_confidence,
                record.operator_notes,
                record.created_at, record.updated_at,
                1 if record.is_validated else 0,
            ))
            conn.commit()
            record.id = cursor.lastrowid
            return cursor.lastrowid

    # ─────────────────────────────────────────────────────────
    # Update
    # ─────────────────────────────────────────────────────────
    def update_record(self, record: BalancingRecord) -> bool:
        """Update an existing record by ID."""
        if record.id is None:
            return False
        record.updated_at = datetime.now().isoformat()
        conn = self._get_connection()
        with self._lock:
            conn.execute("""
                UPDATE balancing_records SET
                    date=?, time=?, punching_number=?, tube_length=?, shaft_type=?,
                    initial_zero_degree=?, initial_left_value=?, initial_left_angle=?,
                    initial_right_value=?, initial_right_angle=?,
                    weight_addition_left=?, weight_addition_right=?,
                    after_correction_zero_degree=?, after_correction_left=?,
                    after_correction_right=?,
                    screenshot_path=?, ocr_confidence=?, operator_notes=?,
                    updated_at=?, is_validated=?
                WHERE id=?
            """, (
                record.date, record.time, record.punching_number,
                record.tube_length, record.shaft_type,
                record.initial_zero_degree, record.initial_left_value,
                record.initial_left_angle, record.initial_right_value,
                record.initial_right_angle,
                record.weight_addition_left, record.weight_addition_right,
                record.after_correction_zero_degree,
                record.after_correction_left, record.after_correction_right,
                record.screenshot_path, record.ocr_confidence,
                record.operator_notes, record.updated_at,
                1 if record.is_validated else 0,
                record.id,
            ))
            conn.commit()
            return True

    # ─────────────────────────────────────────────────────────
    # Delete
    # ─────────────────────────────────────────────────────────
    def delete_record(self, record_id: int) -> bool:
        """Delete a record by ID."""
        conn = self._get_connection()
        with self._lock:
            cursor = conn.execute(
                "DELETE FROM balancing_records WHERE id=?", (record_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    # ─────────────────────────────────────────────────────────
    # Query
    # ─────────────────────────────────────────────────────────
    def get_record(self, record_id: int) -> Optional[BalancingRecord]:
        """Get a single record by ID."""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM balancing_records WHERE id=?", (record_id,)
        ).fetchone()
        return self._row_to_record(row) if row else None

    def get_all_records(self, limit: int = 500, offset: int = 0) -> List[BalancingRecord]:
        """Get all records with pagination."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM balancing_records ORDER BY date DESC, time DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get_records_by_date(self, date_str: str) -> List[BalancingRecord]:
        """Get all records for a specific date."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM balancing_records WHERE date=? ORDER BY time DESC",
            (date_str,),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def search_records(self, filters: SearchFilter) -> List[BalancingRecord]:
        """Search records with flexible filtering."""
        conditions: List[str] = []
        params: List = []

        if filters.punching_number:
            conditions.append("punching_number LIKE ?")
            params.append(f"%{filters.punching_number}%")

        if filters.date_from:
            conditions.append("date >= ?")
            params.append(filters.date_from)

        if filters.date_to:
            conditions.append("date <= ?")
            params.append(filters.date_to)

        if filters.time_from:
            conditions.append("time >= ?")
            params.append(filters.time_from)

        if filters.time_to:
            conditions.append("time <= ?")
            params.append(filters.time_to)

        if filters.tube_length_min is not None:
            conditions.append("tube_length >= ?")
            params.append(filters.tube_length_min)

        if filters.tube_length_max is not None:
            conditions.append("tube_length <= ?")
            params.append(filters.tube_length_max)

        if filters.shaft_type:
            conditions.append("shaft_type = ?")
            params.append(filters.shaft_type)

        if filters.min_confidence is not None:
            conditions.append("ocr_confidence >= ?")
            params.append(filters.min_confidence)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Validate order_by to prevent injection
        allowed_order = {"date", "time", "punching_number", "tube_length",
                         "shaft_type", "ocr_confidence", "id"}
        order_by = filters.order_by if filters.order_by in allowed_order else "date"
        order_dir = "ASC" if filters.order_dir.upper() == "ASC" else "DESC"

        query = f"""
            SELECT * FROM balancing_records
            WHERE {where_clause}
            ORDER BY {order_by} {order_dir}
            LIMIT ? OFFSET ?
        """
        params.extend([filters.limit, filters.offset])

        conn = self._get_connection()
        rows = conn.execute(query, params).fetchall()
        return [self._row_to_record(r) for r in rows]

    def count_records(self, filters: Optional[SearchFilter] = None) -> int:
        """Count total records matching filters."""
        conn = self._get_connection()
        if filters is None or not filters.has_filters():
            row = conn.execute("SELECT COUNT(*) FROM balancing_records").fetchone()
        else:
            conditions: List[str] = []
            params: List = []
            if filters.punching_number:
                conditions.append("punching_number LIKE ?")
                params.append(f"%{filters.punching_number}%")
            if filters.date_from:
                conditions.append("date >= ?")
                params.append(filters.date_from)
            if filters.date_to:
                conditions.append("date <= ?")
                params.append(filters.date_to)
            if filters.shaft_type:
                conditions.append("shaft_type = ?")
                params.append(filters.shaft_type)
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            row = conn.execute(
                f"SELECT COUNT(*) FROM balancing_records WHERE {where_clause}",
                params,
            ).fetchone()
        return row[0] if row else 0

    # ─────────────────────────────────────────────────────────
    # Statistics
    # ─────────────────────────────────────────────────────────
    def get_daily_summary(self, date_str: str) -> DailySummary:
        """Get production summary for a specific date."""
        conn = self._get_connection()
        row = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN shaft_type='Front' THEN 1 ELSE 0 END) as front_count,
                SUM(CASE WHEN shaft_type='Rear' THEN 1 ELSE 0 END) as rear_count,
                AVG(initial_left_value) as avg_init_left,
                AVG(initial_right_value) as avg_init_right,
                AVG(after_correction_left) as avg_final_left,
                AVG(after_correction_right) as avg_final_right,
                AVG(ocr_confidence) as avg_confidence
            FROM balancing_records
            WHERE date=?
        """, (date_str,)).fetchone()

        summary = DailySummary(date=date_str)
        if row and row["total"]:
            summary.total_shafts = row["total"]
            summary.front_shafts = row["front_count"] or 0
            summary.rear_shafts = row["rear_count"] or 0
            summary.avg_initial_left = round(row["avg_init_left"] or 0, 2)
            summary.avg_initial_right = round(row["avg_init_right"] or 0, 2)
            summary.avg_final_left = round(row["avg_final_left"] or 0, 2)
            summary.avg_final_right = round(row["avg_final_right"] or 0, 2)
            summary.avg_ocr_confidence = round(row["avg_confidence"] or 0, 2)

        # Count screenshots
        ss_row = conn.execute(
            "SELECT COUNT(*) FROM balancing_records WHERE date=? AND screenshot_path != ''",
            (date_str,),
        ).fetchone()
        summary.screenshots_count = ss_row[0] if ss_row else 0

        return summary

    def get_records_by_date_range(
        self, start_date: str, end_date: str
    ) -> List[BalancingRecord]:
        """Get all records within a date range."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM balancing_records WHERE date>=? AND date<=? ORDER BY date, time",
            (start_date, end_date),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get_statistics(self, start_date: str, end_date: str) -> dict:
        """Get aggregated statistics for a date range."""
        conn = self._get_connection()
        row = conn.execute("""
            SELECT
                COUNT(*) as total,
                AVG(initial_left_value + initial_right_value) / 2 as avg_initial,
                AVG(after_correction_left + after_correction_right) / 2 as avg_final,
                AVG(ocr_confidence) as avg_confidence,
                MIN(ocr_confidence) as min_confidence,
                MAX(ocr_confidence) as max_confidence
            FROM balancing_records
            WHERE date >= ? AND date <= ?
        """, (start_date, end_date)).fetchone()

        # Most common weight additions
        weight_rows = conn.execute("""
            SELECT weight_addition_left, weight_addition_right
            FROM balancing_records
            WHERE date >= ? AND date <= ?
        """, (start_date, end_date)).fetchall()

        all_weights = []
        for wr in weight_rows:
            if wr["weight_addition_left"]:
                all_weights.append(wr["weight_addition_left"])
            if wr["weight_addition_right"]:
                all_weights.append(wr["weight_addition_right"])

        most_common = Counter(all_weights).most_common(1)

        return {
            "total_shafts": row["total"] if row else 0,
            "avg_initial_imbalance": round(row["avg_initial"] or 0, 2) if row else 0,
            "avg_final_imbalance": round(row["avg_final"] or 0, 2) if row else 0,
            "avg_confidence": round(row["avg_confidence"] or 0, 2) if row else 0,
            "min_confidence": round(row["min_confidence"] or 0, 2) if row else 0,
            "max_confidence": round(row["max_confidence"] or 0, 2) if row else 0,
            "most_common_weight": most_common[0][0] if most_common else 0,
        }

    def check_duplicate(self, punching_number: str, date_str: str,
                        time_str: str, window_sec: int = 5) -> bool:
        """Check if a near-duplicate record exists within the time window."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT time FROM balancing_records WHERE punching_number=? AND date=?",
            (punching_number, date_str),
        ).fetchall()

        if not rows:
            return False

        try:
            new_time = datetime.strptime(time_str, "%H:%M:%S")
            for r in rows:
                existing_time = datetime.strptime(r["time"], "%H:%M:%S")
                diff = abs((new_time - existing_time).total_seconds())
                if diff <= window_sec:
                    return True
        except ValueError:
            pass
        return False

    # ─────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> BalancingRecord:
        """Convert a database row to a BalancingRecord."""
        return BalancingRecord(
            id=row["id"],
            date=row["date"],
            time=row["time"],
            punching_number=row["punching_number"],
            tube_length=row["tube_length"],
            shaft_type=row["shaft_type"],
            initial_zero_degree=row["initial_zero_degree"],
            initial_left_value=row["initial_left_value"],
            initial_left_angle=row["initial_left_angle"],
            initial_right_value=row["initial_right_value"],
            initial_right_angle=row["initial_right_angle"],
            weight_addition_left=row["weight_addition_left"],
            weight_addition_right=row["weight_addition_right"],
            after_correction_zero_degree=row["after_correction_zero_degree"],
            after_correction_left=row["after_correction_left"],
            after_correction_right=row["after_correction_right"],
            screenshot_path=row["screenshot_path"],
            ocr_confidence=row["ocr_confidence"],
            operator_notes=row["operator_notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_validated=bool(row["is_validated"]),
        )

    def get_unique_dates(self) -> List[str]:
        """Get all unique dates that have records."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT DISTINCT date FROM balancing_records ORDER BY date DESC"
        ).fetchall()
        return [r["date"] for r in rows]

    def close(self) -> None:
        """Close the thread-local connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
