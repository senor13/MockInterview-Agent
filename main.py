from agent.llm import call_llm
from agent.profile_agent import profile_extraction_agent
from tools.parse_pdf import parse_pdf
from agent.interviewer import interview_agent
from tools.guardrails import check_input

resume_input = "/Users/sagrikasrivastav/Desktop/AI/Interview-Agent/tools/Piyush Garg resume Februrary.pdf"
with open("sample_jd.txt","r") as f:
    JD_text = f.read()

resume_text = parse_pdf(resume_input)

resume_check = check_input(resume_text)
JD_check = check_input(JD_text)
if not resume_check.safe:
    print(f"Invalid Input : {resume_check.reason}")
    print(f"please re-enter the resume")

elif not JD_check.safe:
    print(f"Invalid Input : {JD_check.reason}")
    print(f"please re-enter the JD")

else:

    candidate_profile,company_info = profile_extraction_agent(resume_text,JD_text)

    candidate_report,interview_eval = interview_agent(resume_text = resume_text,JD_text = JD_text,company_info = company_info ,candidate_profile = candidate_profile)

    print(candidate_profile)
    print("\n\n")
    print(company_info)
    print("\n\n")
    print(f"candidate_report : \n\n {candidate_report}  \n\n Interview_eval : \n\n {interview_eval}")