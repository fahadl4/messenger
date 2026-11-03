import { useState } from "react";
import "./ChatList.css";

function ChatList({
  rooms,
  selectedRoom,
  onSelectRoom,
  onAddChat,
  onDeleteChat,
  onCreateGroup,
  availableUsers,
  selectedMemberIds,
  setSelectedMemberIds,
  groupName,
  setGroupName,
  showGroupForm,
  setShowGroupForm,
  groupError,
  groupLoading,
  onLoadUsers,
}) {
  const [showMenu, setShowMenu] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [email, setEmail] = useState("");
  const [searchError, setSearchError] = useState("");

  const handleSearch = async (event) => {
    event.preventDefault();

    if (!email.trim()) return;

    setSearchError("");

    try {
      await onAddChat(email.trim());
      setEmail("");
      setShowSearch(false);
      setShowMenu(false);
    } catch (error) {
      setSearchError(
        error.response?.data?.detail || "Could not find this user.",
      );
    }
  };

  const handleOpenGroupForm = async () => {
    setShowMenu(false);
    setShowSearch(false);
    setShowGroupForm(true);
    await onLoadUsers();
  };

  const handleMemberChange = (userId, checked) => {
    setSelectedMemberIds((previousIds) =>
      checked
        ? [...previousIds, userId]
        : previousIds.filter((id) => id !== userId),
    );
  };

  return (
    <div className="chat-list">
      <div className="chat-list-header">
        <h2>Chats</h2>

        <button
          className="add-chat-button"
          type="button"
          onClick={() => setShowMenu((previous) => !previous)}
          title="Create a chat"
          aria-label="Create a chat"
        >
          +
        </button>
      </div>

      {showMenu && (
        <div className="chat-create-menu">
          <button
            type="button"
            onClick={() => {
              setShowMenu(false);
              setShowGroupForm(false);
              setShowSearch(true);
            }}
          >
            New private chat
          </button>

          <button type="button" onClick={handleOpenGroupForm}>
            New group
          </button>
        </div>
      )}

      {showSearch && (
        <form className="chat-search" onSubmit={handleSearch}>
          <input
            type="email"
            placeholder="Email address"
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
              setSearchError("");
            }}
            required
          />

          <button type="submit">Search</button>
        </form>
      )}

      {showSearch && searchError && (
        <p className="search-error">{searchError}</p>
      )}

      {showGroupForm && (
        <form className="group-create-form" onSubmit={onCreateGroup}>
          <h3>Create group</h3>

          <label htmlFor="group-name">Group name</label>
          <input
            id="group-name"
            type="text"
            value={groupName}
            onChange={(event) => setGroupName(event.target.value)}
            placeholder="Enter group name"
            maxLength={100}
            required
          />

          <p className="group-select-label">Select members</p>

          <div className="group-user-list">
            {availableUsers.length === 0 ? (
              <p className="group-no-users">No other users available.</p>
            ) : (
              availableUsers.map((availableUser) => (
                <label className="group-user-option" key={availableUser.id}>
                  <input
                    type="checkbox"
                    checked={selectedMemberIds.includes(availableUser.id)}
                    onChange={(event) =>
                      handleMemberChange(availableUser.id, event.target.checked)
                    }
                  />

                  <span>
                    <strong>{availableUser.name}</strong>
                    <small>{availableUser.email}</small>
                  </span>
                </label>
              ))
            )}
          </div>

          {groupError && <p className="search-error">{groupError}</p>}

          <div className="group-form-actions">
            <button type="submit" disabled={groupLoading}>
              {groupLoading ? "Creating..." : "Create group"}
            </button>

            <button
              type="button"
              onClick={() => {
                setShowGroupForm(false);
                setGroupName("");
                setSelectedMemberIds([]);
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {rooms.length === 0 ? (
        <p className="empty-chats">No conversations yet.</p>
      ) : (
        rooms.map((room) => {
          const isGroup = room.is_group;

          const chatName = isGroup
            ? room.name || "Unnamed group"
            : room.other_user_name || "Unknown user";

          return (
            <div
              key={room.id}
              className={`chat-item ${
                selectedRoom?.id === room.id ? "selected" : ""
              } ${isGroup ? "group-chat-item" : ""}`}
            >
              <div
                className="chat-item-content"
                role="button"
                tabIndex={0}
                onClick={() => onSelectRoom(room)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectRoom(room);
                  }
                }}
              >
                {isGroup ? (
                  <div className="chat-avatar group-chat-avatar">👥</div>
                ) : room.other_user_avatar_url ? (
                  <img
                    src={`http://127.0.0.1:8000${room.other_user_avatar_url}`}
                    alt={`${chatName}'s avatar`}
                    className="chat-avatar"
                  />
                ) : (
                  <div className="chat-avatar">
                    {chatName.charAt(0).toUpperCase()}
                  </div>
                )}

                <div className="chat-info">
                  <strong>{chatName}</strong>

                  {isGroup && (
                    <span className="group-member-count">
                      {room.member_count} members
                    </span>
                  )}

                  <p>{room.last_message ?? "No messages yet"}</p>
                </div>
              </div>

              <button
                type="button"
                className="delete-chat-button"
                title="Delete conversation for me"
                aria-label={`Delete conversation with ${chatName}`}
                onClick={(event) => {
                  event.stopPropagation();
                  onDeleteChat(room.id);
                }}
              >
                ×
              </button>
            </div>
          );
        })
      )}
    </div>
  );
}

export default ChatList;
