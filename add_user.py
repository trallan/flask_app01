import sys
import sqlite3
from werkzeug.security import generate_password_hash  # Assuming you're using Werkzeug for password hashing

def add_user(username, plain_password, role):
    hashed_password = generate_password_hash(plain_password)
    conn = sqlite3.connect('/home/pigcat/person.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
              (username, hashed_password, role))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # Check if proper arguments are passed
    if len(sys.argv) != 4:
        print("Usage: python3 add_user.py <username> <password> <role>")
        sys.exit(1)

    username = sys.argv[1]
    plain_password = sys.argv[2]
    role = sys.argv[3]

    add_user(username, plain_password, role)
    print(f"User '{username}' added successfully!")
