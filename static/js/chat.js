document.addEventListener("DOMContentLoaded", function () {
  var shell = document.querySelector("[data-chat-room]");
  if (!shell) return;

  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");
  var log = document.getElementById("chat-log");
  var status = document.getElementById("chat-status");
  var wsPath = shell.getAttribute("data-chat-ws-path");
  if (!form || !input || !log || !status || !wsPath) return;

  var protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  var socket = new WebSocket(protocol + "//" + window.location.host + wsPath);

  function scrollToBottom() {
    log.scrollTop = log.scrollHeight;
  }

  function appendMessage(payload) {
    var item = document.createElement("article");
    item.className = "chat-message";

    var header = document.createElement("header");
    var author = document.createElement("strong");
    author.textContent = payload.author_name || "Anonymous learner";
    var time = document.createElement("span");
    time.textContent = payload.created_at || "just now";

    var body = document.createElement("p");
    body.textContent = payload.body || "";

    header.appendChild(author);
    header.appendChild(time);
    item.appendChild(header);
    item.appendChild(body);
    log.appendChild(item);
    scrollToBottom();
  }

  socket.addEventListener("open", function () {
    status.textContent = "Realtime chat connected.";
    scrollToBottom();
  });

  socket.addEventListener("message", function (event) {
    try {
      var data = JSON.parse(event.data);
      if (data.type === "message") {
        appendMessage(data.payload || {});
        return;
      }
      if (data.type === "system" || data.type === "error") {
        status.textContent = (data.payload && data.payload.message) || "Chat updated.";
      }
    } catch (_) {
      status.textContent = "Received an unreadable chat event.";
    }
  });

  socket.addEventListener("close", function () {
    status.textContent = "Realtime chat disconnected.";
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var body = input.value.trim();
    if (!body) return;
    if (socket.readyState !== WebSocket.OPEN) {
      status.textContent = "Chat is not connected yet.";
      return;
    }
    socket.send(JSON.stringify({ type: "message", body: body }));
    input.value = "";
  });
});
