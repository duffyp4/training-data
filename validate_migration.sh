#!/bin/bash
# Quick validation script to check migration success

echo "🔍 Validating Garmin Migration Results..."
echo

echo "📊 Activity Count Check:"
echo "  Before migration: 40+ activities expected"
echo "  Current count: $(grep -c '"identifier"' index.md) activities"
echo

echo "🔄 ID Transition Check:"
echo "  Current last_id.json:"
cat data/last_id.json
echo

echo "📈 Latest Activity Check:"
echo "  Latest activity in index.md:"
head -20 index.md | grep '"identifier"' | head -1
echo

echo "🎯 Strava Activity Preservation Check:"
echo "  Original Strava activity still present:"
if grep -q '"identifier": "14973422256"' index.md; then
  echo "  ✅ Found: Original activity 14973422256 preserved"
else
  echo "  ❌ Missing: Original activity 14973422256 not found"
fi
echo

echo "📝 Recent GitHub Commits:"
echo "  Last 3 commits:"
git log --oneline -3
echo

echo "✅ Validation complete!" 