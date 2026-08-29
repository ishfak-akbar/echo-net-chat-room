const socket = io({ withCredentials: true });
  const ME = "{{ current_user.username }}";
  const MY_ID = {{ current_user.id }};
  const MY_DP = {{ (current_user.profile_pic or "") | tojson }};

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
            <div class="last-msg">${u.is_online ? "Online" : "Offline"}</div>
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
    document.getElementById("attach-btn").disabled = false;
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