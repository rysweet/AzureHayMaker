# Tips & Tricks - Azure HayMaker

**Helpful shortcuts and best practices**

---

## 🚀 Quick Commands

### See Everything at Once
```bash
# One-line session summary
./scripts/show-session-summary.sh
```

### Open Multiple Things
```bash
# Open PowerPoint and verify security in parallel
./scripts/open-powerpoint.sh & ./scripts/verify-security-fix.sh
```

### Chain Commands
```bash
# Health check then estimate costs
./scripts/health-check.sh && ./scripts/estimate-costs.sh
```

---

## 📁 Navigation Shortcuts

### Jump to Key Files
```bash
# Fastest way to value
cat START_HERE.md | less

# Complete guide
cat MASTER_TREASURE_MAP.md | less

# Cost alert
cat CRITICAL_COST_ALERT.md | less
```

### Find Documentation
```bash
# List all guides
ls -1 *.md | sort

# Search docs
grep -r "keyword" *.md
```

---

## 🔧 Script Tips

### Make All Executable
```bash
./scripts/update-all-scripts.sh
```

### Run All Checks
```bash
# Complete validation
./scripts/health-check.sh
./scripts/verify-security-fix.sh
./scripts/check-infrastructure.sh
```

### Backup Before Cleanup
```bash
# Backup secret names first
./scripts/backup-key-vault-secrets.sh

# Then cleanup
./scripts/complete-cleanup.sh
```

---

## 💰 Cost Optimization

### See Costs Before Cleanup
```bash
# Estimate current
./scripts/estimate-costs.sh > costs-before.txt

# Run cleanup
./scripts/complete-cleanup.sh

# Estimate after  
./scripts/estimate-costs.sh > costs-after.txt

# Compare
diff costs-before.txt costs-after.txt
```

### Monitor Costs
```bash
# Add to crontab for daily cost reports
0 9 * * * cd /path/to/repo && ./scripts/estimate-costs.sh | mail -s "Daily Costs" you@example.com
```

---

## 📊 Monitoring Tips

### Regular Health Checks
```bash
# Add to crontab
0 */6 * * * cd /path/to/repo && ./scripts/health-check.sh >> /var/log/haymaker-health.log
```

### Watch Logs
```bash
# Tail health check log
tail -f /var/log/haymaker-health.log
```

---

## 🎨 PowerPoint Tips

### Extract Slides as PDF
```bash
# If you have LibreOffice installed
soffice --headless --convert-to pdf docs/presentations/Azure_HayMaker_Overview.pptx
```

### Share Easily
```bash
# Copy to shared location
cp docs/presentations/Azure_HayMaker_Overview.pptx /path/to/shared/
```

---

## 🔒 Security Best Practices

### Verify After Changes
```bash
# Always verify after any deployment
./scripts/verify-security-fix.sh
```

### Backup Secrets
```bash
# Before making Key Vault changes
./scripts/backup-key-vault-secrets.sh
```

### Check Access
```bash
# Verify RBAC
az role assignment list --resource-group haymaker-dev-rg --assignee <principal-id>
```

---

## 🐛 Debugging Tips

### Check Infrastructure Health
```bash
./scripts/health-check.sh
```

### List All Resources
```bash
./scripts/list-all-resources.sh | grep ERROR
```

### View Recent Deployments
```bash
gh run list --limit 10
```

---

## 📚 Documentation Tips

### Quick Reference
```bash
# Bookmark these
cat QUICK_WINS.md           # Fast value
cat TROUBLESHOOTING.md      # Common issues
cat FAQ.md                  # Questions answered
```

### Search All Docs
```bash
# Find anything
grep -r "search term" *.md | less
```

### Generate Documentation
```bash
# Tree view
tree -L 2 -I 'node_modules|.git'
```

---

## ⚡ Performance Tips

### Parallel Execution
```bash
# Run multiple scripts in parallel
./scripts/health-check.sh & \
./scripts/estimate-costs.sh & \
wait
```

### Batch Operations
```bash
# Check all resources
for script in scripts/*.sh; do
  echo "Running $script..."
  $script
done
```

---

## 🎯 Workflow Tips

### Daily Routine
```bash
# Morning check
./scripts/health-check.sh
./scripts/estimate-costs.sh

# Review issues
gh issue list
```

### Weekly Review
```bash
# See what changed
git log --oneline --since="1 week ago"

# Check costs trend
./scripts/estimate-costs.sh
```

---

## 💡 Pro Tips

1. **Use tab completion** for script names
2. **Alias common commands** in your shell
3. **Bookmark MASTER_TREASURE_MAP.md** for quick reference
4. **Run health checks before/after changes**
5. **Keep documentation updated**

---

**Discover your own tips and share them!**

🏴‍☠️ Fair winds! ⚓
