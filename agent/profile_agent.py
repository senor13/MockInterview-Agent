import sys
from tools.search_company import company_search
from tools.parse_pdf import parse_pdf
from state.schema import CandidateProfile
#But this requires running from the project root. We'll set up proper imports later — for now note it as a known issue.
from agent.llm import call_llm
import json

def profile_extraction_agent(resume_text,JD_text):
    tools = [
        {
            "type" : "function",
            "function" : {
                "name" : "company_search_tool",
                "description" : "Given the JD of a company, the tool can be used to fetch further details about the company for which the candidiate is applying",
                "parameters" : {
                    "type" : "object",
                    "properties" : {
                        "company_name" : {
                            "type" : "string",
                            "description" : "Name of the company for which the candidate is applying"
                        }
                    },
                    "required" : ["company_name"]
                }
            }
        }  
    ]

    system_prompt_1 = """
    Your have access to candidate's resume and JD (Job Description) for which the candidate is going to apply. 
    Your job is to create a profile for the candidate basis the resume & the JD and output the candidate's profile.
    The final output should be the updated state & the company_info.
    Below is the resume & JD :
    RESUME = {resume_text}
    JD = {JD_text}
    """
    message1 = [{"role":"system","content":system_prompt_1.format(resume_text = resume_text,JD_text = JD_text)}]
    candidate_profile = call_llm(response_model = CandidateProfile ,messages = message1)

    system_prompt_2 = """
    Your have access to the JD (Job Description) and a company_search_tool 
    You can use the company_search tool for fetching details around the company or if you need to search for something mentioned in the JD
    The final output should be the company_info which would be helpful for conducting the interview for AI/ML engineer role
    Below is JD :
    JD = {JD_text}
    """
    message2 = []
    function_map = {"company_search_tool" : company_search}
    message2.append({"role":"system","content":system_prompt_2.format(JD_text = JD_text)})

    while True:
        response = call_llm(messages = message2, tools = tools)
        if response.tool_calls:
            tool_name = response.tool_calls[0].function.name
            arguments = json.loads(response.tool_calls[0].function.arguments)
            tool_result = function_map[tool_name](**arguments)
            message2.append({"role":"assistant","content":None, "tool_calls": [response.tool_calls[0]]})
            message2.append({"role":"tool","content":tool_result,"tool_call_id":response.tool_calls[0].id})
        else:
            company_info = response.content
            return candidate_profile,company_info



