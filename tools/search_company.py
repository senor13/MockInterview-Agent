from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()
client = TavilyClient(api_key = os.environ["TAVILY_API_KEY"])

def company_search(company_name):
    results = client.search(company_name,max_results = 3)
    content = " ".join([r["content"] for r in results["results"]])
    return content
