from pathlib import Path

content = """server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://voxera-backend:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Authorization $http_authorization;
        proxy_pass_header Authorization;
    }
}
"""

p = Path("docker/nginx.conf")
p.write_text(content, encoding="utf-8")  # no BOM
print("Wrote", p)

# verify no BOM
raw = p.read_bytes()[:6]
print("First bytes:", raw.hex(" "))
if raw[:3] == b"\xef\xbb\xbf":
    print("WARNING: file still has BOM")
else:
    print("OK: no BOM")