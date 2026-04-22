let ws = null;
let usernameInput = null;
let statusEl = null;
let publicBtn = null;

window.addEventListener("load", () => {
  usernameInput = document.getElementById("username");
  statusEl = document.getElementById("status");
  publicBtn = document.getElementById("publicBtn");

  publicBtn.onclick = onPublicGameClick;
});

function connectWebSocket(callback) {
  ws = new WebSocket("ws://localhost:8000/ws");

  ws.onopen = () => {
    console.log("WS connected");
    if (callback) callback();
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("WS message:", data);

    if (data.type === "error") {
      statusEl.textContent = data.message;
    }

    if (data.type === "searching") {
      statusEl.textContent = "Finding match…";
    }

    if (data.type === "match_found") {
      const roomId = data.room_id;
      const color = data.your_color;
      const you = encodeURIComponent(data.your_username);
      const opp = encodeURIComponent(data.opponent_username);

      statusEl.textContent = `Match found! You: ${data.your_username} (${color}), Opponent: ${data.opponent_username}`;

      setTimeout(() => {
        window.location.href =
          `/static/game.html?room_id=${roomId}&color=${color}&you=${you}&opp=${opp}`;
      }, 2000);
    }
  };

  ws.onclose = () => {
    console.log("WS closed");
    if (statusEl.textContent === "Finding match…") {
      statusEl.textContent = "Disconnected from server.";
    }
  };
}

function onPublicGameClick() {
  const username = usernameInput.value.trim();
  if (!username) {
    statusEl.textContent = "Please enter a username first.";
    return;
  }

  statusEl.textContent = "Connecting to server…";

  if (!ws || ws.readyState !== WebSocket.OPEN) {
    connectWebSocket(() => {
      startPublicMatch(username);
    });
  } else {
    startPublicMatch(username);
  }
}

function startPublicMatch(username) {
  statusEl.textContent = "Finding match…";
  ws.send(JSON.stringify({
    type: "find_match",
    username: username
  }));

  setTimeout(() => {
    if (statusEl.textContent === "Finding match…") {
      statusEl.textContent = "Still searching for an opponent…";
    }
  }, 5000);
}
