## for per session judgemnet. has 2 jobs - generate the  evaluation report for the candidiate and capture interview quality metrics 
## (distribution, adaptiveness, conisitency with instrictions/prompts, quality of questions)
## finally all this will be fed into the eval pipeline - gotta see how that will look like!
import json
from agent.llm import call_llm

def eval_agent(conversation_history, resume_text,jd_text,system_prompt = None):
    ## candidate evaluation
    prompt1 = """
    You are given the converstaion history of an interview. Conversation history consist of candidate's entire 
    interview conversation. You are also given the Resume & the JD of the role for whcih candidate gave the interview.
    Your job is to generate the candidate's report which will have metrics & remarks across each and feedback with
    strneghts and what can be done better.

    ------------Report guide------
    
    Add Scores and remarks for below metrics in the report:
    - Overall AI/ML knowledge
    - Technical explainability (how well the candidate is explaining the answers with technical aspect)
    - Communication (how well the candidate is handling the questions and able to answer in a structured manner)
    - Practical knowledge ( whether the candidate has knowledge on practical application building and challenges)

    Add Feedback here

    ------------------

    Below is the Resume & JD:

    Resume : {Resume}
    
    JD: {JD}

    Don't give vague feedbck & remarks. Give actions for canididate to work upon

    """

    message = [{"role":"system","content":prompt1.format(Resume = resume_text, JD = jd_text)},
    {"role":"user","content":str(conversation_history)}]

    candidate_feedback = call_llm(messages = message).content

    ##interview evaluation

    prompt2 = """
    You are given the converstaion history of an interview. Conversation history consist of candidate's entire 
    interview conversation. You are also given the Resume & the JD of the role for whcih candidate gave the interview.
    Your job is the access the questions asked by the interviewer. The interview should feel natural, be adaptive, not vague and should
    abide by the instructions (also given) to the interview agent. 

    ---------- Evaluation structure

    You can evaluate the interview questions on below metrics ( give a score & remarks):

    - Consistency with instructions ( was the LLM asking the questions being consistent with the prompt given to it?)
    - Hallucination (was it hallucinating with random statemnets or questions not making sense?)
    - questions quality (were the questions detailed and not vague)
    - adaptiveness ( was the interview difficluty adjusted as per the candidate's confidence level)
    - technical (how was the quality of AI/ML related questions)

    Add additional info here regarding your personal thoughts on the quality of interview. You can share what kind of additinal metrics makes sense

    ----------

    Below is the Resume & JD:

    Resume : {Resume}
    
    JD: {JD}

    Instructions for the interview agent : {Interview_System_Prompt}

    Don't give a score without the rational. You must jsutify the score given in the remarks

    """

    message = [{"role":"system","content":prompt2.format(Resume = resume_text, JD = jd_text, Interview_System_Prompt = system_prompt)},
    {"role":"user","content":str(conversation_history)}]

    questions_feedback = call_llm(messages = message).content


    return candidate_feedback, questions_feedback
