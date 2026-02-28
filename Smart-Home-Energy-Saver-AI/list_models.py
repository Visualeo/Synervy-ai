import google.generativeai as genai

genai.configure(api_key="AIzaSyCMNAqg5PNQA5m09cyJDYepoOuDLbShy0s")

print("Available Models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
