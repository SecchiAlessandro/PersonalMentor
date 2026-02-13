---
name: gog
description: Google Workspace CLI for Gmail, Calendar, Drive, Contacts, Sheets, and Docs. Use when the user needs to send emails, manage calendar events, search Drive, manage contacts, or work with Sheets and Docs.
tools: Bash, Read, Write
context: fork
---

# gog

Google Workspace CLI (`gog`) for interacting with Gmail, Calendar, Drive, Contacts, Sheets, and Docs from the command line.

Homepage: https://gogcli.sh
Install: `brew install steipete/tap/gogcli`

## Setup (one-time)

1. Import OAuth credentials:
   ```bash
   gog auth credentials /path/to/client_secret.json
   ```

2. Add an account with desired services:
   ```bash
   gog auth add you@gmail.com --services gmail,calendar,drive,contacts,docs,sheets
   ```

3. Verify:
   ```bash
   gog auth list
   ```

## Process

1. Identify which Google Workspace service the user needs (Gmail, Calendar, Drive, Contacts, Sheets, Docs)
2. For emails: compose the body, write to a temp file with `Write` if multi-line, then send with `--body-file`
3. For calendar events: confirm date/time and details before creating
4. **Always confirm with the user before sending emails, creating/updating events, or modifying sheets**
5. Use `--json` for structured output when parsing results programmatically

## Command Reference

### Gmail

**Search threads:**
```bash
gog gmail search 'newer_than:7d' --max 10
```

**Search messages (per email):**
```bash
gog gmail messages search "in:inbox from:ryanair.com" --max 20 --account you@example.com
```

**Send (plain text):**
```bash
gog gmail send --to a@b.com --subject "Hi" --body "Hello"
```

**Send (multi-line from file):**
```bash
gog gmail send --to a@b.com --subject "Hi" --body-file ./message.txt
```

**Send (from stdin):**
```bash
gog gmail send --to a@b.com --subject "Hi" --body-file -
```

**Send (HTML):**
```bash
gog gmail send --to a@b.com --subject "Hi" --body-html "<p>Hello</p>"
```

**Create draft:**
```bash
gog gmail drafts create --to a@b.com --subject "Hi" --body-file ./message.txt
```

**Send draft:**
```bash
gog gmail drafts send <draftId>
```

**Reply to a message:**
```bash
gog gmail send --to a@b.com --subject "Re: Hi" --body "Reply" --reply-to-message-id <msgId>
```

### Calendar

**List events:**
```bash
gog calendar events <calendarId> --from <iso> --to <iso>
```

**Create event:**
```bash
gog calendar create <calendarId> --summary "Title" --from <iso> --to <iso>
```

**Create event with color:**
```bash
gog calendar create <calendarId> --summary "Title" --from <iso> --to <iso> --event-color 7
```

**Update event:**
```bash
gog calendar update <calendarId> <eventId> --summary "New Title" --event-color 4
```

**Show available colors:**
```bash
gog calendar colors
```

### Drive

**Search files:**
```bash
gog drive search "query" --max 10
```

### Contacts

**List contacts:**
```bash
gog contacts list --max 20
```

### Sheets

**Get cell range:**
```bash
gog sheets get <sheetId> "Tab!A1:D10" --json
```

**Update cells:**
```bash
gog sheets update <sheetId> "Tab!A1:B2" --values-json '[["A","B"],["1","2"]]' --input USER_ENTERED
```

**Append rows:**
```bash
gog sheets append <sheetId> "Tab!A:C" --values-json '[["x","y","z"]]' --insert INSERT_ROWS
```

**Clear range:**
```bash
gog sheets clear <sheetId> "Tab!A2:Z"
```

**Get sheet metadata:**
```bash
gog sheets metadata <sheetId> --json
```

### Docs

**Export document:**
```bash
gog docs export <docId> --format txt --out /tmp/doc.txt
```

**Print document content:**
```bash
gog docs cat <docId>
```

## Email Formatting

- Prefer plain text. Use `--body-file` for multi-paragraph messages.
- `--body` does **not** unescape `\n`. Use a heredoc or `--body-file -` for newlines.
- Same `--body-file` pattern works for drafts and replies.
- Use `--body-html` only when rich formatting is needed.
- Supported HTML tags: `<p>`, `<br>`, `<strong>`, `<em>`, `<a href="url">`, `<ul>`/`<li>`.

## Calendar Color IDs

| ID | Color   |
|----|---------|
| 1  | #a4bdfc |
| 2  | #7ae7bf |
| 3  | #dbadff |
| 4  | #ff887c |
| 5  | #fbd75b |
| 6  | #ffb878 |
| 7  | #46d6db |
| 8  | #e1e1e1 |
| 9  | #5484ed |
| 10 | #51b749 |
| 11 | #dc2127 |

## Important Notes

- **Confirm before sending**: Always ask the user to confirm before sending emails, creating events, or modifying sheets.
- Set `GOG_ACCOUNT=you@gmail.com` to avoid repeating `--account` on every command.
- Use `--json` and `--no-input` for scripting and structured output.
- `gog gmail search` returns one row per **thread**; use `gog gmail messages search` for individual emails.
- Sheets values can be passed via `--values-json` (recommended) or as inline rows.
- Docs supports export/cat/copy. In-place edits require a Docs API client (not available in gog).
