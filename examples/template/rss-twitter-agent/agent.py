"""
RSS-to-Twitter Agent Template
Hive Example Agent - Content Repurposing Workflow
"""

import yaml
import feedparser
from typing import List, Dict, Any
from pathlib import Path


class RSSTwitterAgent:
    """
    Template agent for RSS-to-Twitter content repurposing.
    Demonstrates multi-step workflow with clear integration points.
    """
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.feeds = self.config["rss"]["feeds"]
        self.tone = self.config["twitter"]["tone"]
    
    def _load_config(self, config_path: str = None) -> dict:
        """Load configuration from YAML."""
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def fetch_rss(self, url: str) -> List[Dict[str, Any]]:
        """Fetch and parse RSS feed. [Integration Point: RSS Source]"""
        try:
            feed = feedparser.parse(url)
            return [
                {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "source": feed.feed.get("title", "Unknown"),
                }
                for entry in feed.entries[:5]
            ]
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return []
    
    def process_content(self, article: Dict) -> Dict[str, Any]:
        """Extract key points from article. [Integration Point: Content Processor]"""
        # TODO: Replace with LLM integration for better extraction
        key_points = [
            article["title"],
            article["summary"][:200] if article["summary"] else "No summary"
        ]
        
        return {
            "title": article["title"],
            "url": article["link"],
            "source": article["source"],
            "key_points": key_points,
        }
    
    def generate_thread(self, processed: Dict) -> List[str]:
        """Generate Twitter thread. [Integration Point: Output Formatter]"""
        thread = []
        
        # Hook
        thread.append(f"🚀 {processed['title']}\n\nThread 🧵👇")
        
        # Key points
        for i, point in enumerate(processed['key_points'], 1):
            thread.append(f"{i}/ {point}")
        
        # CTA
        thread.append(f"🔗 {processed['url']}\n\nFollow for more!")
        
        return thread
    
    def run(self, keyword: str = None) -> List[Dict]:
        """
        Execute full workflow.
        
        Returns:
            List of generated threads with metadata
        """
        results = []
        
        for feed_url in self.feeds:
            articles = self.fetch_rss(feed_url)
            
            for article in articles:
                if keyword and keyword.lower() not in article["title"].lower():
                    continue
                
                processed = self.process_content(article)
                thread = self.generate_thread(processed)
                
                results.append({
                    "article_title": article["title"],
                    "source": article["source"],
                    "thread": thread,
                    "tweet_count": len(thread),
                })
        
        return results[:self.config["rss"]["max_articles"]]


if __name__ == "__main__":
    # Simple CLI test
    agent = RSSTwitterAgent()
    results = agent.run(keyword="AI")
    
    for result in results:
        print(f"\n{'='*50}")
        print(f"Article: {result['article_title']}")
        print(f"Source: {result['source']}")
        print(f"Tweets: {result['tweet_count']}")
        print(f"\nThread preview:")
        print(result['thread'][0])