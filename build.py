import os
import zipfile
import requests
from google import genai

# 1. Download data.csv directly inside GitHub's cloud (0 mobile data used)
csv_url = "YOUR_DATA_CSV_URL_HERE"
response = requests.get(csv_url)
with open("data.csv", "wb") as f:
    f.write(response.content)

# 2. Run Gemini API directly from cloud to cloud
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
result = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents="Process this data and build the 10 empire configs: " + response.text[:10000]
)

with open("result.txt", "w") as f:
    f.write(result.text)

# 3. Compress files in the cloud
with zipfile.ZipFile("output.zip", "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write("data.csv")
    zf.write("result.txt")

print("Done! All heavy work finished in the cloud.")
