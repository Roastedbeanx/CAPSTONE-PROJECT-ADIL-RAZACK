#STEP 1: IMPORTS

from kafka import KafkaProducer, KafkaConsumer
import json
import time
from datetime import datetime
import os
from collections import defaultdict

#STEP 2: KAFKA CONFIG
KAFKA_BROKER = "localhost:9092"

EVENT_TOPIC = "presight.project.events"
ESCALATION_TOPIC = "presight.escalations.critical"



#STEP 4: PRODUCER
def run_producer():

    print("Starting Producer...")

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8")
    )

    count = 0

    with open("datasets/events_stream/events_2025_01.jsonl") as f:
        for line in f:
            event = json.loads(line)

            # ✅ add produced_at
            event["produced_at"] = datetime.utcnow().isoformat()

            key = event.get("event_type", "unknown")

            producer.send(
                EVENT_TOPIC,
                key=key,
                value=event
            )

            count += 1

            # log every 100 messages
            if count % 100 == 0:
                print(f"Produced {count} messages")

            time.sleep(0.05)   # simulate streaming

    producer.flush()
    print(f"Producer finished. Total sent: {count}")


#STEP 5: CONSUMER + FORWARDING

def run_consumer():

    print("Starting Consumer...")

    consumer = KafkaConsumer(
        EVENT_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda x: json.loads(x.decode("utf-8"))
    )

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    count = 0
    forwarded = 0
    event_counts = defaultdict(int)

    start_time = time.time()

    for msg in consumer:

        event = msg.value

        count += 1

        event_type = event.get("event_type")
        event_counts[event_type] += 1

        # log every 100 messages
        if count % 100 == 0:
            print(f"Consumed {count} messages")

        # ✅ escalation forwarding logic
        if event_type == "escalation_raised":
            payload = event.get("payload", {})
            severity = payload.get("severity")

            if severity == "Critical":
                producer.send(ESCALATION_TOPIC, value=event)
                forwarded += 1

        # STOP after one file processed (~8300)
        if count >= 8300:
            break

    end_time = time.time()
    duration = round(end_time - start_time, 2)

    print("Consumer finished")
    print(f"Total consumed: {count}")
    print(f"Forwarded critical escalations: {forwarded}")

    write_summary(count, event_counts, forwarded, duration)


#STEP 6: SUMMARY OUTPUT
def write_summary(total, event_counts, forwarded, duration):

    os.makedirs("outputs/kafka", exist_ok=True)

    summary = {
        "run_timestamp": datetime.now().isoformat(),
        "total_messages_consumed": total,
        "event_type_counts": dict(event_counts),
        "critical_escalations_forwarded": forwarded,
        "throughput_msgs_per_sec": round(total / duration, 2),
        "execution_time_sec": duration
    }

    with open("outputs/results/Test/03/kafka/summary.json", "w") as f:
        json.dump(summary, f, indent=4)

    print("Kafka summary written to outputs/kafka/summary.json")

#STEP 7: MAIN FUNCTION
if __name__ == "__main__":

    # Run producer first
    run_producer()

    # Then run consumer
    run_consumer()
