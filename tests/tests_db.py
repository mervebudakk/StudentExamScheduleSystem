from student_system.core.database import fetch_one
print(fetch_one("SELECT current_database(), current_user, inet_client_addr(), NOW();"))
