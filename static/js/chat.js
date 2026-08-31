const socket = io({ withCredentials: true });

  let mode = null;
  let dmTarget = null;
  let groupTarget = null;

  const conversations = {};
  const groupConversations = {};
  const globalConversation = [];

  let onlineUsersList = [];
  let allUsersList = [];
  let unreadCounts = {};
  let myGroups = [];
  let groupUnreadCounts = {};
  let broadcastHistory = [];

  const dpCache = {};

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
  }

  function avatarInner(user) {
    if (user.profile_pic) {
      return `<img src="${user.profile_pic}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
    }
    return escapeHtml((user.username || "?")[0].toUpperCase());
  }

  function anyUnread() {
    return Object.values(unreadCounts).some((c) => c > 0);
  }
  function anyGroupUnread() {
    return Object.values(groupUnreadCounts).some((c) => c > 0);
  }

  function updateDots() {
    document.getElementById("dot-all").style.display = anyUnread() ? "inline-block" : "none";
    document.getElementById("dot-groups").style.display = anyGroupUnread() ? "inline-block" : "none";
  }

  // ---------- Tabs ----------
  function setActiveTab(id) {
    ["tab-online", "tab-all", "tab-groups"].forEach((t) =>
      document.getElementById(t).classList.toggle("active", t === id)
    );
  }

  function showOnline() {
    setActiveTab("tab-online");
    document.getElementById("user-list").style.display = "block";
    document.getElementById("all-user-list").style.display = "none";
    document.getElementById("groups-section").style.display = "none";
    document.getElementById("search-list").style.display = "none";
    renderUserList("user-list", onlineUsersList);
  }

  function showAll() {
    setActiveTab("tab-all");
    document.getElementById("user-list").style.display = "none";
    document.getElementById("all-user-list").style.display = "block";
    document.getElementById("groups-section").style.display = "none";
    document.getElementById("search-list").style.display = "none";
    socket.emit("get_all_users");
    renderUserList("all-user-list", allUsersList);
  }

  function showGroups() {
    setActiveTab("tab-groups");
    document.getElementById("user-list").style.display = "none";
    document.getElementById("all-user-list").style.display = "none";
    document.getElementById("groups-section").style.display = "block";
    document.getElementById("search-list").style.display = "none";
    socket.emit("get_my_groups");
    renderGroupSidebarList();
  }

  // ---------- User list rendering ----------
  function renderUserList(containerId, users) {
    const el = document.getElementById(containerId);
    if (!users || users.length === 0) {
      el.innerHTML = `<div style="padding:24px;text-align:center;color:var(--muted);font-size:13px;">No users found</div>`;
      return;
    }
    el.innerHTML = users
      .map((u) => {
        const unread = unreadCounts[u.id] || 0;
        const isActive = mode === "dm" && dmTarget && dmTarget.id === u.id;
        return `
        <div class="user-item ${isActive ? "active" : ""}" data-user-id="${u.id}">
          <div class="avatar">${avatarInner(u)}</div>
          <div class="user-info">
            <div class="user-name">${escapeHtml(u.username)}</div>
            <div class="last-msg">${lastMessagePreview[u.id] ? escapeHtml(lastMessagePreview[u.id]) : (u.is_online ? "Online" : "Offline")}</div>
          </div>
          ${unread > 0 ? `<span class="unread-badge">${unread}</span>` : ""}
        </div>`;
      })
      .join("");

    el.querySelectorAll(".user-item").forEach((item) => {
      item.addEventListener("click", () => {
        const id = parseInt(item.dataset.userId, 10);
        const user =
          onlineUsersList.find((u) => u.id === id) ||
          allUsersList.find((u) => u.id === id);
        if (user) openDM(user);
      });
    });
  }

  // ---------- Search ----------
  function onSearch() {
    const q = document.getElementById("search-input").value.trim().toLowerCase();
    const clearBtn = document.getElementById("search-clear");
    const searchListEl = document.getElementById("search-list");

    if (!q) {
      clearBtn.style.display = "none";
      searchListEl.style.display = "none";
      document.getElementById("user-list").style.display =
        document.getElementById("tab-online").classList.contains("active") ? "block" : "none";
      document.getElementById("all-user-list").style.display =
        document.getElementById("tab-all").classList.contains("active") ? "block" : "none";
      return;
    }

    clearBtn.style.display = "inline";
    document.getElementById("user-list").style.display = "none";
    document.getElementById("all-user-list").style.display = "none";
    document.getElementById("groups-section").style.display = "none";
    searchListEl.style.display = "block";

    const pool = allUsersList.length ? allUsersList : onlineUsersList;
    const matches = pool.filter((u) => u.username.toLowerCase().includes(q));
    renderUserList("search-list", matches);
  }

  function clearSearch() {
    document.getElementById("search-input").value = "";
    onSearch();
  }

  // ---------- Chat header / empty state helpers ----------
  function showChatUI(title) {
    document.getElementById("empty-state").style.display = "none";
    document.getElementById("chat-header").style.display = "flex";
    document.getElementById("messages").style.display = "flex";
    document.getElementById("input-row").style.display = "flex";
    document.getElementById("chat-title").textContent = title;
    document.getElementById("msg-input").disabled = false;
    document.getElementById("msg-input").placeholder = "Type a message...";
    document.getElementById("attach-btn").disabled = false;
    document.getElementById("send-btn").disabled = false;
    document.getElementById("msg-input").focus();
  }

  function updateRightPanel(name, statusText, avatarHtml) {
    document.getElementById("right-name").textContent = name;
    document.getElementById("right-status").textContent = statusText;
    document.getElementById("right-avatar").innerHTML = avatarHtml;
  }

  // ---------- Global Chat ----------
  function openGlobal() {
    mode = "global";
    dmTarget = null;
    groupTarget = null;
    document.querySelectorAll(".global-link").forEach((l) => l.classList.remove("active"));
    document.getElementById("global-btn").classList.add("active");

    showChatUI("Global Chat");
    updateRightPanel("Global Chat", "Everyone on EchoNet", `<i class="fa-solid fa-earth-americas"></i>`);

    renderMessages(globalConversation);
    socket.emit("get_global_history", { limit: 50 });
  }

  function renderMessages(list) {
    const el = document.getElementById("messages");
    el.innerHTML = list
      .map((m) => {
        if (m.type === "broadcast") {
          return `<div class="msg msg-broadcast"><i class="fa-solid fa-bullhorn"></i> ${escapeHtml(m.content)}</div>`;
        }
        const mine = m.sender_id === MY_ID;
        const cls = mode === "global"
          ? mine ? "msg-global-mine" : "msg-global"
          : mine ? "msg-sent" : "msg-recv";

        const senderLine =
          mode === "global" && !mine
            ? `<div class="msg-sender">${escapeHtml(m.sender_username || "")}</div>`
            : "";

        const imgHtml = m.image_url
          ? `<div class="msg-img-bubble" onclick="openLightbox('${m.image_url}')"><img src="${m.image_url}"></div>`
          : "";

        const textHtml = m.content ? `<div>${escapeHtml(m.content)}</div>` : "";
        const time = m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";

        return `<div class="msg ${cls}">${senderLine}${imgHtml}${textHtml}<div class="msg-footer">${time}</div></div>`;
      })
      .join("");
    el.scrollTop = el.scrollHeight;
    updateSharedMediaFromList(list);
  }

  function openLightbox(url) {
    document.getElementById("lightbox-img").src = url;
    document.getElementById("lightbox").classList.add("show");
  }
  function closeLightbox() {
    document.getElementById("lightbox").classList.remove("show");
  }

  // ---------- Socket events: presence ----------
  socket.on("online_users_snapshot", (data) => {
    onlineUsersList = data.users.filter((u) => u.id !== MY_ID);
    if (document.getElementById("user-list").style.display !== "none") {
      renderUserList("user-list", onlineUsersList);
    }
  });

  socket.on("presence_update", (data) => {
    const idx = onlineUsersList.findIndex((u) => u.id === data.user_id);
    if (data.is_online) {
      if (idx === -1) {
        onlineUsersList.push({ id: data.user_id, username: data.username, profile_pic: null, is_online: true });
      }
    } else if (idx !== -1) {
      onlineUsersList.splice(idx, 1);
    }
    const allIdx = allUsersList.findIndex((u) => u.id === data.user_id);
    if (allIdx !== -1) allUsersList[allIdx].is_online = data.is_online;

    if (document.getElementById("tab-online").classList.contains("active")) {
      renderUserList("user-list", onlineUsersList);
    } else if (document.getElementById("tab-all").classList.contains("active")) {
      renderUserList("all-user-list", allUsersList);
    }
  });

  socket.on("all_users", (data) => {
    allUsersList = data.users;
    if (document.getElementById("all-user-list").style.display !== "none") {
      renderUserList("all-user-list", allUsersList);
    }
  });

  // ---------- Image attach handling ----------
let pendingImageFile = null;

function onImageSelected(input) {
  const file = input.files[0];
  if (!file) return;
  pendingImageFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    document.getElementById("img-preview-thumb").src = e.target.result;
    document.getElementById("img-preview-bar").style.display = "flex";
  };
  reader.readAsDataURL(file);
}

function cancelImageAttach() {
  pendingImageFile = null;
  document.getElementById("img-attach-input").value = "";
  document.getElementById("img-preview-bar").style.display = "none";
}

async function uploadPendingImage() {
  if (!pendingImageFile) return null;
  const formData = new FormData();
  formData.append("file", pendingImageFile);
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

// ---------- Unified send ----------
async function sendMsg() {
  const input = document.getElementById("msg-input");
  const content = input.value.trim();

  let imageUrl = null;
  if (pendingImageFile) {
    imageUrl = await uploadPendingImage();
    if (!imageUrl) return;
  }

  if (!content && !imageUrl) return;
  if (mode === "broadcast") {
    if (!IS_ADMIN || !content) return;
    socket.emit("send_broadcast", { content });
    input.value = "";
    return;
  }
  if (mode === "global") {
    socket.emit("send_global_message", { content, image_url: imageUrl });
  } else if (mode === "dm" && dmTarget) {
    socket.emit("send_dm", { receiver_id: dmTarget.id, content, image_url: imageUrl });
  } else if (mode === "group" && groupTarget) {
    socket.emit("send_group_message", { group_id: groupTarget.id, content, image_url: imageUrl });
  }

  input.value = "";
  cancelImageAttach();
}

document.getElementById("msg-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    sendMsg();
  }
});

// ---------- Direct Messages ----------
const lastMessagePreview = {};

function updateChatPreview(userId, content, imageUrl) {
  lastMessagePreview[userId] = imageUrl ? "📷 Photo" : (content || "");
  if (document.getElementById("tab-online").classList.contains("active")) {
    renderUserList("user-list", onlineUsersList);
  } else if (document.getElementById("tab-all").classList.contains("active")) {
    renderUserList("all-user-list", allUsersList);
  }
}

function openDM(user) {
  mode = "dm";
  dmTarget = user;
  groupTarget = null;
  document.querySelectorAll(".global-link").forEach((l) => l.classList.remove("active"));

  showChatUI(user.username);
  updateRightPanel(user.username, user.is_online ? "Online" : "Offline", avatarInner(user));

  if (!conversations[user.id]) conversations[user.id] = [];
  renderMessages(conversations[user.id]);

  socket.emit("get_dm_history", { other_user_id: user.id, limit: 50 });
  socket.emit("mark_dm_read", { sender_id: user.id });
  unreadCounts[user.id] = 0;
  updateDots();

  if (document.getElementById("tab-online").classList.contains("active")) {
    renderUserList("user-list", onlineUsersList);
  } else if (document.getElementById("tab-all").classList.contains("active")) {
    renderUserList("all-user-list", allUsersList);
  }
}

socket.on("dm_history", (data) => {
  conversations[data.other_user_id] = data.messages;
  if (mode === "dm" && dmTarget && dmTarget.id === data.other_user_id) {
    renderMessages(conversations[data.other_user_id]);
  }
});

socket.on("new_dm", (msg) => {
  const otherId = msg.sender_id === MY_ID ? msg.receiver_id : msg.sender_id;
  if (!conversations[otherId]) conversations[otherId] = [];
  conversations[otherId].push(msg);

  updateChatPreview(otherId, msg.content, msg.image_url);

  if (mode === "dm" && dmTarget && dmTarget.id === otherId) {
    renderMessages(conversations[otherId]);
    if (msg.sender_id !== MY_ID) {
      socket.emit("mark_dm_read", { sender_id: otherId });
    }
  } else if (msg.sender_id !== MY_ID) {
    unreadCounts[otherId] = (unreadCounts[otherId] || 0) + 1;
    updateDots();
  }
});

  // ---------- Socket events: global chat ----------
  socket.on("global_history", (data) => {
    globalConversation.length = 0;
    globalConversation.push(...data.messages);
    if (mode === "global") renderMessages(globalConversation);
  });

  socket.on("new_global_message", (msg) => {
    globalConversation.push(msg);
    if (mode === "global") renderMessages(globalConversation);
  });

  socket.on("error", (data) => {
    console.error("Server error:", data.message);
  });

  document.getElementById("lightbox-close");
  document.getElementById("lightbox").addEventListener("click", (e) => {
    if (e.target.id === "lightbox") closeLightbox();
  });

  openGlobal();

  // ---------- Groups ----------
function renderGroupSidebarList() {
  const el = document.getElementById("group-list");
  if (!myGroups || myGroups.length === 0) {
    el.innerHTML = `<div style="padding:16px 18px;text-align:center;color:var(--muted);font-size:13px;">No groups yet</div>`;
    return;
  }
  el.innerHTML = myGroups
    .map((g) => {
      const unread = groupUnreadCounts[g.id] || 0;
      const isActive = mode === "group" && groupTarget && groupTarget.id === g.id;
      return `
      <div class="group-item ${isActive ? "active" : ""}" data-group-id="${g.id}">
        <div class="avatar">${escapeHtml(g.name[0].toUpperCase())}</div>
        <div class="user-info">
          <div class="user-name">${escapeHtml(g.name)}</div>
          <div class="last-msg">${g.member_ids.length} members</div>
        </div>
        ${unread > 0 ? `<span class="unread-badge">${unread}</span>` : ""}
      </div>`;
    })
    .join("");

  el.querySelectorAll(".group-item").forEach((item) => {
    item.addEventListener("click", () => {
      const id = parseInt(item.dataset.groupId, 10);
      const group = myGroups.find((g) => g.id === id);
      if (group) openGroup(group);
    });
  });
}

function openGroup(group) {
  mode = "group";
  groupTarget = group;
  dmTarget = null;
  document.querySelectorAll(".global-link").forEach((l) => l.classList.remove("active"));

  showChatUI(group.name);
  updateRightPanel(group.name, `${group.member_ids.length} members`, `<i class="fa-solid fa-users"></i>`);

  if (!groupConversations[group.id]) groupConversations[group.id] = [];
  renderMessages(groupConversations[group.id]);

  socket.emit("get_group_history", { group_id: group.id, limit: 50 });
  socket.emit("mark_group_read", { group_id: group.id });
  groupUnreadCounts[group.id] = 0;
  updateDots();
  renderGroupSidebarList();
}

function openGroupModal() {
  document.getElementById("g-name").value = "";
  document.getElementById("group-overlay").classList.add("show");
  socket.emit("get_all_users");
  renderMemberCheckboxes();
}

function closeGroupModal() {
  document.getElementById("group-overlay").classList.remove("show");
}

function renderMemberCheckboxes() {
  const el = document.getElementById("member-list");
  if (!allUsersList || allUsersList.length === 0) {
    el.innerHTML = `<div style="padding:12px;text-align:center;color:var(--muted);font-size:13px;">No other users to add</div>`;
    return;
  }
  el.innerHTML = allUsersList
    .map(
      (u) => `
      <label style="display:flex;align-items:center;gap:10px;padding:8px 4px;cursor:pointer;font-size:13.5px;">
        <input type="checkbox" value="${u.id}" style="accent-color:var(--accent-end);width:16px;height:16px;">
        <span>${escapeHtml(u.username)}</span>
      </label>`
    )
    .join("");
}

function submitCreateGroup() {
  const name = document.getElementById("g-name").value.trim();
  const checked = Array.from(
    document.querySelectorAll("#member-list input[type=checkbox]:checked")
  ).map((cb) => parseInt(cb.value, 10));

  if (!name || checked.length === 0) {
    alert("Enter a group name and select at least one member.");
    return;
  }

  socket.emit("create_group", { name, member_ids: checked });
}

socket.on("my_groups", (data) => {
  myGroups = data.groups;
  data.groups.forEach((g) => {
    groupUnreadCounts[g.id] = g.unread_count;
  });
  updateDots();
  if (document.getElementById("groups-section").style.display !== "none") {
    renderGroupSidebarList();
  }
});

socket.on("group_created", () => {
  closeGroupModal();
  socket.emit("get_my_groups");
});

socket.on("group_history", (data) => {
  groupConversations[data.group_id] = data.messages;
  if (mode === "group" && groupTarget && groupTarget.id === data.group_id) {
    renderMessages(groupConversations[data.group_id]);
  }
});

socket.on("new_group_message", (msg) => {
  if (!groupConversations[msg.group_id]) groupConversations[msg.group_id] = [];
  groupConversations[msg.group_id].push(msg);

  if (mode === "group" && groupTarget && groupTarget.id === msg.group_id) {
    renderMessages(groupConversations[msg.group_id]);
    if (msg.sender_id !== MY_ID) {
      socket.emit("mark_group_read", { group_id: msg.group_id });
    }
  } else if (msg.sender_id !== MY_ID) {
    groupUnreadCounts[msg.group_id] = (groupUnreadCounts[msg.group_id] || 0) + 1;
    updateDots();
    renderGroupSidebarList();
  }
});

// ---------- Shared Media ----------
function updateSharedMediaFromList(list) {
  const media = list.filter((m) => m.image_url);
  const emptyEl = document.getElementById("shared-media-empty");
  const gridEl = document.getElementById("shared-media-grid");

  if (media.length === 0) {
    emptyEl.style.display = "flex";
    gridEl.style.display = "none";
    gridEl.innerHTML = "";
    return;
  }

  emptyEl.style.display = "none";
  gridEl.style.display = "grid";
  gridEl.innerHTML = media
    .map(
      (m) => `
      <div class="media-thumb" onclick="openLightbox('${m.image_url}')">
        <img src="${m.image_url}">
      </div>`
    )
    .join("");
}

// ---------- Broadcasts ----------
function openBroadcasts() {
  mode = "broadcast";
  dmTarget = null;
  groupTarget = null;
  document.querySelectorAll(".global-link").forEach((l) => l.classList.remove("active"));
  document.getElementById("broadcast-btn").classList.add("active");

  document.getElementById("empty-state").style.display = "none";
  document.getElementById("chat-header").style.display = "flex";
  document.getElementById("messages").style.display = "flex";
  document.getElementById("chat-title").textContent = "Broadcasts";

  if (IS_ADMIN) {
    document.getElementById("input-row").style.display = "flex";
    document.getElementById("msg-input").disabled = false;
    document.getElementById("msg-input").placeholder = "Send an announcement to everyone...";
    document.getElementById("attach-btn").disabled = true;
    document.getElementById("send-btn").disabled = false;
  } else {
    document.getElementById("input-row").style.display = "none";
  }

  updateRightPanel("Broadcasts", "Announcements from admins", `<i class="fa-solid fa-bullhorn"></i>`);
  renderMessages(broadcastHistory.map((b) => ({ type: "broadcast", content: b.content })));
  document.getElementById("broadcast-dot").style.display = "none";

  socket.emit("get_broadcast_history", { limit: 30 });
}

socket.on("broadcast_history", (data) => {
  broadcastHistory = data.broadcasts;
  if (mode === "broadcast") {
    renderMessages(broadcastHistory.map((b) => ({ type: "broadcast", content: b.content })));
  }
});

socket.on("new_broadcast", (b) => {
  broadcastHistory.push(b);
  if (mode === "broadcast") {
    renderMessages(broadcastHistory.map((x) => ({ type: "broadcast", content: x.content })));
  } else {
    document.getElementById("broadcast-dot").style.display = "inline-block";
  }
});