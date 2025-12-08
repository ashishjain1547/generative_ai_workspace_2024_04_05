
import os
import re


INPUT_FILE = "ab_time_oracle.sql"
OUTPUT_FILE = "ab_time_sqlite.sql"

script_dir = os.path.dirname(__file__)  # Get the directory of the script
file_path = os.path.join(script_dir, INPUT_FILE)

with open(file_path, mode='r') as f:
    ab_orders_sql = f.read()

# Convert the SQL statements to be SQLite compatible
sqlite_compatible_sql = []
for line in ab_orders_sql.splitlines():
    if line.startswith('Insert'):
        print(line)
        
        # Match the date in the format to_date('31-DEC-95','DD-MON-RR')
        match = re.search(r"to_date\('(\d{2})-(\w{3})-(\d{2})','DD-MON-RR'\)", line)
        print(match)

        if match:
            day, month, year = match.groups()
        
            line = line.replace(match.group(0), f"19{year}, '{month}', {day}")
            print(line)
            
        
        match = re.search(r'END_DATE', line)
        if match:
            line = line.replace('END_DATE', 'END_YEAR, END_MONTH, END_DAY')
            
        sqlite_compatible_sql.append(line)

# Print the converted SQL statements
for sql in sqlite_compatible_sql:
    print(sql)

with open(os.path.join(script_dir, OUTPUT_FILE), mode='w') as f:
    f.write('\n'.join(sqlite_compatible_sql))