import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# --- Load Environment Variables ---
# Make sure your .env file is in the same directory or accessible
load_dotenv() 
api_url = os.getenv("UNITIME_API_URL")
username = os.getenv("UNITIME_USERNAME")
password = os.getenv("UNITIME_PASSWORD")

# --- Sample XML Data ---
# (Replace this with the actual XML your agent generated if you prefer)
sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<offerings campus="woebegon" year="2010" term="Fal" dateFormat="yyyy/M/d" timeFormat="HHmm" created="Sat Oct 18 19:33:17 CEST 2025" includeExams="none">
  <offering id="132371" offered="true" action="insert">
    <course id="959474" subject="DLCS" courseNbr="10" controlling="true" title="DLCS_10"/>
    <config name="1" limit="25">
      <subpart type="Lab" suffix="" minPerWeek="50"/>
      <class id="DLCS 10 Lab L1" type="Lab" suffix="L1" limit="25" studentScheduling="true" displayInScheduleBook="true" cancelled="false" managingDept="0100">
        <time days="Monday" startTime="08:30" endTime="0920" timePattern="1 x 50"/>
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
         # Optionally print a snippet of the HTML if needed
         # print(f"HTML Snippet:\n{response.text[:500]}...") 
    else:
        print("\n✅ Successfully imported data.")
        print(f"Server response:\n{response.text}")

except requests.exceptions.HTTPError as http_err:
    print(f"\n❌ ERROR: HTTP error occurred: {http_err}")
    print(f"Response Body:\n{http_err.response.text}")
except requests.exceptions.RequestException as req_err:
    print(f"\n❌ ERROR: Network request error occurred: {req_err}")
    # This will catch "Connection Refused" etc.

finally:
    print("\n--- API Test Finished ---")