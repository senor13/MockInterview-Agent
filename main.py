from agent.llm import call_llm
from agent.profile_agent import profile_extraction_agent
from tools.parse_pdf import parse_pdf
from agent.interviewer import interview_agent

resume_input = "/Users/sagrikasrivastav/Desktop/AI/Interview-Agent/tools/Piyush Garg resume Februrary.pdf"
with open("sample_jd.txt","r") as f:
    JD_text = f.read()

resume_text = parse_pdf(resume_input)

candidate_profile,company_info = profile_extraction_agent(resume_text,JD_text)

conversation_history = interview_agent(resume_text = resume_text,JD_text = JD_text,company_info = company_info ,candidate_profile = candidate_profile)

print(candidate_profile)
print("\n\n")
print(company_info)
print("\n\n")
print(conversation_history)

