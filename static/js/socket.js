const socket = io({ withCredentials: true });

socket.on("connect_error", (err) => {
  console.error("Socket connection failed:", err.message);
});

socket.on("disconnect", (reason) => {
  console.warn("Socket disconnected:", reason);
});