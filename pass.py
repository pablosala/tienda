from werkzeug.security import generate_password_hash

password = "admin"
hashed_password = generate_password_hash(password)
print(hashed_password)
#insert into usuario (nombre, email, password_hash, role) values ('admin','admin@example.com','pbkdf2:sha256:600000$NWbcSDgiTyPzwUzw$0e01cb60b57aed64b398bc14a9cdb88c5169638f16de777d3c0d1e8c448abc21','admin')
