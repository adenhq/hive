import { useEffect, useRef, useCallback, useState } from "react";
import { io, Socket } from "socket.io-client";
import { useQueryClient } from "@tanstack/react-query";
import { useAgentControlStore } from "@/stores/agentControlStore";
import { useNotificationStore } from "@/stores/notificationStore";
import type { LLMEventsBatch, PolicyUpdate, AgentStatus } from "@/types/agentControl";

interface AlertMessage {
  type: "alert";
  alert: {
    budget_id: string;
    budget_name: string;
    threshold: number;
    current_percentage: number;
    spent: number;
    limit: number;
    action?: string;
    reason?: string;
    model?: string;
    provider?: string;
    notifications: {
      inApp: boolean;
      email: boolean;
      emailRecipients: string[];
      webhook: boolean;
    };
  };
}

const HIVE_URL = import.meta.env.VITE_API_URL || "http://localhost:4000";

/**
 * WebSocket hook for real-time LLM events and policy updates.
 * Connects to the control WebSocket and handles event routing.
 */
export function useControlSocket() {
  const socketRef = useRef<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const agentStatus = useAgentControlStore((state) => state.agentStatus);

  const connect = useCallback(() => {
    // Check existence, not connected state - prevents duplicate connections during connecting phase
    if (socketRef.current) return;

    const token = localStorage.getItem("token");

    socketRef.current = io(`${HIVE_URL}/v1/control/ws`, {
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      transports: ["websocket"],
      auth: {
        token: token,
      },
    });

    socketRef.current.on("connect", () => {
      setConnectionError(null);
      // 1-second delay before subscribing (matches Vue implementation)
      setTimeout(() => {
        socketRef.current?.emit("subscribe-llm-events", {});
      }, 1000);
    });

    socketRef.current.on("disconnect", () => {
      setIsConnected(false);
    });

    socketRef.current.on("connect_error", (error) => {
      setConnectionError(error.message);
    });

    // Handle all message types via unified 'message' event (matches backend)
    socketRef.current.on(
      "message",
      (data: LLMEventsBatch | PolicyUpdate | { type: string }) => {
        // Get store functions at message time to avoid stale closures and dependency issues
        const { addEvents, setAgentStatus } = useAgentControlStore.getState();
        const { addNotification } = useNotificationStore.getState();

        if ("type" in data && data.type === "subscribed") {
          // Subscription confirmed
          setIsConnected(true);
        } else if ("type" in data && data.type === "agent-status") {
          // Agent status update from WebSocket
          setAgentStatus(data as unknown as AgentStatus);
        } else if ("events" in data) {
          // LLMEventsBatch - add to events buffer
          addEvents((data as LLMEventsBatch).events);
        } else if ("type" in data && data.type === "policy") {
          // PolicyUpdate - invalidate budget queries
          queryClient.invalidateQueries({ queryKey: ["budgets"] });
        } else if ("type" in data && data.type === "alert") {
          // Budget alert - show in-app notification if enabled
          const alertData = (data as AlertMessage).alert;
          if (alertData.notifications?.inApp) {
            addNotification({
              type: "budget",
              title: `Budget Alert: ${alertData.budget_name}`,
              message: alertData.action
                ? `Action "${alertData.action}" triggered. ${alertData.reason || ""}`
                : `${alertData.threshold}% threshold reached (${alertData.current_percentage.toFixed(1)}% spent)`,
              metadata: {
                budgetId: alertData.budget_id,
                threshold: alertData.threshold,
                spent: alertData.spent,
                limit: alertData.limit,
              },
            });
          }
        }
      }
    );
  }, [queryClient]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.removeAllListeners();
      socketRef.current.disconnect();
      socketRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  // Derived agent status values
  const hasActiveAgents = agentStatus?.active === true && (agentStatus?.count ?? 0) > 0;
  const agentCount = agentStatus?.count ?? 0;

  return {
    connect,
    disconnect,
    isConnected,
    connectionError,
    hasActiveAgents,
    agentCount,
  };
}
