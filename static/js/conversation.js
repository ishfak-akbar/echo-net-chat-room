let activeConversation = null;

const chatMainEl = document.getElementById("chat-main");

function renderChatHeader(title, avatarHtml) {
  return `
    <div class="chat-header">
      <div class="user-avatar small">${avatarHtml}</div>
      <div class="chat-header-title">${title}</div>
    </div>
  `;
}

function renderMessagesShell() {
  return `
    <div id="messages-container" class="messages-container"></div>
    <form id="message-form" class="message-form">
      <label class="attach-btn" title="Attach image">
        <i class="fa-solid fa-paperclip"></i>
        <input type="file" id="image-input" accept="image/*" hidden>
      </label>
      <input type="text" id="message-input" placeholder="Type a message..." autocomplete="off">
      <button type="submit" class="send-btn"><i class="fa-solid fa-paper-plane"></i></button>
    </form>
  `;
}

function openGlobalChat() {
  activeConversation = { type: "global" };
  chatMainEl.innerHTML =
    renderChatHeader("Global Chat", '<i class="fa-solid fa-globe"></i>') +
    renderMessagesShell();
  bindMessageForm();
  socket.emit("get_global_history", { limit: 50 });
}

function openDM(userId, username, profilePic) {
  activeConversation = { type: "dm", userId, username };
  const avatarHtml = profilePic
    ? `<img src="${profilePic}" alt="">`
    : '<i class="fa-solid fa-user"></i>';
  chatMainEl.innerHTML = renderChatHeader(username, avatarHtml) + renderMessagesShell();
  bindMessageForm();
  socket.emit("get_dm_history", { other_user_id: userId, limit: 50 });
  socket.emit("mark_dm_read", { sender_id: userId });
}

function openGroup(groupId, groupName) {
  activeConversation = { type: "group", groupId, name: groupName };
  chatMainEl.innerHTML =
    renderChatHeader(groupName, '<i class="fa-solid fa-users"></i>') + renderMessagesShell();
  bindMessageForm();
  socket.emit("get_group_history", { group_id: groupId, limit: 50 });
  socket.emit("mark_group_read", { group_id: groupId });
}

function bindMessageForm() {
  const form = document.getElementById("message-form");
  const textInput = document.getElementById("message-input");
  const imageInput = document.getElementById("image-input");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const content = textInput.value.trim();
    const file = imageInput.files[0];
    let imageUrl = null;

    if (file) {
      imageUrl = await uploadChatImage(file);
      if (!imageUrl) return;
    }

    if (!content && !imageUrl) return;

    if (activeConversation.type === "global") {
      socket.emit("send_global_message", { content, image_url: imageUrl });
    } else if (activeConversation.type === "dm") {
      socket.emit("send_dm", {
        receiver_id: activeConversation.userId,
        content,
        image_url: imageUrl,
      });
    } else if (activeConversation.type === "group") {
      socket.emit("send_group_message", {
        group_id: activeConversation.groupId,
        content,
        image_url: imageUrl,
      });
    }

    textInput.value = "";
    imageInput.value = "";
  });
}

async function uploadChatImage(file) {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/uploads/chat-image", { method: "POST", body: formData });
    const data = await res.json();
    if (!data.success) {
      alert(data.message || "Image upload failed.");
      return null;
    }
    return data.image_url;
  } catch (err) {
    alert("Image upload failed.");
    return null;
  }
}

document.getElementById("global-chat-tab").addEventListener("click", openGlobalChat);