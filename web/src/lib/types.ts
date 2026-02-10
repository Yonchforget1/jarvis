export interface ToolCallDetail {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  tool_calls?: ToolCallDetail[];
  timestamp: string;
  isError?: boolean;
  isStreaming?: boolean;
  streamStatus?: string;
}

export interface ToolInfo {
  name: string;
  description: string;
  parameters: {
    properties: Record<string, unknown>;
    required: string[];
  };
  category: string;
}

export interface LearningEntry {
  timestamp: string;
  category: string;
  insight: string;
  context: string;
  task_description: string;
}

export interface SystemStats {
  backend: string;
  model: string;
  tool_count: number;
  learnings_count: number;
  active_sessions: number;
  uptime_seconds: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tool_calls: number;
}

export interface User {
  id: string;
  username: string;
  email: string;
}

export interface SessionInfo {
  session_id: string;
  created_at: string;
  last_active: string;
  message_count: number;
  preview?: string;
  customName?: string;
  autoTitle?: string;
  pinned?: boolean;
}
