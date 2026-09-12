from datetime import datetime,timezone
from enum import StrEnum
from hashlib import sha256
import json
from typing import Annotated,Literal,Union
from pydantic import BaseModel,ConfigDict,Field
class Strict(BaseModel): model_config=ConfigDict(extra="forbid",strict=True)
class Origin(StrEnum): USER_INTENT="USER_INTENT"; SYSTEM_POLICY="SYSTEM_POLICY"; STRATEGIST_INSTRUCTION="STRATEGIST_INSTRUCTION"; EXECUTOR_INSTRUCTION="EXECUTOR_INSTRUCTION"; ENVIRONMENT_CONTENT="ENVIRONMENT_CONTENT"; PROVIDER_OUTPUT="PROVIDER_OUTPUT"
class ActionKind(StrEnum): WAIT="wait"; SCREENSHOT="screenshot"; TYPE="type"; CLICK="click"
class Wait(Strict): kind:Literal[ActionKind.WAIT]=ActionKind.WAIT; seconds:float=Field(ge=0,le=60)
class Screenshot(Strict): kind:Literal[ActionKind.SCREENSHOT]=ActionKind.SCREENSHOT
class TypeText(Strict): kind:Literal[ActionKind.TYPE]=ActionKind.TYPE; text:str=Field(max_length=10000)
class Click(Strict): kind:Literal[ActionKind.CLICK]=ActionKind.CLICK; x:int; y:int
Action=Annotated[Union[Wait,Screenshot,TypeText,Click],Field(discriminator="kind")]
class Observation(Strict): run_id:str; revision:int=Field(ge=0); captured_at:datetime; coordinate_space_id:str; foreground_window:str|None=None
class ActionProposal(Strict): action_id:str; run_id:str; action:Action; origin:Origin; observation_revision:int; policy_revision:str
class Permit(Strict): permit_id:str; run_id:str; action_id:str; action_hash:str; observation_revision:int; policy_revision:str; expires_at:datetime; consumed:bool=False
def now(): return datetime.now(timezone.utc)
def digest_action(a): return sha256(json.dumps(a.model_dump(mode="json"),sort_keys=True,separators=(",",":")).encode()).hexdigest()
