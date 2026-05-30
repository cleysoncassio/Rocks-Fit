import base64
from google import genai
from google.genai import types

client = genai.Client(api_key="AIzaSyAFrByGIzSZRKpPl4peEK0GAB2zLp3srTo")
# 1x1 pixel base64 image
b64_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
imagem = types.Part.from_bytes(data=base64.b64decode(b64_data), mime_type='image/png')

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=["O que tem nessa imagem?", imagem]
)
print(response.text)
