import json
import uuid

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response
from sse_starlette.sse import EventSourceResponse

app = FastAPI()


@app.post("/v1/chat/completions")
async def proxy(request: Request):
    data = await request.json()
    headers = request.headers
    if not headers.get("Authorization", None):
        return Response(content="Invalid token", status_code=403)
    if not headers["Authorization"].startswith("Bearer "):
        return Response(content="Invalid token", status_code=403)
    auth_data = headers["Authorization"].split(" ")[1].split("|")
    if len(auth_data) != 2:
        return Response(content="Invalid token", status_code=403)
    token = auth_data[0]
    group_id = auth_data[1]
    stream = data.get("stream", False)
    model = data.get("model", "abab5.5")

    if model not in ["abab5-chat", "abab5.5-chat", "abab5.5-chat-pro"]:
        return Response(content="Invalid model", status_code=400)

    if model == "abab5.5-chat-pro":
        url = "https://api.minimax.chat/v1/text/chatcompletion_pro"

        messages = data.get("messages", [])
        prompt = ""
        messages_to_send = []
        for message in messages:
            if message["role"] == "system":
                prompt += message["content"] + "\n"
            elif message["role"] == "assistant":
                messages_to_send.append({
                    "sender_type": "BOT",
                    "sender_name": "MM智能助理",
                    "text": message.get("content", ""),
                    "function_call": message.get("function_call", {})
                })
            elif message["role"] == "function":
                messages_to_send.append({
                    "sender_type": "FUNCTION",
                    "sender_name": "MM智能助理",
                    "text": message["content"]
                })
            else:
                messages_to_send.append({
                    "sender_type": "USER",
                    "sender_name": "小明",
                    "text": message["content"]
                })
        if prompt == "":
            prompt = "MM智能助理是一款由MiniMax自研的，没有调用其他产品的接口的大型语言模型。MiniMax是一家中国科技公司，一直致力于进行大模型相关的研究。\n"

        request_data = {
            "model": "abab5.5-chat",
            "bot_setting": [
                {
                    "bot_name": "MM智能助理",
                    "content": prompt
                }
            ],
            "messages": messages_to_send,
            "top_p": data.get("top_p", 0.95),
            "temperature": data.get("temperature", 0.9),
            "tokens_to_generate": data.get("max_tokens", None),
            "functions": data.get("functions", []),
            "reply_constraints": {
                "sender_type": "BOT",
                "sender_name": "MM智能助理"
            },
        }

        if stream:
            request_data["stream"] = True
            request_data["use_standard_sse"] = True

            async def event_stream():
                async with httpx.AsyncClient() as client:
                    async with client.stream(method="POST", url=url,
                                             headers={
                                                 "Authorization": "Bearer " + token
                                             },
                                             params={
                                                 "GroupId": group_id
                                             },
                                             json=request_data, timeout=180) as response:
                        request_id = str(uuid.uuid4())
                        async for line in response.aiter_lines():
                            if line[:6] == "data: ":
                                stream_data = json.loads(line[6:])
                                stream_choices = []
                                for c in stream_data["choices"]:
                                    for m in c["messages"]:
                                        single_choice = {
                                            "index": 0,
                                            "delta": {
                                                "content": m["text"],
                                            },
                                            "content_filter_results": {}
                                        }
                                        if "finish_reason" in c:
                                            single_choice["finish_reason"] = c["finish_reason"]
                                        if "function_call" in m:
                                            single_choice["delta"]["function_call"] = {}
                                            if "name" in m["function_call"]:
                                                single_choice["delta"]["function_call"]["name"] = m["function_call"]["name"]
                                            if "arguments" in m["function_call"]:
                                                single_choice["delta"]["function_call"]["arguments"] = m["function_call"]["arguments"]
                                            del single_choice["delta"]["content"]
                                        stream_choices.append(single_choice)
                                send_resp_data = json.dumps({
                                    "id": request_id,
                                    "object": "chat.completion.chunk",
                                    "created": stream_data["created"],
                                    "model": stream_data["model"],
                                    "choices": stream_choices,
                                    "usage": None
                                })
                                yield send_resp_data
                        yield "[DONE]"

            return EventSourceResponse(event_stream(), media_type="text/event-stream")
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=request_data,
                                             headers={
                                                 "Authorization": "Bearer " + token,
                                                 "Content-Type": "application/json"
                                             }, params={
                                                "GroupId": group_id
                                             }, timeout=180)
                resp_data = json.loads(response.content)
                resp_choices = []
                for choice in resp_data["choices"]:
                    for message in choice["messages"]:
                        simple_choice = {
                            "message": {
                                "role": "assistant",
                                "content": message["text"]
                            },
                            "finish_reason": choice["finish_reason"]
                        }
                        if "function_call" in message:
                            simple_choice["message"]["function_call"] = message["function_call"]
                            simple_choice["finish_reason"] = "function_call"
                            del simple_choice["message"]["content"]
                        resp_choices.append(simple_choice)
                resp_content = json.dumps({
                    "id": str(uuid.uuid4()),
                    "object": "chat.completion",
                    "created": resp_data["created"],
                    "model": resp_data["model"],
                    "choices": resp_choices,
                    "usage": {
                        "completion_tokens": resp_data["usage"]["total_tokens"],
                        "prompt_tokens": 0,
                        "total_tokens": resp_data["usage"]["total_tokens"]
                    }
                })
                return Response(content=resp_content, status_code=response.status_code,
                                media_type="application/json")
    else:
        url = "https://api.minimax.chat/v1/text/chatcompletion"

        messages = data.get("messages", [])
        prompt = ""
        messages_to_send = []
        for message in messages:
            if message["role"] == "system":
                prompt += message["content"] + "\n"
            elif message["role"] == "assistant":
                messages_to_send.append({
                    "sender_type": "BOT",
                    "text": message["content"]
                })
            else:
                messages_to_send.append({
                    "sender_type": "USER",
                    "text": message["content"]
                })
        if prompt == "":
            prompt = "MM智能助理是一款由MiniMax自研的，没有调用其他产品的接口的大型语言模型。MiniMax是一家中国科技公司，一直致力于进行大模型相关的研究。\n"

        request_data = {
            "model": model,
            "prompt": prompt,
            "role_meta": {
                "user_name": "我",
                "bot_name": "系统"
            },
            "messages": messages_to_send,
            "top_p": data.get("top_p", 0.95),
            "temperature": data.get("temperature", 0.9),
            "tokens_to_generate": data.get("max_tokens", None),
        }
        if stream:
            request_data["stream"] = True
            request_data["use_standard_sse"] = True

            async def event_stream():
                async with httpx.AsyncClient() as client:
                    async with client.stream(method="POST", url=url,
                                             headers={
                                                 "Authorization": "Bearer " + token
                                             },
                                             params={
                                                 "GroupId": group_id
                                             },
                                             json=request_data, timeout=180) as response:
                        request_id = str(uuid.uuid4())
                        async for line in response.aiter_lines():
                            if line[:6] == "data: ":
                                stream_data = json.loads(line[6:])
                                stream_choices = []
                                for c in stream_data["choices"]:
                                    single_choice = {
                                        "index": 0,
                                        "delta": {
                                            "content": c["delta"],
                                        },
                                        "content_filter_results": {}
                                    }
                                    if "finish_reason" in c:
                                        single_choice["finish_reason"] = c["finish_reason"]
                                    stream_choices.append(single_choice)
                                send_resp_data = json.dumps({
                                    "id": request_id,
                                    "object": "chat.completion.chunk",
                                    "created": stream_data["created"],
                                    "model": stream_data["model"],
                                    "choices": stream_choices,
                                    "usage": None
                                })
                                yield send_resp_data
                        yield "[DONE]"

            return EventSourceResponse(event_stream(), media_type="text/event-stream")
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=request_data,
                                             headers={
                                                 "Authorization": "Bearer " + token,
                                                 "Content-Type": "application/json"
                                             }, params={
                                                "GroupId": group_id
                                             }, timeout=180)

                resp_data = json.loads(response.content)
                resp_choices = []
                for choice in resp_data["choices"]:
                    resp_choices.append({
                        "index": choice["index"],
                        "message": {
                            "role": "assistant",
                            "content": choice["text"]
                        },
                        "finish_reason": choice["finish_reason"]
                    })
                resp_content = json.dumps({
                    "id": str(uuid.uuid4()),
                    "object": "chat.completion",
                    "created": resp_data["created"],
                    "model": resp_data["model"],
                    "choices": resp_choices,
                    "usage": {
                        "completion_tokens": resp_data["usage"]["total_tokens"],
                        "prompt_tokens": 0,
                        "total_tokens": resp_data["usage"]["total_tokens"]
                    }
                })
                return Response(content=resp_content, status_code=response.status_code,
                                media_type="application/json")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
