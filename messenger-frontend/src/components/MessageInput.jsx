import { useEffect, useRef, useState } from "react";

function MessageInput({
  onSend,
  editingMessage,
  editContent,
  setEditContent,
  onEdit,
  onCancelEdit,
}) {
  const [content, setContent] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (editingMessage) {
      setContent(editingMessage.content);

      inputRef.current?.focus();
    } else {
      setContent("");
    }
  }, [editingMessage]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!content.trim()) {
      return;
    }

    if (editingMessage) {
      setEditContent(content);

      await onEdit();

      return;
    }

    onSend(content);

    setContent("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Escape" && editingMessage) {
      e.preventDefault();

      onCancelEdit();

      return;
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();

      e.currentTarget.form.requestSubmit();
    }
  };

  return (
    <form className="message-input" onSubmit={handleSubmit}>
      <input
        ref={inputRef}
        type="text"
        placeholder={editingMessage ? "Edit message..." : "Type a message..."}
        value={content}
        onChange={(e) => {
          setContent(e.target.value);

          if (editingMessage) {
            setEditContent(e.target.value);
          }
        }}
        onKeyDown={handleKeyDown}
        onBlur={() => {
          if (editingMessage) {
            onCancelEdit();
          }
        }}
      />

      <button type="submit">{editingMessage ? "Update" : "Send"}</button>
    </form>
  );
}

export default MessageInput;
