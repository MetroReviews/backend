from pydantic import BaseModel
from typing import Optional, Any
from .tables import BotQueue, Action, State, BotList, ListState
import aiohttp
import orjson

class SilverpeltRequest(BaseModel):
    """Data that makes up a silverpelt request"""
    bot_id: int
    reason: str
    resend: bool
    action: Action
    reviewer: int

class SilverpeltAction(BaseModel):
    """Internal class containing info about a possible action"""
    banned_states: list[State]
    error: str
    new_state: State
    list_key: str

class SilverpeltHTTP(BaseModel):
    """A Silverpelt HTTP request"""
    data: dict
    url: str
    key: str

class SilverpeltHttpResponse(BaseModel):
    """A Silverpelt HTTP response"""
    status: int
    msg: Optional[str] = None
    data: Any
    exc: Optional[str] = None
    sent_data: dict

class SilverpeltResponse(BaseModel):
    """
Response to a silverpelt request

- message: the message on why the request was rejected (if none, the request was accepted)
- lists: Any list specific errors
"""
    message: str = None
    lists: Optional[dict[str, SilverpeltHttpResponse]] = None

    def to_msg(self) -> str:
        """
        Convert the response to a message
        """
        msg = ""
        if self.message:
            msg = f"**Request Failed**\n{self.message}"
        if self.lists:
            msg += "\n".join(f"{name}: {response.msg}" for name, response in self.lists.items())
        return msg
    
    def to_html(self) -> str:
        """
        Convert the response to a message
        """
        msg = ""
        if self.message:
            msg = f"<h1>Request Failed</h1><h2>{self.message}</h2>"
        else:
            msg = "<h1>Request Successful</h1>"
        if self.lists:
            msg += "<br/><br/>".join(f"<h3>{name}<h3><br/>{response.msg}" for name, response in self.lists.items())
        return msg

class Silverpelt():
    """Core heart of metro reviews"""
    def __init__(self, secrets: dict[str, str]):
        self.secrets = secrets
        self.good_states = (ListState.PENDING_API_SUPPORT, ListState.SUPPORTED)
        self._actions = {
            Action.CLAIM: SilverpeltAction(
                banned_states=[State.PENDING],
                error="This bot cannot be claimed as it is not pending review? Maybe someone is testing it right now?",
                new_state=State.UNDER_REVIEW,
                list_key="claim_bot_api"
            ),
            Action.UNCLAIM: SilverpeltAction(
                banned_states=[State.UNDER_REVIEW],
                error="This bot cannot be unclaimed as it is not under review?",
                new_state=State.PENDING,
                list_key="unclaim_bot_api"
            ),
            Action.APPROVE: SilverpeltAction(
                banned_states=[State.UNDER_REVIEW],
                error="This bot cannot be approved as it is not under review?",
                new_state=State.APPROVED,
                list_key="approve_bot_api"
            ),
            Action.DENY: SilverpeltAction(
                banned_states=[State.UNDER_REVIEW],
                error="This bot cannot be denied as it is not under review?",
                new_state=State.DENIED,
                list_key="deny_bot_api"
            )
        }
    
    async def _make_request(self, data: SilverpeltHTTP) -> SilverpeltHttpResponse:     
        try:   
            async with aiohttp.ClientSession() as sess:
                async with sess.post(
                    data.url, 
                    headers={"Authorization": data.key, "User-Agent": "Frostpaw/0.2 (Silverpelt)"}, 
                ) as resp:
                    try:
                        json_d = await resp.text()
                    except Exception as exc:
                        return SilverpeltHttpResponse(
                            status=resp.status, 
                            msg="Failed to parse response", 
                            data=None, 
                            exc=str(exc),
                            sent_data=data.data
                        )
                
                    if resp.headers.get("content-type", "").startswith("application/json"):
                        try:
                            json_d = orjson.loads(json_d)
                        except Exception as exc:
                            return SilverpeltHttpResponse(
                                status=resp.status, 
                                msg=f"JSON deserialisation failed", 
                                data=json_d, 
                                exc=str(exc), 
                                sent_data=data.data
                            )
                    
                    return SilverpeltHttpResponse(status=resp.status, msg=None, data=json_d, sent_data=data.data)
        except Exception as exc:
            return SilverpeltHttpResponse(status=-1, msg="Failed to make request", data=None, exc=str(exc), sent_data=data.data)

    async def request(self, data: SilverpeltRequest) -> Optional[SilverpeltResponse]:
        """Asks silverpelt to handle a action"""
        if len(data.reason) < 5:
            return SilverpeltResponse(message="Reason must be at least 5 characters")

        bot = await BotQueue.select(BotQueue.all_columns(
            exclude=(
                BotQueue.bot_id,
            )
        )).where(BotQueue.bot_id == data.bot_id).first()

        if not bot:
            return SilverpeltResponse(message="Bot not found")
        
        action = self._actions[data.action]

        if not data.resend:
            # Check if state is banned
            if bot["state"] in action.banned_states:
                return SilverpeltResponse(message=action.error)

        if action == Action.CLAIM and not data.resend:
            await BotQueue.update(reviewer=data.reviewer).where(BotQueue.bot_id == data.bot_id)

        # Update state
        await BotQueue.update(state=action.new_state).where(BotQueue.bot_id == data.bot_id)

        lists = await BotList.select(BotList.id, BotList.name, BotList.domain, BotList.state, action.list_key, BotList.secret_key)

        list_resp: dict[str, SilverpeltHttpResponse] = {}

        for obj in lists:
            name = str(obj["domain"] or obj["name"] or obj["id"])
            if obj["state"] not in self.good_states:
                continue
            if str(obj["id"]) != str(bot["list_source"]) and not bot["cross_add"]:
                list_resp[name] = (
                    await self._make_request(
                        SilverpeltHTTP(
                            url=obj[action.list_key],
                            key=obj["secret_key"],
                            data = {
                                "bot_id": str(data.bot_id), 
                                "owner": str(bot["owner"]), 
                                "extra_owners": [str(v) for v in data["extra_owners"]],
                                "cross_add": False,
                                "prefix": None, # Dont send prefix
                                "description": "", # Dont send description
                                "long_description": "", # Dont send ld
                                "list_source": bot["list_source"],
                                "nsfw": True, # Dont send nsfw
                                "tags": ["this-shouldnt-be-set"], # Dont send tags
                                "username": bot["username"], # Username is needed for approve 
                                "added_at": bot["added_at"], 
                                "reason": data.reason or "STUB_REASON",
                                "reviewer": str(data.reviewer),
                                "limited": True
                            }
                        )
                    )
                )
            else:
                list_resp[name] = (
                    await self._make_request(
                        SilverpeltHTTP(
                            url=obj[action.list_key],
                            key=obj["secret_key"],
                            data = bot | {
                                "bot_id": str(data.bot_id), 
                                "owner": str(bot["owner"]), 
                                "reason": data.reason or "STUB_REASON", 
                                "reviewer": str(data.reviewer), 
                                "added_at": str(bot["added_at"]), 
                                "list_source": str(bot["list_source"]),
                                "owner": str(bot["owner"]),
                                "extra_owners": [str(v) for v in bot["extra_owners"]],
                                "limted": False
                            },
                        )
                    )
                )
        
        return SilverpeltResponse(
            lists=list_resp
        )
    