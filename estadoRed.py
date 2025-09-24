import requests, certifi

url = "https://cumbresanramon.cl/socket.io/?EIO=4&transport=polling"
r = requests.get(url, verify=certifi.where())
print("✅ Conectado:", r.text[:100])
