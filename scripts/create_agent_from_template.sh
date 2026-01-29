#!/usr/bin/env bash
set -e

TEMPLATE_NAME="basic_worker_agent"

if [ -z "$1" ]; then
  echo "Usage: ./create_agent_from_template.sh <new_agent_name>"
  exit 1
fi

NEW_AGENT_NAME="$1"
TEMPLATE_DIR="exports/templates/${TEMPLATE_NAME}"
TARGET_DIR="exports/${NEW_AGENT_NAME}"

if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "${RED}✗${NC} Template not found: $TEMPLATE_DIR"
  exit 1
fi

if [ -d "$TARGET_DIR" ]; then
  echo "${RED}✗${NC} Target agent already exists: $TARGET_DIR"
  exit 1
fi

echo "Creating agent '$NEW_AGENT_NAME' from template..."

cp -r "$TEMPLATE_DIR" "$TARGET_DIR"

# Optional: rename internal references
grep -rl "$TEMPLATE_NAME" "$TARGET_DIR" | xargs sed -i "s/${TEMPLATE_NAME}/${NEW_AGENT_NAME}/g"

echo "${GREEN}✓${NC} Agent created at $TARGET_DIR"
echo
echo "Next steps:"
echo "  cd $TARGET_DIR"
echo "  python -m ${NEW_AGENT_NAME} info"
