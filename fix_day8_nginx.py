from pathlib import Path

content = """server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ws/ {
        proxy_pass http://voxera-backend:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    location /api/ {
        proxy_pass http://voxera-backend:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Authorization $http_authorization;
        proxy_pass_header Authorization;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        proxy_connect_timeout 30s;
    }
}
"""

Path("docker/nginx.conf").write_text(content, encoding="utf-8")
print("Wrote docker/nginx.conf with WebSocket passthrough")