import mysql.connector
from random import randint

# Get random samples from alibaba_item table and print their data
index = 10000
select_range = 2000
sample_size = 20
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='root',
    database='alibaba_scraper'
)
cursor = conn.cursor()

for i in range(sample_size):
    row_num = index + randint(0, 2000)
    cursor.execute(f"SELECT * FROM alibaba_item LIMIT {row_num - 1},1")
    row = cursor.fetchone()
    print(f"id: {row[0]}\nlink:{row[1]}\nname:{row[2]}\nprice:{row[3]}\nmin purchase: {row[4]}\ncountry: {row[5]}\n")
