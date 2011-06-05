
.PHONY: certs

certs: ca.pem client.pem client-key.pem server.pem server-key.pem

ca.pem ca-key.pem: openssl-ca.cnf
	openssl req -config openssl-ca.cnf -new -x509 -nodes -keyout ca-key.pem -out ca.pem -days 3650

client-req.pem client-key.pem: openssl-client.cnf
	openssl req -config openssl-client.cnf -new -nodes -keyout client-key.pem -out client-req.pem -days 3650

client.pem: client-req.pem ca.pem ca-key.pem
	openssl x509 -extfile openssl-client.cnf -extensions v3_req -req -in client-req.pem -CA ca.pem -CAkey ca-key.pem -set_serial 1 -days 3650 -out client.pem

server-req.pem server-key.pem: openssl-server.cnf
	openssl req -config openssl-server.cnf -new -nodes -keyout server-key.pem -out server-req.pem -days 3650

server.pem: server-req.pem ca.pem ca-key.pem
	openssl x509 -extfile openssl-server.cnf -extensions v3_req -req -in server-req.pem -CA ca.pem -CAkey ca-key.pem -set_serial 2 -days 3650 -out server.pem

