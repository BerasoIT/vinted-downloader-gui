#!/bin/bash

# Script per creare una release su GitHub
# Usage: ./release.sh v0.1.0

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "❌ Specifica la versione: ./release.sh v0.1.0"
    exit 1
fi

echo "🚀 Preparing release $VERSION..."

# Verifica che sia tutto committato
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Ci sono modifiche non committate. Commit prima di creare la release."
    git status --short
    exit 1
fi

# Crea il tag
echo "🏷️  Creating tag $VERSION..."
git tag -a $VERSION -m "Release $VERSION"

# Push del tag
echo "📤 Pushing tag to GitHub..."
git push origin $VERSION

echo "✅ Tag $VERSION creato e inviato!"
echo ""
echo "Prossimi passi:"
echo "1. Vai su https://github.com/BerasoIT/vinted-downloader-gui/actions"
echo "2. Verifica che il workflow 'Build and Release' sia in esecuzione"
echo "3. Una volta completato, la release sarà disponibile automaticamente"
echo ""
echo "🔗 Link diretto alla release:"
echo "   https://github.com/BerasoIT/vinted-downloader-gui/releases/tag/$VERSION"
