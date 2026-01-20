#!/bin/bash
# Script to set GitHub repository topics for adenhq/hive
# Run this script after installing GitHub CLI: https://cli.github.com/

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI (gh) is not installed."
    echo "Install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "Please authenticate with GitHub CLI first:"
    echo "  gh auth login"
    exit 1
fi

# Set the repository topics
TOPICS="ai-agents,autonomous-agents,multi-agent-systems,agent-framework,agentic-ai,self-improving,self-evolving,llm,openai,anthropic,claude,python,typescript,human-in-the-loop,observability,open-source,production-ready,docker,mcp,generative-ai"

echo "Setting GitHub topics for adenhq/hive..."
gh repo edit adenhq/hive --add-topic "$TOPICS"

echo "Done! Topics have been added to the repository."
echo ""
echo "Topics added:"
echo "$TOPICS" | tr ',' '\n' | sed 's/^/  - /'
