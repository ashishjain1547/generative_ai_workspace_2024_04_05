
import os
import re


INPUT_FILE = "ab_orders_oracle.sql"
OUTPUT_FILE = "ab_time_sqlite.sql"

script_dir = os.path.dirname(__file__)  # Get the directory of the script
file_path = os.path.join(script_dir, INPUT_FILE)

with open(file_path, mode='r') as f:
    ab_orders_sql = f.read()

# Convert the SQL statements to be SQLite compatible
sqlite_compatible_sql = []
for line in ab_orders_sql.splitlines():
    if line.startswith('insert'):

        # Match the date in the format to_date('MM/DD/YYYY','MM-DD-YYYY')
        match = re.search(r"to_date\('(\d{2})/(\d{2})/(\d{4})','MM-DD-YYYY'\)", line)
        if match:
            month, day, year = match.groups()
        
            line = line.replace(match.group(0), f"{year}, {month}, {day}")
            sqlite_compatible_sql.append(line)

# Print the converted SQL statements
for sql in sqlite_compatible_sql:
    print(sql)

with open(os.path.join(script_dir, OUTPUT_FILE), mode='w') as f:
    f.write('\n'.join(sqlite_compatible_sql))