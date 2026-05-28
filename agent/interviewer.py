
from agent.llm import call_llm
import json
from state.schema import InterviewState , CandidateLiveSignal , SessionMeta
from config import PROMPT_VERSION
from datetime import datetime
import uuid
from tools.guardrails import check_input
from agent.evaluator import eval_agent


def interview_agent(resume_text,JD_text,company_info,candidate_profile): #these arguments will come from a different LLM call which we are calling profile extraction agent
    with open("prompts/system_v0.1.0.md","r") as p:
        system_prompt = p.read() 
    conversation_history = []
    turns = 0
    interview_complete = False
    interview_state = InterviewState(no_of_turns = 0, topics_covered = [], current_topic = None)

    ## initialize session state
    session_state = SessionMeta(session_id = str(uuid.uuid4()),started_at = datetime.now().isoformat(),prompt_version = PROMPT_VERSION)
    ##

    ## update system prompt variables
    static_system_prompt = [{"role":"system","content":system_prompt.format(resume_text = resume_text,jd_text = JD_text, candidate_profile = candidate_profile)}]
    ##

    ##start interview
    while turns <= 15 and not interview_complete:
        interview_state = interview_state.model_copy(update={"no_of_turns": turns})
        message = static_system_prompt + [{"role":"system","content": f"current interview state : {interview_state.model_dump_json()}"}] + conversation_history
               # {"role":"user","content": CandidateLiveSignal} for later
        llm_response = call_llm(messages = message)
        print(llm_response.content)
        conversation_history.append({"role":"assistant","content":llm_response.content})
        if "INTERVIEW_COMPLETE" in llm_response.content:
            interview_complete = True
        else:
            turns += 1
            candidate_response = input("please enter your response: ")
            check_response = check_input(candidate_response)
            invalid_attempts = 0
            while not check_response.safe:
                invalid_attempts += 1
                if invalid_attempts >= 3:
                    print("too many invalid inputs. Ending the interview")
                    return conversation_history
                print(f"Invalid response : {check_response.reason}")
                print("re-enter the repsonse")
                candidate_response = input("please enter your response: ")
                check_response = check_input(candidate_response)
            
            conversation_history.append({"role":"user","content":candidate_response})
                ##update the candidate live signal -> via LLM
    ## call llm to genrate the report -> a diff system prompt will be used to generating the report
    candidate_report, interview_eval = eval_agent(conversation_history = conversation_history,resume_text =  resume_text, jd_text = JD_text, system_prompt = system_prompt)
    return candidate_report,interview_eval
            


                
            

