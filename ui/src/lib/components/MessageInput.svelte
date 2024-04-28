<script>
  import {socket} from "$lib/api";
  import {agentState, messages} from "$lib/store";
  import {calculateTokens} from "$lib/token";

  let isAgentActive = false;

  if ($agentState !== null) {
    isAgentActive = $agentState.agent_is_active;
  }

  let messageInput = "";

  async function handleSendMessage() {
    const projectName = localStorage.getItem("selectedProject");
    const selectedModel = localStorage.getItem("selectedModel");
    const searchEngine = localStorage.getItem("selectedSearchEngine");

    if (!projectName) {
      alert("Please select a project first!");
      return;
    }
    if (!selectedModel) {
      alert("Please select a model first!");
      return;
    }

    if (messageInput.trim() !== "" && !isAgentActive) {
      if ($messages.length === 0) {
        socket.emit("user-message", {
          action: "execute_agent",
          message: messageInput,
          base_model: selectedModel,
          project_name: projectName,
          search_engine: searchEngine,
        });
      } else {
        socket.emit("user-message", {
          action: "continue",
          message: messageInput,
          base_model: selectedModel,
          project_name: projectName,
          search_engine: searchEngine,
        });
      }
      messageInput = "";
    }
  }

  async function handleRegenerate() {
    const projectName = localStorage.getItem("selectedProject");
    const selectedModel = localStorage.getItem("selectedModel");
    const searchEngine = localStorage.getItem("selectedSearchEngine");

    if (!projectName) {
      alert("Please select a project first!");
      return;
    }
    if (!selectedModel) {
      alert("Please select a model first!");
      return;
    }

    if (!isAgentActive) {
      socket.emit("regenerate", {
        base_model: selectedModel,
        project_name: projectName,
        search_engine: searchEngine,
      });
    }
  }

  async function handleClearConversation() {
    const projectName = localStorage.getItem("selectedProject");
    if (confirm("Are you sure you want to clear the conversation?")) {
      socket.emit("clear-conversation", {project_name: projectName});
    }
  }

  async function handleStop() {
    const projectName = localStorage.getItem("selectedProject");
    if (isAgentActive) {
      socket.emit("stop", {project_name: projectName});
    }
  }

  function setTokenSize(event) {
    const prompt = event.target.value;
    let tokens = calculateTokens(prompt);
    document.querySelector(".token-count").textContent = `${tokens} tokens`;
  }
</script>

<div class="expandable-input relative">
  <textarea
    id="message-input"
    class="w-full p-2 dark:border-blue-900 border-2 rounded-lg pr-20 dark:bg-gray-900"
    placeholder="Type your message..."
    bind:value={messageInput}
    on:input={setTokenSize}
    on:keydown={(e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    }}
  ></textarea>
  <div class="token-count text-gray-400 text-xs p-1">0 tokens</div>
  <div class="flex space-x-2">
    <button
      id="send-message-btn"
      class={`px-4 py-3 text-white rounded-lg flex-grow ${isAgentActive ? "bg-slate-800" : "bg-black dark:bg-blue-800"}`}
      on:click={handleSendMessage}
      disabled={isAgentActive}
    >
      {@html isAgentActive ? "<i>Agent is busy...</i>" : "Send"}
    </button>
    <button
      id="refresh-btn"
      class={`px-4 py-3 text-white rounded-lg w-auto ${isAgentActive ? "bg-slate-800" : "bg-blue-500"}`}
      on:click={handleRegenerate}
      disabled={isAgentActive}
    >
      <i class="fas fa-refresh"></i>
    </button>
    <button
      id="stop-btn"
      class={`px-4 py-3 text-white rounded-lg w-auto ${isAgentActive ? "bg-orange-500" : "bg-slate-800"}`}
      on:click={handleStop}
      disabled={!isAgentActive}
    >
      <i class="fas fa-stop"></i>
    </button>

    <button
      id="stop-btn"
      class={`px-4 py-3 text-white rounded-lg w-auto bg-red-500`}
      on:click={handleClearConversation}
    >
      <i class="fas fa-trash"></i>
    </button>

  </div>
</div>

<style>
  .expandable-input textarea {
    min-height: 60px;
    max-height: 200px;
    resize: none;
  }
</style>
