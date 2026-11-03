import { useEffect, useState } from "react";
import "./Dashboard.css";

import api from "../services/api";

import ChatList from "../components/ChatList";
import MessageList from "../components/MessageList";
import MessageInput from "../components/MessageInput";

function Dashboard() {
  const [user, setUser] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [selectedRoom, setSelectedRoom] = useState(null);
  const [activeTab, setActiveTab] = useState("chats");

  const [showGroupForm, setShowGroupForm] = useState(false);
  const [groupName, setGroupName] = useState("");
  const [availableUsers, setAvailableUsers] = useState([]);
  const [selectedMemberIds, setSelectedMemberIds] = useState([]);
  const [groupError, setGroupError] = useState("");
  const [groupLoading, setGroupLoading] = useState(false);

  const [messages, setMessages] = useState([]);
  const [editingMessage, setEditingMessage] = useState(null);
  const [editContent, setEditContent] = useState("");
  const [socket, setSocket] = useState(null);
  const [notificationSocket, setNotificationSocket] = useState(null);

  const [meetings, setMeetings] = useState([]);
  const [meetingsLoading, setMeetingsLoading] = useState(false);
  const [meetingsError, setMeetingsError] = useState("");

  const [showAccount, setShowAccount] = useState(false);
  const [accountMode, setAccountMode] = useState("profile");
  const [accountError, setAccountError] = useState("");
  const [accountSuccess, setAccountSuccess] = useState("");

  const [profileForm, setProfileForm] = useState({
    name: "",
    email: "",
  });

  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
  });

  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState("");
  const [avatarError, setAvatarError] = useState("");
  const [avatarSuccess, setAvatarSuccess] = useState("");

  const handleStartEdit = (message) => {
    setEditingMessage(message);
    setEditContent(message.content);
  };

  const getCurrentUser = async () => {
    try {
      const response = await api.get("/users/me");
      setUser(response.data);
    } catch (error) {
      console.error(
        "CURRENT USER ERROR:",
        error.response?.data || error.message,
      );
    }
  };

  const getRooms = async () => {
    try {
      const response = await api.get("/chatroom");

      console.log("ROOM LIST:", JSON.stringify(response.data, null, 2));

      setRooms(response.data);
    } catch (error) {
      console.error("GET ROOMS ERROR:", error.response?.data || error.message);
    }
  };

  // Fetch meetings belonging to the logged-in user.
  const getMyMeetings = async () => {
    setMeetingsLoading(true);
    setMeetingsError("");

    try {
      const response = await api.get("/meetings/my-meetings");

      console.log("MY MEETINGS RESPONSE:", response.data);

      const data = response.data;

      // Support either a direct list or an object containing a meetings list.
      if (Array.isArray(data)) {
        setMeetings(data);
      } else if (Array.isArray(data?.meetings)) {
        setMeetings(data.meetings);
      } else {
        setMeetings([]);
      }
    } catch (error) {
      console.error(
        "GET MEETINGS ERROR:",
        error.response?.data || error.message,
      );

      setMeetingsError(
        error.response?.data?.detail || "Could not load meetings.",
      );
    } finally {
      setMeetingsLoading(false);
    }
  };

  const getAvailableUsers = async () => {
    try {
      const response = await api.get("/users");

      setAvailableUsers(
        response.data.filter((availableUser) => availableUser.id !== user?.id),
      );
    } catch (error) {
      console.error("GET USERS ERROR:", error.response?.data || error.message);

      setGroupError("Could not load users. Please try again.");
    }
  };

  // Load the user, chat rooms, and meetings when the dashboard opens.
  useEffect(() => {
    getCurrentUser();
    getRooms();
    getMyMeetings();
  }, []);

  // Connect to the selected chat room's WebSocket.
  useEffect(() => {
    if (!selectedRoom?.id) {
      return;
    }

    const token = localStorage.getItem("token");

    if (!token) {
      console.error("No authentication token found.");
      return;
    }

    const ws = new WebSocket(
      `ws://127.0.0.1:8000/ws/${selectedRoom.id}?token=${encodeURIComponent(token)}`,
    );

    ws.onopen = () => {
      console.log("WebSocket connected to room:", selectedRoom.id);
    };

    ws.onmessage = (event) => {
      try {
        const newMessage = JSON.parse(event.data);

        if (newMessage.error) {
          console.error("WebSocket message error:", newMessage.error);
          return;
        }

        setMessages((previousMessages) => {
          const alreadyExists = previousMessages.some(
            (message) => message.id === newMessage.id,
          );

          if (alreadyExists) {
            return previousMessages;
          }

          return [...previousMessages, newMessage];
        });

        setRooms((previousRooms) =>
          previousRooms
            .map((room) =>
              room.id === newMessage.room_id
                ? {
                    ...room,
                    last_message: newMessage.content,
                    last_message_at: newMessage.created_at,
                  }
                : room,
            )
            .sort(
              (a, b) =>
                new Date(b.last_message_at || 0) -
                new Date(a.last_message_at || 0),
            ),
        );
      } catch (error) {
        console.error("Could not process WebSocket message:", error);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected from room:", selectedRoom.id);
    };

    setSocket(ws);

    return () => {
      ws.close();

      setSocket((currentSocket) =>
        currentSocket === ws ? null : currentSocket,
      );
    };
  }, [selectedRoom?.id]);

  // Connect to notifications WebSocket.
  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) {
      console.error("No authentication token found.");
      return;
    }

    const ws = new WebSocket(
      `ws://127.0.0.1:8000/ws/notifications?token=${encodeURIComponent(token)}`,
    );

    ws.onopen = () => {
      console.log("Notification WebSocket connected");
    };

    ws.onmessage = (event) => {
      try {
        const notification = JSON.parse(event.data);

        if (notification.type !== "new_message") {
          return;
        }

        const newMessage = notification.message;
        const roomId = notification.room_id;

        setRooms((previousRooms) =>
          previousRooms
            .map((room) =>
              room.id === roomId
                ? {
                    ...room,
                    last_message: newMessage.content,
                    last_message_at: newMessage.created_at,
                  }
                : room,
            )
            .sort(
              (a, b) =>
                new Date(b.last_message_at || 0) -
                new Date(a.last_message_at || 0),
            ),
        );
      } catch (error) {
        console.error("Could not process notification:", error);
      }
    };

    ws.onerror = (error) => {
      console.error("Notification WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("Notification WebSocket disconnected");
    };

    setNotificationSocket(ws);

    return () => {
      ws.close();

      setNotificationSocket((currentSocket) =>
        currentSocket === ws ? null : currentSocket,
      );
    };
  }, []);

  const handleAddChat = async (email) => {
    try {
      const userResponse = await api.get("/users/search", {
        params: { email },
      });

      const foundUser = userResponse.data;

      const roomsResponse = await api.get("/chatroom");
      setRooms(roomsResponse.data);

      const existingRoom = roomsResponse.data.find(
        (room) => room.other_user_id === foundUser.id,
      );

      if (existingRoom) {
        await handleSelectRoom(existingRoom);
      } else {
        setSelectedRoom({
          id: null,
          other_user_id: foundUser.id,
          other_user_name: foundUser.name,
          other_user_email: foundUser.email,
        });

        setMessages([]);
        setEditingMessage(null);
        setEditContent("");
      }
    } catch (error) {
      throw error;
    }
  };

  const handleCreateGroup = async (event) => {
    event.preventDefault();
    setGroupError("");

    if (!groupName.trim()) {
      setGroupError("Please enter a group name.");
      return;
    }

    if (selectedMemberIds.length === 0) {
      setGroupError("Please select at least one other member.");
      return;
    }

    setGroupLoading(true);

    try {
      const response = await api.post("/chatroom/group", {
        name: groupName.trim(),
        member_ids: selectedMemberIds,
      });

      const roomsResponse = await api.get("/chatroom");
      setRooms(roomsResponse.data);

      const createdRoom = roomsResponse.data.find(
        (room) => room.id === response.data.id,
      );

      if (createdRoom) {
        setSelectedRoom(createdRoom);
        setMessages([]);
        setEditingMessage(null);
        setEditContent("");
      }

      setGroupName("");
      setSelectedMemberIds([]);
      setGroupError("");
      setShowGroupForm(false);
    } catch (error) {
      setGroupError(
        error.response?.data?.detail || "Could not create the group.",
      );
    } finally {
      setGroupLoading(false);
    }
  };

  const getMessages = async (roomId) => {
    try {
      const response = await api.post("/messages/getMessages", {
        room_id: roomId,
      });

      setMessages(response.data);
    } catch (error) {
      console.error(
        "GET MESSAGES ERROR:",
        error.response?.data || error.message,
      );

      setMessages([]);
    }
  };

  const handleSelectRoom = async (room) => {
    setSelectedRoom(room);
    setEditingMessage(null);
    setEditContent("");
    setMessages([]);

    await getMessages(room.id);
  };

  const handleOpenMeetingRoom = async (meeting) => {
    const roomId = meeting.room_id;

    if (!roomId) {
      alert("This meeting does not have an associated chat room.");
      return;
    }

    let room = rooms.find((item) => item.id === roomId);

    if (!room) {
      try {
        const response = await api.get("/chatroom");
        setRooms(response.data);

        room = response.data.find((item) => item.id === roomId);
      } catch (error) {
        console.error(
          "GET ROOMS ERROR:",
          error.response?.data || error.message,
        );
      }
    }

    if (room) {
      await handleSelectRoom(room);
      setActiveTab("chats");
    } else {
      alert("The chat room for this meeting could not be found.");
    }
  };

  const formatMeetingDate = (meetingDate) => {
    if (!meetingDate) {
      return "Date not available";
    }

    const date = new Date(meetingDate);

    if (Number.isNaN(date.getTime())) {
      return "Invalid meeting date";
    }

    return date.toLocaleString("en-PK", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Asia/Karachi",
    });
  };

  const handleDeleteChatForMe = async (roomId) => {
    try {
      await api.delete("/chatroom/delete", {
        data: { room_id: roomId },
      });

      setRooms((previousRooms) =>
        previousRooms.filter((room) => room.id !== roomId),
      );

      if (selectedRoom?.id === roomId) {
        setSelectedRoom(null);
        setMessages([]);
        setEditingMessage(null);
        setEditContent("");
      }
    } catch (error) {
      console.error(
        "DELETE CHAT ERROR:",
        error.response?.data || error.message,
      );
    }
  };

  const handleSendMessage = async (content) => {
    if (!selectedRoom) return;

    try {
      if (selectedRoom.id) {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
          alert(
            "Chat connection is not ready. Please wait a moment and try again.",
          );
          return;
        }

        socket.send(JSON.stringify({ content }));
        return;
      }

      const roomResponse = await api.post("/chatroom", {
        receiver_id: selectedRoom.other_user_id,
      });

      const roomId = roomResponse.data.id;

      const response = await api.post("/messages", {
        room_id: roomId,
        content,
      });

      const roomsResponse = await api.get("/chatroom");

      console.log(
        "CHAT ROOM RESPONSE:",
        JSON.stringify(roomsResponse.data, null, 2),
      );

      setRooms(roomsResponse.data);

      const updatedRoom = roomsResponse.data.find((room) => room.id === roomId);

      if (updatedRoom) {
        setSelectedRoom(updatedRoom);
      }

      setMessages((previousMessages) => [...previousMessages, response.data]);
    } catch (error) {
      console.error(
        "SEND MESSAGE ERROR:",
        error.response?.data || error.message,
      );

      alert(error.response?.data?.detail || "Could not send message.");
    }
  };

  const handleEditMessage = async () => {
    if (!editingMessage || !editContent.trim()) return;

    try {
      const response = await api.patch("/messages", {
        message_id: editingMessage.id,
        content: editContent,
      });

      setMessages((previousMessages) =>
        previousMessages.map((message) =>
          message.id === editingMessage.id ? response.data : message,
        ),
      );

      setEditingMessage(null);
      setEditContent("");
    } catch (error) {
      console.error(
        "EDIT MESSAGE ERROR:",
        error.response?.data || error.message,
      );
    }
  };

  const handleDeleteForMe = async (messageId) => {
    try {
      await api.delete("/messages/deleteForMe", {
        data: { message_ids: [messageId] },
      });

      setMessages((previousMessages) =>
        previousMessages.filter((message) => message.id !== messageId),
      );
    } catch (error) {
      console.error(
        "DELETE FOR ME ERROR:",
        error.response?.data || error.message,
      );
    }
  };

  const handleDeleteForEveryone = async (messageId) => {
    try {
      await api.delete("/messages/delete", {
        data: { message_ids: [messageId] },
      });

      setMessages((previousMessages) =>
        previousMessages.map((message) =>
          message.id === messageId
            ? {
                ...message,
                deleted_for_everyone_at: new Date().toISOString(),
              }
            : message,
        ),
      );
    } catch (error) {
      console.error(
        "DELETE FOR EVERYONE ERROR:",
        error.response?.data || error.message,
      );
    }
  };

  const openAccount = () => {
    setProfileForm({
      name: user?.name || "",
      email: user?.email || "",
    });

    setPasswordForm({
      current_password: "",
      new_password: "",
    });

    setAccountError("");
    setAccountSuccess("");
    setAccountMode("profile");
    setShowAccount(true);
  };

  const handleUpdateProfile = async (event) => {
    event.preventDefault();
    setAccountError("");
    setAccountSuccess("");

    try {
      const response = await api.patch("/users/me", profileForm);
      setUser(response.data);
      setAccountSuccess("Profile updated successfully.");
    } catch (error) {
      setAccountError(
        error.response?.data?.detail || "Could not update profile.",
      );
    }
  };

  const handleChangePassword = async (event) => {
    event.preventDefault();
    setAccountError("");
    setAccountSuccess("");

    try {
      const response = await api.patch("/users/me/password", passwordForm);

      setAccountSuccess(
        response.data.message || "Password changed successfully.",
      );

      setPasswordForm({
        current_password: "",
        new_password: "",
      });
    } catch (error) {
      setAccountError(
        error.response?.data?.detail || "Could not change password.",
      );
    }
  };

  const handleAvatarUpload = async (event) => {
    event.preventDefault();

    if (!avatarFile) {
      setAvatarError("Please select an image first.");
      return;
    }

    setAvatarError("");
    setAvatarSuccess("");

    const formData = new FormData();
    formData.append("file", avatarFile);

    try {
      const response = await api.post("/users/me/avatar", formData);

      setUser(response.data);
      setAvatarFile(null);
      setAvatarPreview("");
      setAvatarSuccess("Avatar updated successfully.");
    } catch (error) {
      setAvatarError(
        error.response?.data?.detail || "Could not upload avatar.",
      );
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    window.location.href = "/login";
  };

  return (
    <div className="messenger">
      <div className="navbar">
        <h2>Messenger</h2>

        <div className="navbar-user">
          {user && (
            <>
              {user.avatar_url ? (
                <img
                  src={`http://127.0.0.1:8000${user.avatar_url}`}
                  alt="Profile"
                  className="navbar-avatar"
                />
              ) : (
                <div className="navbar-avatar-placeholder">
                  {user.name?.charAt(0)?.toUpperCase() || "?"}
                </div>
              )}

              <span>{user.name}</span>
            </>
          )}

          <button
            type="button"
            onClick={openAccount}
            className="account-button"
          >
            Account
          </button>

          <button
            type="button"
            onClick={handleLogout}
            className="logout-button"
          >
            Logout
          </button>
        </div>
      </div>

      <nav className="dashboard-tabs" aria-label="Main navigation">
        <button
          type="button"
          className={activeTab === "chats" ? "active" : ""}
          onClick={() => setActiveTab("chats")}
          aria-current={activeTab === "chats" ? "page" : undefined}
        >
          <span aria-hidden="true">💬</span> Chats
        </button>

        <button
          type="button"
          className={activeTab === "meetings" ? "active" : ""}
          onClick={() => setActiveTab("meetings")}
          aria-current={activeTab === "meetings" ? "page" : undefined}
        >
          <span aria-hidden="true">📅</span> Meetings
          {meetings.length > 0 && (
            <span className="tab-count">{meetings.length}</span>
          )}
        </button>
      </nav>

      {showAccount && (
        <div className="account-overlay">
          <section className="account-panel">
            <div className="account-heading">
              <h2>Account settings</h2>

              <button
                type="button"
                onClick={() => setShowAccount(false)}
                className="account-close"
              >
                ×
              </button>
            </div>

            <div className="account-tabs">
              <button
                type="button"
                className={accountMode === "profile" ? "active" : ""}
                onClick={() => {
                  setAccountMode("profile");
                  setAccountError("");
                  setAccountSuccess("");
                }}
              >
                Edit profile
              </button>

              <button
                type="button"
                className={accountMode === "password" ? "active" : ""}
                onClick={() => {
                  setAccountMode("password");
                  setAccountError("");
                  setAccountSuccess("");
                }}
              >
                Change password
              </button>
            </div>

            <div className="avatar-section">
              <h3>Profile picture</h3>

              {avatarPreview ? (
                <img
                  src={avatarPreview}
                  alt="Avatar preview"
                  className="avatar-preview"
                />
              ) : user?.avatar_url ? (
                <img
                  src={`http://127.0.0.1:8000${user.avatar_url}`}
                  alt="Your avatar"
                  className="avatar-preview"
                />
              ) : (
                <div className="avatar-placeholder">
                  {user?.name?.charAt(0)?.toUpperCase() || "?"}
                </div>
              )}

              <form onSubmit={handleAvatarUpload}>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(event) => {
                    const file = event.target.files?.[0];

                    setAvatarError("");
                    setAvatarSuccess("");
                    setAvatarFile(file || null);
                    setAvatarPreview(file ? URL.createObjectURL(file) : "");
                  }}
                />

                <button type="submit" className="account-submit">
                  Upload avatar
                </button>
              </form>

              {avatarError && <p className="account-error">{avatarError}</p>}

              {avatarSuccess && (
                <p className="account-success">{avatarSuccess}</p>
              )}
            </div>

            {accountMode === "profile" ? (
              <form onSubmit={handleUpdateProfile}>
                <label>Name</label>

                <input
                  type="text"
                  value={profileForm.name}
                  required
                  onChange={(event) =>
                    setProfileForm({
                      ...profileForm,
                      name: event.target.value,
                    })
                  }
                />

                <label>Email</label>

                <input
                  type="email"
                  value={profileForm.email}
                  required
                  onChange={(event) =>
                    setProfileForm({
                      ...profileForm,
                      email: event.target.value,
                    })
                  }
                />

                <button type="submit" className="account-submit">
                  Save changes
                </button>
              </form>
            ) : (
              <form onSubmit={handleChangePassword}>
                <label>Current password</label>

                <input
                  type="password"
                  value={passwordForm.current_password}
                  required
                  onChange={(event) =>
                    setPasswordForm({
                      ...passwordForm,
                      current_password: event.target.value,
                    })
                  }
                />

                <label>New password</label>

                <input
                  type="password"
                  value={passwordForm.new_password}
                  minLength={8}
                  maxLength={72}
                  required
                  onChange={(event) =>
                    setPasswordForm({
                      ...passwordForm,
                      new_password: event.target.value,
                    })
                  }
                />

                <button type="submit" className="account-submit">
                  Change password
                </button>
              </form>
            )}

            {accountError && <p className="account-error">{accountError}</p>}

            {accountSuccess && (
              <p className="account-success">{accountSuccess}</p>
            )}
          </section>
        </div>
      )}

      {activeTab === "chats" ? (
        <div className="messenger-body">
          <aside>
            <ChatList
              rooms={rooms}
              selectedRoom={selectedRoom}
              onSelectRoom={handleSelectRoom}
              onAddChat={handleAddChat}
              onDeleteChat={handleDeleteChatForMe}
              onCreateGroup={handleCreateGroup}
              availableUsers={availableUsers}
              selectedMemberIds={selectedMemberIds}
              setSelectedMemberIds={setSelectedMemberIds}
              groupName={groupName}
              setGroupName={setGroupName}
              showGroupForm={showGroupForm}
              setShowGroupForm={setShowGroupForm}
              groupError={groupError}
              groupLoading={groupLoading}
              onLoadUsers={getAvailableUsers}
            />
          </aside>

          <main className="chat-main">
            {selectedRoom ? (
              <>
                <div className="chat-header">
                  <h2>
                    {selectedRoom.is_group
                      ? selectedRoom.name || "Unnamed group"
                      : selectedRoom.other_user_name}
                  </h2>

                  {selectedRoom.is_group ? (
                    <p>{selectedRoom.member_count} members</p>
                  ) : (
                    <p>{selectedRoom.other_user_email}</p>
                  )}
                </div>

                <MessageList
                  messages={messages}
                  currentUserId={user?.id}
                  onStartEdit={handleStartEdit}
                  onDeleteForMe={handleDeleteForMe}
                  onDeleteForEveryone={handleDeleteForEveryone}
                />

                <MessageInput
                  onSend={handleSendMessage}
                  editingMessage={editingMessage}
                  editContent={editContent}
                  setEditContent={setEditContent}
                  onEdit={handleEditMessage}
                  onCancelEdit={() => {
                    setEditingMessage(null);
                    setEditContent("");
                  }}
                />
              </>
            ) : (
              <div className="no-chat">
                <h2>Select a conversation</h2>
                <p>Choose a chat room from the list.</p>
              </div>
            )}
          </main>
        </div>
      ) : (
        <main className="meetings-page">
          <section className="meetings-section">
            <div className="meetings-heading">
              <div>
                <p className="meetings-eyebrow">YOUR SCHEDULE</p>
                <h2>My Meetings</h2>
                <p className="meetings-subtitle">
                  Meetings shared with you from your conversations.
                </p>
              </div>

              <button
                type="button"
                className="meetings-refresh"
                onClick={getMyMeetings}
                disabled={meetingsLoading}
              >
                <span aria-hidden="true">↻</span>{" "}
                {meetingsLoading ? "Refreshing..." : "Refresh"}
              </button>
            </div>

            {meetingsLoading && meetings.length === 0 && (
              <div className="meetings-state">
                <span className="meetings-state-icon" aria-hidden="true">
                  ◷
                </span>
                <h3>Loading your meetings</h3>
                <p>Please wait while we get your schedule.</p>
              </div>
            )}

            {meetingsError && (
              <div className="meetings-error" role="alert">
                <p>{meetingsError}</p>
                <button type="button" onClick={getMyMeetings}>
                  Try again
                </button>
              </div>
            )}

            {!meetingsLoading && !meetingsError && meetings.length === 0 && (
              <div className="meetings-state">
                <span className="meetings-state-icon" aria-hidden="true">
                  📅
                </span>
                <h3>No meetings yet</h3>
                <p>
                  When a meeting is identified in your conversations, it will
                  appear here.
                </p>
                <button type="button" onClick={() => setActiveTab("chats")}>
                  Go to chats
                </button>
              </div>
            )}

            {meetings.length > 0 && (
              <div className="meetings-list">
                {meetings.map((meeting) => (
                  <article className="meeting-card" key={meeting.id}>
                    <div className="meeting-card-topline">
                      <span className="meeting-icon" aria-hidden="true">
                        📅
                      </span>
                      <span className="meeting-label">MEETING</span>
                    </div>

                    <div className="meeting-details">
                      <h3>{meeting.title || "Untitled meeting"}</h3>

                      <p className="meeting-meta">
                        <span aria-hidden="true">🕒</span>
                        <span>{formatMeetingDate(meeting.meeting_date)}</span>
                      </p>

                      {meeting.duration_minutes != null && (
                        <p className="meeting-meta">
                          <span aria-hidden="true">⏱</span>
                          <span>{meeting.duration_minutes} minutes</span>
                        </p>
                      )}

                      <div className="meeting-participants">
                        <strong>Participants</strong>
                        <p>
                          {Array.isArray(meeting.participants)
                            ? meeting.participants
                                .map((participant) => {
                                  if (typeof participant === "string") {
                                    return participant;
                                  }

                                  return (
                                    participant.name ||
                                    participant.participant_name ||
                                    participant.user_name ||
                                    participant.participant_id ||
                                    participant.user_id ||
                                    ""
                                  );
                                })
                                .filter(Boolean)
                                .join(", ") || "Not specified"
                            : "Not specified"}
                        </p>
                      </div>
                    </div>

                    <button
                      type="button"
                      className="meeting-open-chat"
                      onClick={() => handleOpenMeetingRoom(meeting)}
                    >
                      Open conversation <span aria-hidden="true">→</span>
                    </button>
                  </article>
                ))}
              </div>
            )}
          </section>
        </main>
      )}
    </div>
  );
}

export default Dashboard;
