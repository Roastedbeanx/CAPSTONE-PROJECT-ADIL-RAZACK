"""Pillar 3 Task 3.2: Kafka producer, consumer, and escalation forwarding."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from kafka import KafkaAdminClient, KafkaConsumer, KafkaProducer
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError


PROJECT_ROOT = Path(__file__).resolve().parents[4]
EVENTS_FILE = Path(
    os.getenv("EVENTS_FILE", PROJECT_ROOT / "datasets" / "events_stream" / "events_2025_01.jsonl")
)
OUTPUT_DIR = Path(
    os.getenv(
        "OUTPUT_DIR",
        PROJECT_ROOT / "outputs" / "results" / "adil_razack" / "03_big_data" / "kafka",
    )
)
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC_EVENTS = "presight.project.events"
TOPIC_ESCALATIONS = "presight.escalations.critical"
CONSUMER_GROUP = "presight-assessment-consumer"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def create_topics() -> None:
    """Create the two required topics, tolerating existing topics."""
    admin = KafkaAdminClient(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        client_id="presight-assessment-admin",
        request_timeout_ms=10000,
    )
    try:
        topics = [
            NewTopic(TOPIC_EVENTS, num_partitions=3, replication_factor=1),
            NewTopic(TOPIC_ESCALATIONS, num_partitions=1, replication_factor=1),
        ]
        try:
            admin.create_topics(new_topics=topics, validate_only=False)
            logger.info("Created Kafka topics: %s, %s", TOPIC_EVENTS, TOPIC_ESCALATIONS)
        except TopicAlreadyExistsError:
            logger.info("Kafka topics already exist")
    finally:
        admin.close()


def build_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        key_serializer=lambda value: value.encode("utf-8"),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        request_timeout_ms=10000,
        retries=3,
    )


def run_producer(
    producer: KafkaProducer,
    events_file: Path = EVENTS_FILE,
    delay_seconds: float = 0.05,
) -> int:
    """Send January JSONL events keyed by event type."""
    sent_count = 0
    started_at = time.perf_counter()
    with events_file.open(encoding="utf-8") as source_file:
        for line in source_file:
            event = json.loads(line)
            event["produced_at"] = datetime.now(timezone.utc).isoformat()
            producer.send(TOPIC_EVENTS, key=event["event_type"], value=event)
            sent_count += 1
            if sent_count % 100 == 0:
                logger.info("Produced %d messages", sent_count)
            time.sleep(delay_seconds)
    producer.flush()
    producer.close()
    elapsed = time.perf_counter() - started_at
    logger.info("Producer complete: %d messages in %.2f seconds", sent_count, elapsed)
    return sent_count


def build_consumer(topic: str = TOPIC_EVENTS) -> KafkaConsumer:
    return KafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=CONSUMER_GROUP,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        consumer_timeout_ms=10000,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def run_consumer(consumer: KafkaConsumer) -> dict:
    """Consume all available events and forward critical escalations."""
    summary = Counter()
    consumed_count = 0
    forwarded_count = 0
    started_at = time.perf_counter()
    forwarding_producer = build_producer()
    try:
        for message in consumer:
            event = message.value
            event_type = event.get("event_type", "unknown")
            summary[event_type] += 1
            consumed_count += 1
            if consumed_count % 100 == 0:
                logger.info(
                    "Consumed %d messages; latest=%s project=%s",
                    consumed_count,
                    event.get("event_id"),
                    event.get("project_id"),
                )

            payload = event.get("payload") or {}
            if event_type == "escalation_raised" and payload.get("severity") == "Critical":
                forwarding_producer.send(TOPIC_ESCALATIONS, key="Critical", value=event)
                forwarded_count += 1
    finally:
        forwarding_producer.flush()
        forwarding_producer.close()
        consumer.close()

    elapsed = time.perf_counter() - started_at
    result = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "topic": TOPIC_EVENTS,
        "total_messages_consumed": consumed_count,
        "event_counts": dict(summary),
        "critical_escalations_forwarded": forwarded_count,
        "throughput_messages_per_second": round(consumed_count / elapsed, 2) if elapsed else 0.0,
        "elapsed_seconds": round(elapsed, 3),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = OUTPUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info("Consumer complete: %s", summary_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Presight Kafka streaming pipeline")
    parser.add_argument("--mode", choices=["producer", "consumer", "both"], default="both")
    parser.add_argument("--delay-seconds", type=float, default=0.05)
    args = parser.parse_args()

    create_topics()
    if args.mode in {"producer", "both"}:
        run_producer(build_producer(), delay_seconds=args.delay_seconds)
    if args.mode in {"consumer", "both"}:
        result = run_consumer(build_consumer())
        logger.info("Event summary: %s", json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
