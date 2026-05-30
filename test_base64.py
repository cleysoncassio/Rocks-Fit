import requests, json

msg = {
    "key": {
      "remoteJid": "558491424877@s.whatsapp.net",
      "fromMe": False,
      "id": "3EB007A7F8763CB15EA820"
    },
    "message": {
      "audioMessage": {
        "url": "https://mmg.whatsapp.net/v/t62.7114-24/31697380_971358357732298_2408013145899933005_n.enc"
      }
    }
}

headers = {"apikey": "5961FD6698B6-4EFE-9540-2303EE0FB31F", "Content-Type": "application/json"}
response = requests.post("http://localhost:8080/chat/getBase64FromMediaMessage/API-Evolution", headers=headers, json={"message": msg})
print(response.status_code)
print(response.text[:200])
