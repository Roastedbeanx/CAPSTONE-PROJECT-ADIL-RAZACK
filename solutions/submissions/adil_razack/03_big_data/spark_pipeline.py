"""Pillar 3 Task 3.1: Spark event processing pipeline."""

from __future__ import annotations

import os
import time
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import MapType, StringType, StructField, StructType, TimestampType


PROJECT_ROOT = Path(__file__).resolve().parents[4]
EVENTS_DIR = Path(os.getenv("EVENTS_DIR", PROJECT_ROOT / "datasets" / "events_stream"))
OUTPUT_DIR = Path(
    os.getenv(
        "OUTPUT_DIR",
        PROJECT_ROOT / "outputs" / "results" / "adil_razack" / "03_big_data" / "spark",
    )
)

EVENT_SCHEMA = StructType(
    [
        StructField("event_id", StringType(), nullable=False),
        StructField("event_type", StringType(), nullable=True),
        StructField("project_id", StringType(), nullable=True),
        StructField("user_id", StringType(), nullable=False),
        StructField("timestamp", TimestampType(), nullable=True),
        StructField("payload", MapType(StringType(), StringType()), nullable=True),
    ]
)


def get_spark_session() -> SparkSession:
    spark = (
        SparkSession.builder.appName("PresightEventsProcessing")
        .master("local[*]")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def load_events(spark: SparkSession, events_dir: Path) -> DataFrame:
    event_files = sorted(events_dir.glob("events_*.jsonl"))
    if not event_files:
        raise FileNotFoundError(f"No event files found in {events_dir}")
    return spark.read.schema(EVENT_SCHEMA).json([str(path) for path in event_files])


def validate_events(df: DataFrame) -> DataFrame:
    raw_count = df.count()
    valid = df.dropna(subset=["event_id", "user_id"])
    after_required_count = valid.count()
    print(f"events loaded={raw_count}; dropped_missing_keys={raw_count - after_required_count}")

    duplicate_window = Window.partitionBy("event_id").orderBy(
        F.col("timestamp").asc_nulls_last()
    )
    deduplicated = (
        valid.withColumn("duplicate_rank", F.row_number().over(duplicate_window))
        .where(F.col("duplicate_rank") == 1)
        .drop("duplicate_rank")
    )
    after_dedup_count = deduplicated.count()
    print(f"events after required keys={after_required_count}; dropped_duplicates={after_required_count - after_dedup_count}")

    return (
        deduplicated.withColumn("event_date", F.to_date("timestamp"))
        .withColumn("event_hour", F.hour("timestamp"))
        .withColumn("event_month", F.date_format("timestamp", "yyyy-MM"))
    )


def project_activity_summary(df: DataFrame) -> DataFrame:
    return (
        df.where(F.col("project_id").isNotNull())
        .groupBy("project_id")
        .agg(
            F.count("*").alias("total_events"),
            F.sum(F.when(F.col("event_type") == "escalation_raised", 1).otherwise(0)).alias("escalation_count"),
            F.sum(F.when(F.col("event_type") == "task_completed", 1).otherwise(0)).alias("task_completions"),
            F.sum(F.when(F.col("event_type") == "document_uploaded", 1).otherwise(0)).alias("document_uploads"),
            F.max("timestamp").alias("last_event_timestamp"),
            F.countDistinct("user_id").alias("unique_users"),
            F.countDistinct("event_type").alias("unique_event_types"),
        )
        .orderBy(F.col("total_events").desc())
    )


def user_activity_summary(df: DataFrame) -> DataFrame:
    return (
        df.groupBy("user_id")
        .agg(
            F.sum(F.when(F.col("event_type") == "login", 1).otherwise(0)).alias("login_count"),
            F.sum(F.when(F.col("event_type") == "logout", 1).otherwise(0)).alias("logout_count"),
            F.sum(
                F.when(~F.col("event_type").isin("login", "logout"), 1).otherwise(0)
            ).alias("actions_taken"),
            F.countDistinct(F.when(F.col("project_id").isNotNull(), F.col("project_id"))).alias("projects_touched"),
            F.min("timestamp").alias("first_active"),
            F.max("timestamp").alias("last_active"),
            F.countDistinct("event_date").alias("active_days"),
        )
        .orderBy(F.col("last_active").desc())
    )


def escalation_log(df: DataFrame) -> DataFrame:
    raised = (
        df.where(F.col("event_type") == "escalation_raised")
        .select(
            F.col("event_id").alias("event_id"),
            "project_id",
            F.col("user_id").alias("raised_by"),
            F.col("timestamp").alias("raised_at"),
            F.col("payload").getItem("severity").alias("severity"),
        )
    )
    resolved = (
        df.where(F.col("event_type") == "escalation_resolved")
        .select(
            "project_id",
            F.col("user_id").alias("resolved_by"),
            F.col("timestamp").alias("resolved_at"),
            F.col("payload").getItem("resolved_by").alias("payload_resolved_by"),
        )
    )
    raised_events = raised.alias("raised")
    resolved_events = resolved.alias("resolved")
    candidates = raised_events.join(
        resolved_events,
        (F.col("raised.project_id") == F.col("resolved.project_id"))
        & (F.col("resolved.resolved_at") > F.col("raised.raised_at")),
        "left",
    ).select(
        F.col("raised.event_id").alias("event_id"),
        F.col("raised.project_id").alias("project_id"),
        F.col("raised.raised_by").alias("raised_by"),
        F.col("raised.raised_at").alias("raised_at"),
        F.col("raised.severity").alias("severity"),
        F.col("resolved.resolved_by").alias("resolved_by"),
        F.col("resolved.payload_resolved_by").alias("payload_resolved_by"),
        F.col("resolved.resolved_at").alias("resolved_at"),
    )
    nearest_resolution = Window.partitionBy("event_id").orderBy(F.col("resolved_at").asc_nulls_last())
    return (
        candidates.withColumn("resolution_rank", F.row_number().over(nearest_resolution))
        .where(F.col("resolution_rank") == 1)
        .withColumn("resolved", F.col("resolved_at").isNotNull())
        .withColumn(
            "resolved_by",
            F.coalesce(F.col("payload_resolved_by"), F.col("resolved_by")),
        )
        .withColumn(
            "resolution_time_hours",
            (F.col("resolved_at").cast("long") - F.col("raised_at").cast("long")) / F.lit(3600.0),
        )
        .select(
            "event_id",
            "project_id",
            "raised_by",
            "raised_at",
            "severity",
            "resolved",
            "resolved_by",
            "resolved_at",
            "resolution_time_hours",
        )
        .orderBy("raised_at")
    )


def daily_event_volume(df: DataFrame) -> DataFrame:
    daily = df.groupBy("event_date", "event_type").agg(F.count("*").alias("event_count"))
    cumulative_window = (
        Window.partitionBy("event_type")
        .orderBy("event_date")
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    )
    return (
        daily.withColumn("cumulative_count", F.sum("event_count").over(cumulative_window))
        .orderBy(F.col("event_date").asc(), F.col("event_count").desc())
    )


def peak_usage_analysis(df: DataFrame) -> DataFrame:
    return (
        df.groupBy("event_date", "event_hour")
        .agg(
            F.count("*").alias("total_events"),
            F.countDistinct("user_id").alias("unique_users"),
            F.countDistinct("event_type").alias("event_types_per_hour"),
        )
        .orderBy(F.col("total_events").desc())
        .limit(20)
    )


def write_parquet(df: DataFrame, name: str, partition_by: str | None = None) -> int:
    output_path = OUTPUT_DIR / name
    writer = df.coalesce(1).write.mode("overwrite").format("parquet")
    if partition_by:
        writer = writer.partitionBy(partition_by)
    writer.save(str(output_path))
    row_count = df.count()
    print(f"wrote {name}: {row_count} rows -> {output_path}")
    return row_count


def run_pipeline() -> None:
    started_at = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    spark = get_spark_session()
    try:
        raw = load_events(spark, EVENTS_DIR).cache()
        clean = validate_events(raw).cache()
        print(f"clean_events={clean.count()}")

        aggregations = [
            ("project_activity_summary", project_activity_summary(clean), None),
            ("user_activity_summary", user_activity_summary(clean), None),
            ("escalation_log", escalation_log(clean), "severity"),
            ("daily_event_volume", daily_event_volume(clean), "event_date"),
            ("peak_usage_analysis", peak_usage_analysis(clean), None),
        ]
        for name, dataframe, partition_by in aggregations:
            write_parquet(dataframe, name, partition_by)

        elapsed = time.perf_counter() - started_at
        print(f"total_seconds={elapsed:.3f}")
        print(f"events_processed_per_second={clean.count() / elapsed:.2f}")
    finally:
        spark.stop()


if __name__ == "__main__":
    run_pipeline()
