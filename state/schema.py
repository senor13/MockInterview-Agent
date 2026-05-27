from pydantic import BaseModel
from datetime import datetime
from typing import Literal,Dict,List


class CandidateProfile(BaseModel):
    match_score : float
    projects : List[str]
    seniority_estimate : Literal["senior","mid","junior"]
    strenghts_for_role : List[str]
    gaps_for_role : List[str]

class InterviewState(BaseModel):
    no_of_turns : int
    topics_covered : List[str]
    current_topic : str | None = None
   # current_topic_depth_level : int

class CandidateLiveSignal(BaseModel):
    current_confidence_level: Literal["high","medium","low"] | None = None##could be basis voice
    last_answer_quality : Literal["poor","strong"] | None = None

class SessionMeta(BaseModel):
    session_id: str
    prompt_version: str
    started_at: datetime
    ended_at: datetime | None = None

class StateSchema(BaseModel):
    candidate_profile : CandidateProfile
    interview_state : InterviewState
    candidate_live_signal : CandidateLiveSignal
    session_meta : SessionMeta