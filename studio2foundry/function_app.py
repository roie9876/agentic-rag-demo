import azure.functions as func
import logging
import os
import json

from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import MessageRole           # <- AGENT / USER
from azure.identity import DefaultAzureCredential        # managed identity

PROJECT_ENDPOINT = os.getenv(
    "PROJECT_ENDPOINT",

)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="agent_httptrigger", methods=["GET", "POST"])
def agent_httptrigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(f"agent_httptrigger invoked with method: {req.method}")

    # ---------- parameters --------------------------------------------------
    msg = None
    agent_id = None
    thread_id = None

    # For POST requests, prioritize JSON body
    if req.method == "POST":
        try:
            body = req.get_json()
            if body:
                msg = body.get("message")
                agent_id = body.get("agentid")
                thread_id = body.get("threadid")
        except ValueError:
            error_response = {
                "success": False,
                "error": "Invalid JSON in request body"
            }
            return func.HttpResponse(
                json.dumps(error_response, ensure_ascii=False, indent=2),
                status_code=400,
                mimetype="application/json"
            )
    
    # For GET requests or if POST body is empty, use URL parameters
    if not (msg and agent_id):
        msg = req.params.get("message")
        agent_id = req.params.get("agentid")
        thread_id = req.params.get("threadid")

    if not (msg and agent_id):
        error_response = {
            "success": False,
            "error": "Need both 'message' and 'agentid' in request body (POST) or as URL parameters (GET)"
        }
        return func.HttpResponse(
            json.dumps(error_response, ensure_ascii=False, indent=2),
            status_code=400,
            mimetype="application/json"
        )

    try:
        # ---------- client --------------------------------------------------
        client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(),
        )

        if not client.agents.get_agent(agent_id):
            error_response = {
                "success": False,
                "error": f"Agent '{agent_id}' not found."
            }
            return func.HttpResponse(
                json.dumps(error_response, ensure_ascii=False, indent=2),
                status_code=404,
                mimetype="application/json"
            )

        # ---------- create / reuse thread -----------------------------------
        if thread_id:
            # validate thread exists
            try:
                client.agents.get_thread(thread_id)
            except Exception:
                error_response = {
                    "success": False,
                    "error": f"Thread '{thread_id}' not found."
                }
                return func.HttpResponse(
                    json.dumps(error_response, ensure_ascii=False, indent=2),
                    status_code=404,
                    mimetype="application/json"
                )

            client.agents.messages.create(                  # add user message
                thread_id=thread_id,
                role="user",
                content=msg,
            )

            run = client.agents.create_and_process_run(     # run agent
                thread_id=thread_id,
                agent_id=agent_id,
            )
        else:
            # one-shot create thread + run + first message
            run = client.agents.create_thread_and_process_run(
                agent_id=agent_id,
                thread={
                    "messages": [ { "role": "user", "content": msg } ]
                },
            )
            thread_id = run.thread_id

        # ---------- last AGENT reply ----------------------------------------
        last = client.agents.messages.get_last_message_text_by_role(
            thread_id=thread_id,
            role=MessageRole.AGENT,                         # enum value ✔
        )
        reply = last.text.value if last else "No agent reply."

        # Return JSON response
        response_data = {
            "success": True,
            "message": reply,
            "thread_id": thread_id,
            "agent_id": agent_id
        }

        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False, indent=2),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as exc:
        logging.exception("Agent call failed")
        error_response = {
            "success": False,
            "error": f"Internal Server Error: {str(exc)}"
        }
        return func.HttpResponse(
            json.dumps(error_response, ensure_ascii=False, indent=2),
            status_code=500,
            mimetype="application/json"
        )