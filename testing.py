import snowflake.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
print("SNOWFLAKE_USER:", os.getenv('SNOWFLAKE_USER'))
print("SNOWFLAKE_PASSWORD:", os.getenv('SNOWFLAKE_PASSWORD'))
print("SNOWFLAKE_ACCOUNT:", os.getenv('SNOWFLAKE_ACCOUNT'))
print("SNOWFLAKE_DATABASE:", os.getenv('SNOWFLAKE_DATABASE'))
print("SNOWFLAKE_SCHEMA:", os.getenv('SNOWFLAKE_SCHEMA'))
print("SNOWFLAKE_WAREHOUSE:", os.getenv('SNOWFLAKE_WAREHOUSE'))

conn = snowflake.connector.connect(
    user=os.getenv('SNOWFLAKE_USER'),
    password=os.getenv('SNOWFLAKE_PASSWORD'),
    account=os.getenv('SNOWFLAKE_ACCOUNT'),
    database=os.getenv('SNOWFLAKE_DATABASE'),
    schema=os.getenv('SNOWFLAKE_SCHEMA'),
    warehouse=os.getenv('SNOWFLAKE_WAREHOUSE')
)

cursor = conn.cursor()

try:
    # Test Query
    cursor.execute("SELECT CURRENT_VERSION()")
    result = cursor.fetchone()
    print(f"Connected to Snowflake! Version: {result[0]}")  # Should print Snowflake version

except Exception as e:
    print(f"Connection failed: {e}")

finally:
    cursor.close()
    conn.close()