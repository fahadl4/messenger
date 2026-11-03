import { useEffect, useRef, useState } from "react";

function MessageList({
  messages,
  currentUserId,
  onStartEdit,
  onDeleteForMe,
  onDeleteForEveryone,
}) {
  const [openMenuId, setOpenMenuId] = useState(null);

  const messagesEndRef = useRef(null);

  // Store the previous number of messages
  const previousMessageCount = useRef(messages.length);

  const toggleMenu = (messageId) => {
    if (openMenuId === messageId) {
      setOpenMenuId(null);
    } else {
      setOpenMenuId(messageId);
    }
  };

  useEffect(() => {
    // Chat was opened / messages were loaded
    if (previousMessageCount.current === 0 && messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({
        behavior: "auto",
      });
    }

    // A new message was added
    if (messages.length > previousMessageCount.current) {
      messagesEndRef.current?.scrollIntoView({
        behavior: "smooth",
      });
    }

    // Update previous message count
    previousMessageCount.current = messages.length;
  }, [messages]);

  const handleEdit = (message) => {
    console.log("MESSAGE LIST EDIT:", message);

    setOpenMenuId(null);
    onStartEdit(message);
  };

  return (
    <div className="message-list">
      {messages.map((message) => {
        const isMine = message.sender_id === currentUserId;

        const isDeletedForEveryone = message.deleted_for_everyone_at !== null;

        return (
          <div
            key={message.id}
            className={`message-row ${isMine ? "mine" : "theirs"}`}
          >
            <div className="message-bubble">
              {isDeletedForEveryone ? (
                <span>Message Has Been Deleted</span>
              ) : (
                <>
                  <span>{message.content}</span>

                  <button
                    className="message-menu-button"
                    onClick={() => toggleMenu(message.id)}
                  >
                    ⋮
                  </button>

                  {openMenuId === message.id && (
                    <div className="message-menu">
                      {isMine && (
                        <button onClick={() => handleEdit(message)}>
                          Edit
                        </button>
                      )}

                      <button onClick={() => onDeleteForMe(message.id)}>
                        Delete for me
                      </button>

                      {isMine && (
                        <button onClick={() => onDeleteForEveryone(message.id)}>
                          Delete for everyone
                        </button>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        );
      })}

      <div ref={messagesEndRef} />
    </div>
  );
}

export default MessageList;
