#!/bin/bash
# Quick script to open the PowerPoint presentation

PPTX="docs/presentations/Azure_HayMaker_Overview.pptx"

if [ -f "$PPTX" ]; then
  echo "🎊 Opening Azure HayMaker PowerPoint Presentation..."
  echo "File: $PPTX"
  echo "Size: $(ls -lh $PPTX | awk '{print $5}')"
  echo ""
  open "$PPTX"
  echo "✅ PowerPoint opened!"
else
  echo "❌ PowerPoint not found at: $PPTX"
  exit 1
fi
