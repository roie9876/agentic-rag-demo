import azure.functions as func
import logging
import os

from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import MessageRole           # <- AGENT / USER
from azure.identity import DefaultAzureCredential        # managed identity

PROJECT_ENDPOINT = os.getenv(
    "PROJECT_ENDPOINT",

)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="agent_httptrigger")
def agent_httptrigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("agent_httptrigger invoked")

    # ---------- parameters --------------------------------------------------
    msg       = req.params.get("message")
    agent_id  = req.params.get("agentid")
    thread_id = req.params.get("threadid")

    if not (msg and agent_id):
        try:
            body = req.get_json()
            msg       = msg       or body.get("message")
            agent_id  = agent_id  or body.get("agentid")
            thread_id = thread_id or body.get("threadid")
        except ValueError:
            pass

    if not (msg and agent_id):
        return func.HttpResponse(
            "Need both 'message' and 'agentid'.",
            status_code=400,
        )

    try:
        # ---------- client --------------------------------------------------
        client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(),
        )

        if not client.agents.get_agent(agent_id):
            return func.HttpResponse(f"Agent '{agent_id}' not found.", status_code=404)

        # ---------- create / reuse thread -----------------------------------
        if thread_id:
            # validate thread exists
            try:
                client.agents.get_thread(thread_id)
            except Exception:
                return func.HttpResponse(f"Thread '{thread_id}' not found.", status_code=404)

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

        return func.HttpResponse(reply, status_code=200, mimetype="text/plain")

    except Exception as exc:
        logging.exception("Agent call failed")
        return func.HttpResponse(f"Internal Server Error: {exc}", status_code=500)