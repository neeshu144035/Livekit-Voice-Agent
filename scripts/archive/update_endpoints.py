
with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update all endpoints with /api prefix
content = content.replace('@app.get("/phone-numbers', '@app.get("/api/phone-numbers')
content = content.replace('@app.post("/phone-numbers', '@app.post("/api/phone-numbers')
content = content.replace('@app.patch("/phone-numbers', '@app.patch("/api/phone-numbers')
content = content.replace('@app.delete("/phone-numbers', '@app.delete("/api/phone-numbers')
content = content.replace('@app.get("/agents', '@app.get("/api/agents')
content = content.replace('@app.post("/agents', '@app.post("/api/agents')
content = content.replace('@app.patch("/agents', '@app.patch("/api/agents')
content = content.replace('@app.delete("/agents', '@app.delete("/api/agents')
content = content.replace('@app.get("/token', '@app.get("/api/token')
content = content.replace('@app.get("/analytics', '@app.get("/api/analytics')
content = content.replace('@app.post("/calls', '@app.post("/api/calls')
content = content.replace('@app.get("/webhooks', '@app.get("/api/webhooks')

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Endpoints updated successfully')
