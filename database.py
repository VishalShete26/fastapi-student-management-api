import psycopg2

conn = psycopg2.connect(
    host = "localhost",
    database = "students",
    user = "postgres",
    password = "admin",
    port = "5432"
)

print("Database is connected successfully.!")


cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) NOT NULL,
        age INTEGER DEFAULT 0
        )    
""")

conn.commit()
cur.close()

print("student table created successfully.!")