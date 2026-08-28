function formatTime(isoString) {
  const date = new Date(isoString);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function appendMessage(msg, isMine) {
  const container = document.getElementById("messages-container");
  if (!container) return;

  const row = document.createElement("div");
  row.className = `message-row ${isMine ? "mine" : "theirs"}`;

  row.innerHTML = `
    <div class="message-bubble">
      ${
        msg.sender_username && !isMine
          ? `<div class="msg-sender">${escapeHtml(msg.sender_username)}</div>`
          : ""
      }
      ${msg.image_url ? `<img src="${msg.image_url}" class="msg-image" alt="">` : ""}
      ${msg.content ? `<div class="msg-content">${escapeHtml(msg.content)}</div>` : ""}
      <div class="msg-time">${formatTime(msg.timestamp)}</div>
    </div>
  `;

  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

function renderHistory(messages, isMineFn) {
  const container = document.getElementById("messages-container");
  if (!container) return;
  container.innerHTML = "";
  messages.forEach((msg) => appendMessage(msg, isMineFn(msg)));
}

socket.on("global_history", (data) => {
  if (activeConversation?.type === "global") {
    renderHistory(data.messages, (msg) => msg.sender_id === currentUserId);
  }
});

socket.on("new_global_message", (msg) => {
  if (activeConversation?.type === "global") {
    appendMessage(msg, msg.sender_id === currentUserId);
  }
});

socket.on("dm_history", (data) => {
  if (activeConversation?.type === "dm" && activeConversation.userId === data.other_user_id) {
    renderHistory(data.messages, (msg) => msg.sender_id === currentUserId);
  }
});

socket.on("new_dm", (msg) => {
  const otherId = msg.sender_id === currentUserId ? msg.receiver_id : msg.sender_id;
  if (activeConversation?.type === "dm" && activeConversation.userId === otherId) {
    appendMessage(msg, msg.sender_id === currentUserId);
    if (msg.sender_id !== currentUserId) {
      socket.emit("mark_dm_read", { sender_id: msg.sender_id });
    }
  }
});

socket.on("dm_read_receipt", (data) => {
  console.log("Messages read:", data.message_ids);
});

socket.on("group_history", (data) => {
  if (activeConversation?.type === "group" && activeConversation.groupId === data.group_id) {
    renderHistory(data.messages, (msg) => msg.sender_id === currentUserId);
  }
});

socket.on("new_group_message", (msg) => {
  if (activeConversation?.type === "group" && activeConversation.groupId === msg.group_id) {
    appendMessage(msg, msg.sender_id === currentUserId);
  } else {
    // Not currently viewing this group -> refresh sidebar unread counts
    socket.emit("get_my_groups");
  }
});