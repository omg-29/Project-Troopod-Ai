from google import genai

client = genai.Client(api_key="AIzaSyCR9FaPBa_rxH27pjSYeb_3ZqGCecwSmuA")
try:
    models = client.models.list()
    for m in models:
        print(f"Name: {m.name}, DisplayName: {m.display_name}")
except Exception as e:
    print(f"Error fetching models: {e}")
