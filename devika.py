"""
    DO NOT REARRANGE THE ORDER OF THE FUNCTION CALLS AND VARIABLE DECLARATIONS
    AS IT MAY CAUSE IMPORT ERRORS AND OTHER ISSUES
"""
# import eventlet
# eventlet.monkey_patch()
from gevent import monkey

monkey.patch_all()
from src.init import init_devika

init_devika()

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from src.socket_instance import socketio, emit_agent
import os
import logging
import tiktoken

from src.apis.project import project_bp
from src.config import Config
from src.logger import Logger, route_logger
from src.project import ProjectManager, MessageSources
from src.state import AgentState
from src.agents import Agent, Action
from src.llm import LLM

app = Flask(__name__)
CORS(app)
app.register_blueprint(project_bp)
socketio.init_app(app)

log = logging.getLogger("werkzeug")
log.disabled = True

TIKTOKEN_ENC = tiktoken.get_encoding("cl100k_base")

os.environ["TOKENIZERS_PARALLELISM"] = "false"

manager = ProjectManager()
agent_state = AgentState()
config = Config()
logger = Logger()


# initial socket
@socketio.on('socket_connect')
def test_connect(data):
    print("Socket connected :: ", data)
    emit_agent("socket_response", {"data": "Server Connected"})


@app.route("/api/data", methods=["GET"])
@route_logger(logger)
def data():
    projects = manager.get_project_list()
    models = LLM().list_models()
    search_engines = ["Bing", "Google", "DuckDuckGo"]
    return jsonify({"projects": projects, "models": models, "search_engines": search_engines})


@app.route("/api/messages", methods=["POST"])
def get_messages():
    data = request.json
    project_name = data.get("project_name")
    messages = manager.get_messages(project_name)
    return jsonify({"messages": messages})


# Main socket
@socketio.on('user-message')
def handle_message(data):
    action = data.get('action')
    message = data.get('message')
    base_model = data.get('base_model')
    project_name = data.get('project_name')
    search_engine = data.get('search_engine').lower()

    # agent = Agent(base_model=base_model, search_engine=search_engine)

    # if action == 'continue':
    # new_message = manager.new_message(MessageSources.USER, message)
    manager.add_message_from_user(project_name, message)

    agent = Action(project_name=project_name, base_model=base_model)

    # if AgentState.is_agent_completed(project_name):
    # thread = Thread(target=lambda: agent.subsequent_execute(message, project_name))
    # thread.start()

    # non-threaded debugging variant
    agent.execute()

    # if action == 'execute_agent' and False:
    #     thread = Thread(target=lambda: agent.execute(message, project_name))
    #     thread.start()


@socketio.on('regenerate')
def regenerate(data):
    base_model = data.get('base_model')
    project_name = data.get('project_name')
    search_engine = data.get('search_engine').lower()

    agent = Action(project_name=project_name, base_model=base_model)
    agent.execute()


@socketio.on('clear-conversation')
def clear_conversation(data):
    project_name = data.get('project_name')
    manager.clear_conversation(project_name)
    emit_agent("clear-conversation", {})


@socketio.on('stop')
def regenerate(data):
    print("STOPPING")
    project_name = data.get('project_name')
    current_state = agent_state.get_latest_state(project_name)
    new_state = agent_state.new_state()
    new_state["browser_session"] = current_state["browser_session"]  # keep the browser session
    new_state["internal_monologue"] = "Interrupted by user"
    agent_state.add_to_current_state(project_name, new_state)


@app.route("/api/is-agent-active", methods=["POST"])
@route_logger(logger)
def is_agent_active():
    data = request.json
    project_name = data.get("project_name")
    is_active = agent_state.is_agent_active(project_name)
    return jsonify({"is_active": is_active})


@app.route("/api/get-agent-state", methods=["POST"])
@route_logger(logger)
def get_agent_state():
    data = request.json
    project_name = data.get("project_name")
    state = agent_state.get_latest_state(project_name)
    return jsonify({"state": state})


@app.route("/api/get-browser-snapshot", methods=["GET"])
@route_logger(logger)
def browser_snapshot():
    snapshot_path = request.args.get("snapshot_path")
    return send_file(snapshot_path, as_attachment=True)


@app.route("/api/get-browser-session", methods=["GET"])
@route_logger(logger)
def get_browser_session():
    project_name = request.args.get("project_name")
    state = agent_state.get_latest_state(project_name)
    if not state:
        return jsonify({"session": None})
    else:
        browser_session = agent_state["browser_session"]
        return jsonify({"session": browser_session})


@app.route("/api/get-terminal-session", methods=["GET"])
@route_logger(logger)
def get_terminal_session():
    project_name = request.args.get("project_name")
    state = agent_state.get_latest_state(project_name)
    if not state:
        return jsonify({"terminal_state": None})
    else:
        terminal_state = state["terminal_session"]
        return jsonify({"terminal_state": terminal_state})


@app.route("/api/run-code", methods=["POST"])
@route_logger(logger)
def run_code():
    data = request.json
    project_name = data.get("project_name")
    code = data.get("code")
    # TODO: Implement code execution logic
    return jsonify({"message": "Code execution started"})


@app.route("/api/calculate-tokens", methods=["POST"])
@route_logger(logger)
def calculate_tokens():
    data = request.json
    prompt = data.get("prompt")
    tokens = len(TIKTOKEN_ENC.encode(prompt))
    return jsonify({"token_usage": tokens})


@app.route("/api/token-usage", methods=["GET"])
@route_logger(logger)
def token_usage():
    project_name = request.args.get("project_name")
    token_count = agent_state.get_latest_token_usage(project_name)
    return jsonify({"token_usage": token_count})


@app.route("/api/logs", methods=["GET"])
def real_time_logs():
    log_file = logger.read_log_file()
    return jsonify({"logs": log_file})


@app.route("/api/settings", methods=["POST"])
@route_logger(logger)
def set_settings():
    data = request.json
    print("Data: ", data)
    config.config.update(data)
    config.save_config()
    return jsonify({"message": "Settings updated"})


@app.route("/api/settings", methods=["GET"])
@route_logger(logger)
def get_settings():
    configs = config.get_config()
    return jsonify({"settings": configs})


if __name__ == "__main__":
    logger.info("Devika is up and running!")
    socketio.run(app, debug=False, port=1337, host="0.0.0.0")
