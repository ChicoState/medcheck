import { useCallback, useEffect, useRef, useState } from "react";
import {
  AuthError,
  requestSession,
  type AuthErrors,
  type Credentials,
  type Session,
} from "./api";

export function useAuth() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionError, setSessionError] = useState(false);
  const [busy, setBusy] = useState(false);
  const requestVersion = useRef(0);

  const restore = useCallback(async () => {
    const version = ++requestVersion.current;
    setLoading(true);
    setSessionError(false);
    try {
      const restored = await requestSession("session");
      if (version === requestVersion.current) setSession(restored);
    } catch {
      if (version === requestVersion.current) setSessionError(true);
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void restore();
    return () => {
      requestVersion.current++;
    };
  }, [restore]);

  async function submit(
    action: "register" | "login" | "logout",
    credentials?: Credentials,
  ): Promise<AuthErrors | null> {
    const version = ++requestVersion.current;
    setBusy(true);
    try {
      const updated = await requestSession(
        action,
        session?.csrfToken,
        credentials,
      );
      if (version === requestVersion.current) setSession(updated);
      return null;
    } catch (error) {
      if (error instanceof AuthError) {
        if (error.status === 403) {
          await restore();
          return {
            non_field_errors: ["Your session changed. Please try again."],
          };
        }
        return error.errors;
      }
      return { non_field_errors: ["Unable to connect. Please try again."] };
    } finally {
      setBusy(false);
    }
  }

  return {
    user: session?.user ?? null,
    loading,
    sessionError,
    busy,
    restore,
    submit,
  };
}

export type Auth = ReturnType<typeof useAuth>;
