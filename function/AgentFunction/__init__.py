import json
import logging
import azure.functions as func

logging.info("About to import agent module")
try:
    from agent import answer_question
    logging.info("Successfully imported answer_question")
except Exception as e:
    logging.error(f"Failed to import agent: {e}")
    raise

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function entry-point.
    Accepts either:
      • query-string ?q=your+question
      • JSON body { "question": "…" }
    Returns plain-text answer (could be easily switched to JSON).
    """
    logging.info("AgentFunction triggered")

    question = req.route_params.get("question")   # ← 1st priority: path
    if not question:
        question = req.params.get("q")            # ← 2nd: query string
    # NEW: optional overrides
    index_override     = req.params.get("index")
    reranker_override  = req.params.get("reranker")
    agent_override   = req.params.get("agent")     # ← new
    maxout_override   = req.params.get("maxout")   # optional
    mode_override = req.params.get("mode")          # "responses" to switch
    debug_flag = req.params.get("debug")  # ?debug=true
    include_src = req.params.get("includesrc")   # ?includesrc=true

    # JSON body fall-back
    if not question:
        try:
            data = req.get_json()
            question          = question or data.get("question")
            index_override    = index_override or data.get("index")
            reranker_override = reranker_override or data.get("reranker")
            agent_override   = agent_override or data.get("agent")
            maxout_override = maxout_override or data.get("maxout")
            mode_override = mode_override or data.get("mode")
            debug_flag = debug_flag or data.get("debug")
            include_src = include_src or data.get("includesrc")
        except ValueError:
            pass

    if not question:
        return func.HttpResponse(
            "Missing 'question'. Pass as query ?q= or JSON {\"question\": \"...\"}",
            status_code=400
        )

    try:
        result = answer_question(
            question,
            index_name=index_override,
            reranker_threshold=float(reranker_override) if reranker_override else None,
            agent_name=agent_override,
            max_output_size=int(maxout_override) if maxout_override else None,
            use_responses=(mode_override == "responses"),
            debug=str(debug_flag).lower() == "true",
            include_sources=str(include_src).lower() == "true",   # ← NEW
        )

        if isinstance(result, dict):           # JSON mode
            return func.HttpResponse(
                json.dumps(result, ensure_ascii=False),
                mimetype="application/json"
            )

        return func.HttpResponse(result, mimetype="text/plain")
    except Exception as exc:
        logging.exception("answer_question failed")
        return func.HttpResponse(
            f"Internal error: {exc}", status_code=500, mimetype="text/plain"
        )
