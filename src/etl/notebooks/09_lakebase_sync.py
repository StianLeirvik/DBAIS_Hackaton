# Databricks notebook source
tables = [t.name for t in spark.catalog.listTables("workspace.caremap")]
df_map = {table: spark.table(f"workspace.caremap.{table}") for table in tables}

# COMMAND ----------

# PostgreSQL connection details
host = "ep-broad-heart-d8y2wfnw.database.us-east-2.cloud.databricks.com"
port = "5432"
database = "databricks_postgres"
user = "dais_master"
password = "REPLACE_WITH_PASS"

for table_name, df in df_map.items():
    df.write \
        .format("postgresql") \
        .mode("overwrite") \
        .option("host", host) \
        .option("port", port) \
        .option("database", database) \
        .option("user", user) \
        .option("password", password) \
        .option("dbtable", f"caremap.{table_name}") \
        .save()
