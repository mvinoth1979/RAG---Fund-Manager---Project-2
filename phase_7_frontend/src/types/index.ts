export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  source_url?: string;
  last_updated?: string;
  disclaimer?: string;
  isError?: boolean;
}
