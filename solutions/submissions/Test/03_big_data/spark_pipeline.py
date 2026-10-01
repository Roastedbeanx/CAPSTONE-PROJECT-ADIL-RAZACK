#STEP 1: IMPORTS + SPARK SESSION

import os

# ✅ FORCE Java 17 for PySpark launcher
os.environ["JAVA_HOME"] = "/opt/homebrew/Cellar/openjdk@17/17.0.19/libexec/openjdk.jdk/Contents/Home"
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]

# Optional but safe
os.environ["HADOOP_USER_NAME"] = "spark"

from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.window import Window
import time


from pyspark.sql.functions import (
    col, count, countDistinct, sum, when,
    max, min, to_date, hour, date_format, row_number
)




import subprocess
print(subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT).decode())






import os

os.environ["HADOOP_USER_NAME"] = "spark"
os.environ["HADOOP_CONF_DIR"] = ""
os.environ["YARN_CONF_DIR"] = ""
os.environ["SPARK_DIST_CLASSPATH"] = ""





os.environ["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@11"




spark = SparkSession.builder \
    .master("local[*]") \
    .appName("Presight Events Processing") \
    .config("spark.driver.extraJavaOptions", "-Djava.io.tmpdir=/tmp") \
    .config("spark.executor.extraJavaOptions", "-Djava.io.tmpdir=/tmp") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()



spark.sparkContext.setLogLevel("ERROR")

#STEP 2: DEFINE SCHEMA (MANDATORY)

schema = StructType([
    StructField("event_id", StringType()),
    StructField("event_type", StringType()),
    StructField("user_id", StringType()),
    StructField("project_id", StringType()),
    StructField("timestamp", TimestampType()),
    StructField("payload", MapType(StringType(), StringType()))
])


#STEP 3: LOAD DATA  


start_time = time.time()




df = spark.read \
    .schema(schema) \
    .json("file:///Users/poonam.dixit/Documents/Poonam_Engineer_Assesment/stackup-engineering-academy_assessment/datasets/events_stream/events_2025_*.jsonl")

print(f"Total rows loaded: {df.count()}")



#STEP 4: CLEANING + VALIDATION
initial_count = df.count()

# Drop nulls
df = df.dropna(subset=["event_id", "user_id"])
after_null_drop = df.count()

print(f"Dropped null rows: {initial_count - after_null_drop}")

# Remove duplicates (keep latest)
window_spec = Window.partitionBy("event_id").orderBy(col("timestamp").desc())

df = df.withColumn("row_num", row_number().over(window_spec)) \
       .filter(col("row_num") == 1) \
       .drop("row_num")

after_dedup = df.count()
print(f"Removed duplicates: {after_null_drop - after_dedup}")


#STEP 5: ENRICH COLUMNS

df = df \
    .withColumn("event_date", to_date("timestamp")) \
    .withColumn("event_hour", hour("timestamp")) \
    .withColumn("event_month", date_format("timestamp", "yyyy-MM"))


#STEP 6: AGGREGATION 1 — project_activity_summary

project_summary = df.filter(col("project_id").isNotNull()) \
.groupBy("project_id") \
.agg(
    count("*").alias("total_events"),
    sum(when(col("event_type") == "escalation_raised", 1).otherwise(0)).alias("escalation_count"),
    sum(when(col("event_type") == "task_completed", 1).otherwise(0)).alias("task_completions"),
    sum(when(col("event_type") == "document_uploaded", 1).otherwise(0)).alias("document_uploads"),
    max("timestamp").alias("last_event_timestamp"),
    countDistinct("user_id").alias("unique_users"),
    countDistinct("event_type").alias("unique_event_types")
)

#STEP 7: AGGREGATION 2 — user_activity_summary


user_summary = df.groupBy("user_id").agg(
    sum(when(col("event_type") == "login", 1).otherwise(0)).alias("login_count"),
    sum(when(col("event_type") == "logout", 1).otherwise(0)).alias("logout_count"),
    sum(when(~col("event_type").isin("login", "logout"), 1).otherwise(0)).alias("actions_taken"),
    countDistinct("project_id").alias("projects_touched"),
    min("timestamp").alias("first_active"),
    max("timestamp").alias("last_active"),
    countDistinct("event_date").alias("active_days")
)


#STEP 8: AGGREGATION 3 — escalation_log

raised = df.filter(col("event_type") == "escalation_raised") \
    .select("event_id", "project_id", "timestamp", col("payload")["severity"].alias("severity"))

resolved = df.filter(col("event_type") == "escalation_resolved") \
    .select("project_id", "timestamp", col("payload")["resolved_by"].alias("resolved_by"))

escalation_log = raised.alias("r").join(
    resolved.alias("res"),
    on="project_id",
    how="left"
).select(
    col("r.event_id"),
    col("r.project_id"),
    col("r.timestamp").alias("raised_at"),
    col("res.timestamp").alias("resolved_at"),
    col("severity"),
    col("resolved_by"),
    ((col("res.timestamp").cast("long") - col("r.timestamp").cast("long")) / 3600).alias("resolution_time_hours"),
    when(col("res.timestamp").isNotNull(), True).otherwise(False).alias("resolved")
)


#STEP 9: AGGREGATION 4 — daily_event_volume
window_spec = Window.partitionBy("event_type").orderBy("event_date")

daily_volume = df.groupBy("event_date", "event_type") \
    .count() \
    .withColumnRenamed("count", "event_count") \
    .withColumn("cumulative_count", sum("event_count").over(window_spec))


#STEP 10: AGGREGATION 5 — peak_usage_analysis

peak_usage = df.groupBy("event_date", "event_hour").agg(
    count("*").alias("total_events"),
    countDistinct("user_id").alias("unique_users"),
    countDistinct("event_type").alias("event_types_per_hour")
).orderBy(col("total_events").desc()).limit(20)


#STEP 11: WRITE OUTPUTS (PARQUET)

project_summary.coalesce(1).write.mode("overwrite").parquet("outputs/results/Test/03/spark/project_activity_summary")
user_summary.coalesce(1).write.mode("overwrite").parquet("outputs/results/Test/03/spark/user_activity_summary")
escalation_log.write.mode("overwrite").partitionBy("severity").parquet("outputs/results/Test/03/spark/escalation_log")
daily_volume.write.mode("overwrite").partitionBy("event_date").parquet("outputs/results/Test/03/spark/daily_event_volume")
peak_usage.coalesce(1).write.mode("overwrite").parquet("outputs/results/Test/03/spark/peak_usage_analysis")


#STEP 12: PERFORMANCE METRICS

end_time = time.time()

total_time = round(end_time - start_time, 2)
total_rows = df.count()

events_per_sec = total_rows / total_time

print(f"Execution Time: {total_time} sec")
print(f"Rows Processed: {total_rows}")
print(f"Events/sec: {events_per_sec}")