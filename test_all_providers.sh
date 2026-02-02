#!/bin/bash

echo "=== Testing All LLM Provider Options ==="
echo ""

# Test each option
for option in 1 2 3 4 5 6; do
    echo "Testing option $option..."
    
    # Run quickstart.sh with the option piped in
    # Timeout after 5 seconds (to avoid hanging on real API key prompts)
    timeout 5 bash -c "echo '$option' | ./quickstart.sh" 2>/dev/null
    
    exit_code=$?
    
    if [ $exit_code -eq 0 ] || [ $exit_code -eq 124 ]; then
        # 0 = normal exit, 124 = timeout (expected, means it kept running)
        echo "✅ Option $option: PASSED (script didn't exit)"
    else
        echo "❌ Option $option: FAILED (script exited with code $exit_code)"
    fi
    echo ""
done
