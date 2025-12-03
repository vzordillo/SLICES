# How to Push to GitHub

## Current Status

- **Remote**: Already configured → `https://github.com/vzordillo/SLICES.git`
- **Current Branch**: `feature/testing-and-organization`
- **Safety Tags**: 19 checkpoints + v2.0.12-working + v2.1.0-rc1

## Authentication Options

### Option 1: Personal Access Token (Recommended for HTTPS)

1. **Create a Personal Access Token**:
   - Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token (classic)"
   - Give it a name (e.g., "SLICES Development")
   - Select scopes: `repo` (full control of private repositories)
   - Copy the token (you won't see it again!)

2. **Push using the token**:
   ```bash
   # When prompted for password, use the token instead
   git push origin feature/testing-and-organization
   ```

   Or set it in the URL:
   ```bash
   git remote set-url origin https://YOUR_TOKEN@github.com/vzordillo/SLICES.git
   git push origin feature/testing-and-organization
   ```

### Option 2: SSH (Recommended for frequent use)

1. **Check if you have SSH keys**:
   ```bash
   ls -la ~/.ssh/id_*.pub
   ```

2. **If no SSH key, generate one**:
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   # Press Enter to accept default location
   # Optionally set a passphrase
   ```

3. **Add SSH key to GitHub**:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   # Copy the output
   ```
   - Go to GitHub → Settings → SSH and GPG keys → New SSH key
   - Paste the key and save

4. **Change remote to SSH**:
   ```bash
   git remote set-url origin git@github.com:vzordillo/SLICES.git
   ```

5. **Test connection**:
   ```bash
   ssh -T git@github.com
   # Should see: "Hi vzordillo! You've successfully authenticated..."
   ```

## Push Commands

### Push the Feature Branch

```bash
# Push branch to GitHub
git push -u origin feature/testing-and-organization
```

### Push All Tags

```bash
# Push all tags (including checkpoints)
git push origin --tags

# Or push specific tags
git push origin v2.0.12-working
git push origin v2.1.0-rc1
git push origin checkpoint-phase0-initial
# ... etc
```

### Push Everything at Once

```bash
# Push branch and all tags
git push -u origin feature/testing-and-organization
git push origin --tags
```

## Push Backup Branch (Optional)

```bash
# Push the backup branch too
git push origin backup/pre-refactor-20251127
```

## Verify on GitHub

After pushing:
1. Go to https://github.com/vzordillo/SLICES
2. You should see the new branch: `feature/testing-and-organization`
3. Go to "Releases" or "Tags" to see all the checkpoint tags

## Troubleshooting

### Authentication Failed
- Make sure you're using a token (not password) for HTTPS
- For SSH, verify key is added to GitHub: `ssh -T git@github.com`

### Permission Denied
- Check that you have write access to the repository
- Verify the remote URL is correct: `git remote -v`

### Branch Already Exists
- If branch exists on GitHub, use: `git push -u origin feature/testing-and-organization --force-with-lease`
- `--force-with-lease` is safer than `--force` as it checks for remote changes

