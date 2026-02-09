"use client";

import { useChat } from "@/hooks/use-chat";
import { ChatContainer } from "@/components/chat/chat-container";

export default function ChatPage() {
  const { messages, isLoading, sendMessage } = useChat();

  return <ChatContainer messages={messages} isLoading={isLoading} onSend={sendMessage} />;
}
