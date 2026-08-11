import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

// Tracks whether the current article is bookmarked and toggles it.
// Redirects to /login when an unauthenticated user tries to save.
export function useBookmark(articleId: number) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [isSaved, setIsSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!user) {
      setIsSaved(false);
      return;
    }
    api
      .get<{ items: { article_id?: number; article?: { id: number } }[] }>(
        `/bookmarks?size=100`,
      )
      .then((page) => {
        if (cancelled) return;
        setIsSaved(
          page.items.some((b) => b.article?.id === articleId || b.article_id === articleId),
        );
      })
      .catch(() => {
        /* ignore — treat as unsaved */
      });
    return () => {
      cancelled = true;
    };
  }, [user, articleId]);

  const toggle = useCallback(async () => {
    if (!user) {
      navigate("/login");
      return;
    }
    setBusy(true);
    try {
      if (isSaved) {
        await api.delete(`/bookmarks/${articleId}`);
        setIsSaved(false);
      } else {
        await api.post(`/bookmarks/${articleId}`);
        setIsSaved(true);
      }
    } catch {
      /* keep current state on failure */
    } finally {
      setBusy(false);
    }
  }, [user, isSaved, articleId, navigate]);

  return { isSaved, busy, toggle };
}
