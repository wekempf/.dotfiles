# npm global packages installed under user-owned prefix (avoids sudo/EACCES)
if [[ -d "$HOME/.npm-global/bin" ]]; then
  path=("$HOME/.npm-global/bin" $path)
fi
