from server import db, load_connections, save_connection
print(load_connections())
save_connection({"id": "REQ_001", "student_id": "test", "alumni_id": "ALUM_001", "message": "hello"})
print(load_connections())
