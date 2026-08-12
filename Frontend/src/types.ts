// TypeScript mirrors of the backend's Pydantic response schemas.

export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  created_at: string;
}

export interface Source {
  id: number;
  name: string;
  slug: string;
  url: string | null;
  category_id: number | null;
  category: Category | null;
  description: string | null;
  logo_url: string | null;
  language: string;
  country: string;
  is_active: boolean;
  created_at: string;
}

export interface Article {
  id: number;
  title: string;
  slug: string;
  summary: string | null;
  content: string | null;
  url: string | null;
  image_url: string | null;
  author: string | null;
  source_id: number | null;
  source: Source | null;
  category_id: number | null;
  category: Category | null;
  published_at: string;
  is_featured: boolean;
  is_breaking: boolean;
  views: number;
  ai_summary: string | null;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  is_superuser: boolean;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Bookmark {
  id: number;
  user_id: number;
  article: Article;
  created_at: string;
}

export interface DiscoveryRun {
  id: number;
  trigger: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  error_code: string | null;
  imported: number;
  skipped: number;
  categories: string[];
  message: string | null;
}

export interface DiscoveryStatus {
  configured: boolean;
  provider: string;
  auto_fetch_enabled: boolean;
  fetch_interval_minutes: number;
  last_run: DiscoveryRun | null;
}

export type ArticleSort = "newest" | "oldest" | "popular" | "title";

export interface ArticleQuery {
  q?: string;
  category?: string;
  source_id?: number;
  featured?: boolean;
  breaking?: boolean;
  from_date?: string;
  to_date?: string;
  sort?: ArticleSort;
  page?: number;
  size?: number;
}

export interface RegisterPayload {
  email: string;
  username: string;
  password: string;
  full_name?: string | null;
}

export interface ArticleSummary {
  summary: string;
  model: string;
  cached: boolean;
}

