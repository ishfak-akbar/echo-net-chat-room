const socket = io({ withCredentials: true });

let actions = parseInt(localStorage.getItem("admin_actions") || "0");
document.getElementById("s-actions").textContent = actions;

function log(text) {
  const box = document.getElementById("log");
  const placeholder = box.querySelector(".log-m");
  if (placeholder && placeholder.textContent === "Waiting for activity...") {
    box.innerHTML = "";
  }
  const now = new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  const row = document.createElement("div");
  row.className = "log-row";
  row.innerHTML = `<span class="log-t">${now}</span><span class="log-m">${text}</span>`;
  box.appendChild(row);
  box.scrollTop = box.scrollHeight;
}

function bumpActions() {
  actions++;
  localStorage.setItem("admin_actions", actions);
  document.getElementById("s-actions").textContent = actions;
}

// ---------- Online users ----------
socket.on("online_users_snapshot", (data) => {
  const list = document.getElementById("admin-users");
  const online = data.users.filter((u) => u.id !== MY_ID);
  document.getElementById("s-online").textContent = online.length;

  if (!online.length) {
    list.innerHTML = '<li class="empty">No other users online</li>';
    return;
  }

  list.innerHTML = "";
  online.forEach((u) => {
    const li = document.createElement("li");
    li.id = `auser-${u.id}`;
    li.innerHTML = `
      <span class="udot"></span>
      <span style="font-weight:500">${u.username}</span>
      <div class="actions">
        <button class="bkick" onclick="doKick(${u.id}, '${u.username}')">Kick</button>
        <button class="bban" onclick="doBan(${u.id}, '${u.username}')">Ban</button>
      </div>`;
    list.appendChild(li);
  });
});

// ---------- Banned users ----------
socket.on("banned_users", (data) => {
  const list = document.getElementById("ban-list");
  if (!data.bans.length) {
    list.innerHTML = '<li class="empty">No banned users</li>';
    return;
  }
  list.innerHTML = "";
  data.bans.forEach((b) => {
    const li = document.createElement("li");
    li.id = `buser-${b.user_id}`;
    li.innerHTML = `
      <span class="bdot"></span>
      <span style="font-weight:500">${b.username}</span>
      <div class="actions">
        <button class="bunban" onclick="doUnban(${b.user_id}, '${b.username}')">Unban</button>
      </div>`;
    list.appendChild(li);
  });
});

// ---------- Stats ----------
socket.on("admin_stats", (stats) => {
  document.getElementById("s-online").textContent = stats.online_users;
  document.getElementById("s-bc").textContent = stats.total_broadcasts;
});

// ---------- Broadcasts ----------
socket.on("broadcast_history", (data) => {
  data.broadcasts.forEach((b) => log(`📢 ${b.content}`));
});

socket.on("new_broadcast", (b) => {
  log(`📢 Broadcast: ${b.content}`);
  socket.emit("get_admin_stats");
});

function doBroadcast() {
  const msg = document.getElementById("bc-msg").value.trim();
  if (!msg) return;
  socket.emit("send_broadcast", { content: msg });
  document.getElementById("bc-msg").value = "";
}

// ---------- Actions: kick / ban / unban ----------
socket.on("admin_action", (data) => {
  if (data.action === "kick") {
    log(`⚠️ Kicked ${data.username}`);
    document.getElementById(`auser-${data.user_id}`)?.remove();
  } else if (data.action === "ban") {
    log(`🚫 Banned ${data.username}${data.reason ? " (" + data.reason + ")" : ""}`);
    document.getElementById(`auser-${data.user_id}`)?.remove();
  } else if (data.action === "unban") {
    log(`✅ Unbanned ${data.username}`);
    const li = document.getElementById(`buser-${data.user_id}`);
    if (li) li.remove();
    const list = document.getElementById("ban-list");
    if (!list.children.length) list.innerHTML = '<li class="empty">No banned users</li>';
  }
  socket.emit("get_admin_stats");
  socket.emit("get_banned_users");
});

function doKick(userId, username) {
  if (!confirm(`Kick ${username} from the chat?`)) return;
  socket.emit("kick_user", { user_id: userId });
  bumpActions();
}

function doBan(userId, username) {
  if (!confirm(`Permanently ban ${username}?`)) return;
  socket.emit("ban_user", { user_id: userId });
  bumpActions();
}

function doUnban(userId, username) {
  if (!confirm(`Unban ${username}?`)) return;
  socket.emit("unban_user", { user_id: userId });
  bumpActions();
}

socket.on("error", (data) => {
  alert(data.message);
});

socket.on("disconnect", (reason) => {
  if (reason === "io server disconnect") {
    window.location.href = "/login";
  }
});

// ---------- Logout ----------
document.getElementById("logout-link").addEventListener("click", async (e) => {
  e.preventDefault();
  await fetch("/auth/logout", { method: "POST" });
  window.location.href = "/login";
});

// ---------- Initial load ----------
socket.emit("get_admin_stats");
socket.emit("get_banned_users");
socket.emit("get_broadcast_history", { limit: 20 });