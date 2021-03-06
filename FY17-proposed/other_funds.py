from csv import writer as csv_writer

from xlrd import open_workbook

from constants import FUNDS, CLASS_NAMES
from clean_departments import CleanDepartments
from util import aggregate_similar_rows

DEPARTMENTS_FILE_PATH = './departments.yml'
OUTPUT_FILE_NAME = './output/other-funds.csv'

def int_or_zero(str):
  if str: return int(str)
  else: return 0

def index_where_starts_with(rows, column_index, needle):
  for row_index, row in enumerate(rows):
    if rows[column_index] and row[column_index].startswith(needle):
      return row_index
  return -1

def construct_dept_rows(fund, dept, row):
  dept_rows = []

  if row[u'CLASS 100'] or row[u'PENSIONS'] or row[u'OTHER FB']:
    total_class_100 = int_or_zero(row[u'CLASS 100']) + int_or_zero(row[u'PENSIONS']) + int_or_zero(row[u'OTHER FB'])
    dept_rows.append(['2017', fund, dept, 100, CLASS_NAMES['100'], total_class_100])
  if row[u'CLASS 300'] or row[u'CLASS 400']:
    total_class_300 = int_or_zero(row[u'CLASS 300']) + int_or_zero(row[u'CLASS 400'])
    dept_rows.append(['2017', fund, dept, 300, CLASS_NAMES['300'], total_class_300])

  for key in ['200', '500', '700', '800', '900']:
    if row.get(u'CLASS ' + key):
      dept_rows.append(['2017', fund, dept, key, CLASS_NAMES[key], row[u'CLASS ' + key]])

  return dept_rows

# Load departments and their matches
departments = CleanDepartments(DEPARTMENTS_FILE_PATH)

new_rows = []

for fund in FUNDS:
  workbook = open_workbook(fund['input'])
  sheet = workbook.sheet_by_name(fund['sheet'])

  # Convert rows to list
  rows = []
  for row_index in range(sheet.nrows):
    rows.append(sheet.row_values(row_index))

  # Remove unneeded rows at top
  rows = rows[4:]

  # Only keep columns A and C through K
  rows = [[row[0]] + row[2:12] for row in rows]

  # Remove empty rows
  rows = [row for row in rows if any(row)]
  
  # Remove rows from "TOTAL XX FUND" and after
  total_row_index = index_where_starts_with(rows, 0, 'TOTAL')
  rows = rows[:total_row_index]

  # Convert list of lists to list of dicts
  keys = rows[0]
  rows = rows[1:]
  rows = [dict(zip(keys, row)) for row in rows]

  # Convert "department sections" to individual department rows using FY17 amount
  fund_rows = []
  current_dept = ''
  for row in rows:
    label = row[u'Department']

    if label.startswith('FY17'):
      new_rows = new_rows + construct_dept_rows(fund['name'], current_dept, row)
    elif not label.startswith('FY16') and not label.startswith('INCREASE') and not label.startswith('TOTAL'):
      current_dept = departments.clean(label)

# Group rows by everything but total and aggregate the total (sum)
new_rows = aggregate_similar_rows(new_rows, 5)

# Sort rows for idempotency
new_rows.sort()

header = ['Fiscal Year', 'Fund', 'Department', 'Class ID', 'Class', 'Total']

with open(OUTPUT_FILE_NAME, 'wb') as f:
  writer = csv_writer(f)
  writer.writerow(header)
  writer.writerows(new_rows)

print('Wrote {0} rows to {1}'.format(len(new_rows), OUTPUT_FILE_NAME))
