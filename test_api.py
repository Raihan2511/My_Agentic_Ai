import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv() 
api_url = os.getenv("UNITIME_API_URL")
username = os.getenv("UNITIME_USERNAME")
password = os.getenv("UNITIME_PASSWORD")

# --- CORRECTED XML Data for UPDATE ---
# This now matches the correct structure you provided
# It uses action="update" and I've changed the title for testing.
sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<offerings campus="woebegon" year="2010" term="Fal" dateFormat="yyyy/M/d" timeFormat="HHmm" created="Sat Oct 18 19:33:17 CEST 2025" includeExams="none">
  <offering id="132371" offered="true" action="update">
    <course id="684737" subject="DLCS" courseNbr="101" controlling="true" title="DLCS_101 Updated"/>
    <config name="1" limit="25">
      <subpart type="Lab" suffix="" minPerWeek="50"/>
      <class id="DLCS 10 Lab L1" type="Lab" suffix="L1" limit="25" studentScheduling="true" displayInScheduleBook="true" cancelled="false" managingDept="0100">
        <time days="MWF" startTime="0830" endTime="0920" timePattern="2 x 50"/>
        <room building="EDUC" roomNbr="106"/>
      </class>
    </config>
  </offering>
</offerings>
"""

# --- Check Config ---
if not api_url or not username or not password:
    print("❌ ERROR: Missing UNITIME_API_URL, UNITIME_USERNAME, or UNITIME_PASSWORD in .env file.")
    exit()

# --- Set Headers ---
headers = {
    "Content-Type": "application/xml;charset=UTF-8" 
}

# --- Make the Request (Copied from your tool) ---
try:
    print(f"--- ATTEMPTING TO POST XML TO {api_url} using Basic Auth ---")
    
    response = requests.post(
        api_url, 
        data=sample_xml.encode('utf-8'), 
        headers=headers,
        auth=HTTPBasicAuth(username, password) 
    )
    
    print(f"✅ Received HTTP status code: {response.status_code}")
    print(f"✅ Response Content-Type: {response.headers.get('Content-Type', 'N/A')}")

    response.raise_for_status() # Check for HTTP errors 
    
    if "text/html" in response.headers.get("Content-Type", ""):
          print("\n✅ Successfully imported data. Server returned HTML response.")
          # You should see the log from the server in the response text
          print(f"Server response:\n{response.text}") 
    else:
          print("\n✅ Successfully imported data.")
          print(f"Server response:\n{response.text}")

except requests.exceptions.HTTPError as http_err:
    print(f"\n❌ ERROR: HTTP error occurred: {http_err}")
    print(f"Response Body:\n{http_err.response.text}")
except requests.exceptions.RequestException as req_err:
    print(f"\n❌ ERROR: Network request error occurred: {req_err}")

finally:
    print("\n--- API Test Finished ---")