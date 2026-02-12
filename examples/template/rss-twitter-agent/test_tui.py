"""
TUI Testing Interface for RSS-Twitter Agent
Tests agent through Terminal User Interface
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agent import RSSTwitterAgent


def print_header():
    """Print TUI header."""
    print("\n" + "="*60)
    print("  RSS-to-Twitter Agent - TUI Test Interface")
    print("="*60 + "\n")


def print_menu():
    """Print menu options."""
    print("Options:")
    print("  1. Run agent (fetch latest)")
    print("  2. Run with keyword filter")
    print("  3. Show configuration")
    print("  4. Test single feed")
    print("  5. Exit")
    print()


def run_agent_test(keyword: str = None):
    """Run agent and display results."""
    print(f"\n🚀 Running agent (keyword: {keyword or 'None'})...")
    
    agent = RSSTwitterAgent()
    results = agent.run(keyword=keyword)
    
    if not results:
        print("❌ No results found")
        return
    
    print(f"\n✅ Generated {len(results)} threads:\n")
    
    for i, result in enumerate(results, 1):
        print(f"--- Thread {i} ---")
        print(f"Source: {result['source']}")
        print(f"Article: {result['article_title'][:60]}...")
        print(f"Tweets: {result['tweet_count']}")
        print(f"Preview: {result['thread'][0][:80]}...")
        print()


def show_config():
    """Display current configuration."""
    agent = RSSTwitterAgent()
    config = agent.config
    
    print("\n📋 Current Configuration:")
    print(f"  Agent: {config['agent']['name']}")
    print(f"  Version: {config['agent']['version']}")
    print(f"  Tone: {config['twitter']['tone']}")
    print(f"  Max Articles: {config['rss']['max_articles']}")
    print(f"  Feeds: {len(config['rss']['feeds'])} configured")
    for feed in config['rss']['feeds']:
        print(f"    - {feed}")
    print()


def main():
    """Main TUI loop."""
    print_header()
    
    while True:
        print_menu()
        choice = input("Select option (1-5): ").strip()
        
        if choice == "1":
            run_agent_test()
        elif choice == "2":
            keyword = input("Enter keyword: ").strip()
            run_agent_test(keyword=keyword)
        elif choice == "3":
            show_config()
        elif choice == "4":
            print("\n⚠️  Single feed test not implemented yet")
        elif choice == "5":
            print("\n👋 Exiting TUI...\n")
            break
        else:
            print("\n❌ Invalid option\n")


if __name__ == "__main__":
    main()