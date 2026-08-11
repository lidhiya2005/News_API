import { useSearchParams } from "react-router-dom";
import ArticleFeed from "../components/ArticleFeed";

export default function SearchPage() {
  const [searchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";

  return (
    <div className="page">
      <div className="container">
        <ArticleFeed showHeader />
        {!q && (
          <p className="hint">Tip: use the search box in the top bar or the feed above.</p>
        )}
      </div>
    </div>
  );
}
