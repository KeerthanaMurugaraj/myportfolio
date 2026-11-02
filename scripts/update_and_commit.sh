#!/usr/bin/env bash
# Refresh scholar.json and push it if the numbers changed.
# Run by the GitHub workflow every day and by a weekly job on Keerthana's Mac.
# Google Scholar often blocks GitHub's servers; a blocked fetch is only a warning,
# so the run stays green and the next one tries again.
set -euo pipefail
cd "$(dirname "$0")/.."

git pull --rebase --autostash --quiet

if ! python3 scripts/update_scholar.py; then
  if [ -n "${GITHUB_ACTIONS:-}" ]; then
    echo "::warning::Google Scholar blocked the request; scholar.json left unchanged."
  else
    echo "Google Scholar blocked the request; scholar.json left unchanged."
  fi
  exit 0
fi

# The date alone changing is not worth a commit.
if git diff --quiet -I '"as_of"' -- scholar.json; then
  echo "No change in publications or citations."
  git checkout -- scholar.json
  exit 0
fi

if [ -n "${GITHUB_ACTIONS:-}" ]; then
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
elif ! git config user.email >/dev/null; then
  git config user.name "Keerthana Murugaraj"
  git config user.email "161293737+KeerthanaMurugaraj@users.noreply.github.com"
fi
git commit --quiet -m "Update Google Scholar numbers" scholar.json
git push --quiet
echo "Pushed the new Scholar numbers."
