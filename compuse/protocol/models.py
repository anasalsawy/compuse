"""Strict protocol models for the coordination boundary."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
from typing import Annotated, Literal, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
class StrictModel(BaseModel): model_config=ConfigDict(extra="forbid",strict=True)
class Origin(StrEnum):
 USER_INTENT="USER_INTENT"; SYSTEM_POLICY="SYSTEM_POLICY"; STRATEGIST_INSTRUCTION="STRATEGIST_INSTRUCTION"; EXECUTOR_INSTRUCTION="EXECUTOR_INSTRUCTION"; ENVIRONMENT_CONTENT="ENVIRONMENT_CONTENT"; PROVIDER_OUTPUT="PROVIDER_OUTPUT"
class ActionKind(StrEnum):
 WAIT="wait"; SCREENSHOT="screenshot"; MOUSE_MOVE="mouse_move"; TYPE="type"; CLICK="click"; DOUBLE_CLICK="double_click"; DRAG="drag"; SCROLL="scroll"; KEYPRESS="keypress"; KEY_COMBO="key_combo"; FOCUS_WINDOW="window.focus"; LAUNCH="application.launch"; OPEN_FILE="file.open"; BROWSE="browse"
class Wait(StrictModel): kind:Literal[ActionKind.WAIT]=ActionKind.WAIT; seconds:float=Field(ge=0,le=60)
class Screenshot(StrictModel): kind:Literal[ActionKind.SCREENSHOT]=ActionKind.SCREENSHOT
class MouseMove(StrictModel): kind:Literal[ActionKind.MOUSE_MOVE]=ActionKind.MOUSE_MOVE; x:int=Field(ge=-1000000,le=1000000); y:int=Field(ge=-1000000,le=1000000)
class TypeText(StrictModel): kind:Literal[ActionKind.TYPE]=ActionKind.TYPE; text:str=Field(max_length=10000)
class Click(StrictModel): kind:Literal[ActionKind.CLICK]=ActionKind.CLICK; x:int=Field(ge=-1000000,le=1000000); y:int=Field(ge=-1000000,le=1000000)
class DoubleClick(Click): kind:Literal[ActionKind.DOUBLE_CLICK]=ActionKind.DOUBLE_CLICK
class Drag(StrictModel): kind:Literal[ActionKind.DRAG]=ActionKind.DRAG; start_x:int=Field(ge=-1000000,le=1000000); start_y:int=Field(ge=-1000000,le=1000000); end_x:int=Field(ge=-1000000,le=1000000); end_y:int=Field(ge=-1000000,le=1000000)
class Scroll(StrictModel): kind:Literal[ActionKind.SCROLL]=ActionKind.SCROLL; delta:int=Field(ge=-100000,le=100000)
class Keypress(StrictModel): kind:Literal[ActionKind.KEYPRESS]=ActionKind.KEYPRESS; key:str=Field(min_length=1,max_length=64)
class KeyCombo(StrictModel): kind:Literal[ActionKind.KEY_COMBO]=ActionKind.KEY_COMBO; keys:tuple[str,...]=Field(min_length=1,max_length=8)
class FocusWindow(StrictModel): kind:Literal[ActionKind.FOCUS_WINDOW]=ActionKind.FOCUS_WINDOW; window_id:str=Field(min_length=1,max_length=256)
class ApplicationLaunch(StrictModel): kind:Literal[ActionKind.LAUNCH]=ActionKind.LAUNCH; target_id:str=Field(min_length=1,max_length=128)
class OpenFile(StrictModel): kind:Literal[ActionKind.OPEN_FILE]=ActionKind.OPEN_FILE; path:str=Field(min_length=1,max_length=1024)
class Browse(StrictModel): kind:Literal[ActionKind.BROWSE]=ActionKind.BROWSE; url:str=Field(min_length=1,max_length=2048)
Action=Annotated[Union[Wait,Screenshot,MouseMove,TypeText,Click,DoubleClick,Drag,Scroll,Keypress,KeyCombo,FocusWindow,ApplicationLaunch,OpenFile,Browse],Field(discriminator="kind")]
class Observation(StrictModel):
 run_id:str=Field(min_length=1,max_length=128); revision:int=Field(ge=0); captured_at:datetime; coordinate_space_id:str=Field(min_length=1,max_length=256); foreground_window:str|None=None; process_id:int|None=Field(default=None,ge=0); session_id:int|None=Field(default=None,ge=0); input_desktop:str|None=Field(default=None,max_length=256)
 @field_validator("captured_at")
 @classmethod
 def aware(cls,v):
  if v.tzinfo is None or v.utcoffset() is None: raise ValueError("captured_at must be timezone-aware")
  return v.astimezone(timezone.utc)
class ActionProposal(StrictModel):
 action_id:str=Field(min_length=1,max_length=128); run_id:str=Field(min_length=1,max_length=128); action:Action; origin:Origin; observation_revision:int=Field(ge=0); coordinate_space_id:str=Field(min_length=1,max_length=256); policy_revision:str=Field(min_length=1,max_length=128); tool:str=Field(default="portable",min_length=1,max_length=128); capability_hash:str|None=Field(default=None,pattern=r"^[0-9a-f]{64}$"); launch_policy_revision:str|None=None; browser_revision:str|None=None; window_id:str|None=None; process_id:int|None=Field(default=None,ge=0); session_id:int|None=Field(default=None,ge=0); input_desktop:str|None=None; confirmation_id:UUID|None=None
class Permit(StrictModel):
 permit_id:UUID; run_id:str; action_id:str; action_hash:str=Field(pattern=r"^[0-9a-f]{64}$"); observation_revision:int=Field(ge=0); coordinate_space_id:str; policy_revision:str; expires_at:datetime; consumed:bool=False; tool:str="portable"; capability_hash:str|None=None; launch_policy_revision:str|None=None; browser_revision:str|None=None; window_id:str|None=None; process_id:int|None=None; session_id:int|None=None; input_desktop:str|None=None; confirmation_id:UUID|None=None
def now(): return datetime.now(timezone.utc)
def digest_action(action:Action)->str: return sha256(json.dumps(action.model_dump(mode="json"),sort_keys=True,separators=(",",":")).encode()).hexdigest()
