# FYLIX Room Management Guide

## Understanding Rooms

### **Direct Chats**
- **Auto-created** when you send a file to someone via email
- Permanent between two users
- Cannot be deleted or left
- Example: `fylix send document.pdf user@email.com` creates/uses direct room

### **Group Chats**
- Manually created with `fylix create <name>`
- Support multiple members
- Have admins who can add/remove members and delete room
- Send files using room ID: `fylix sendroom <room_id> <file>`

---

## All Commands

### 📋 View All Rooms
```bash
fylix rooms
```
**Shows:**
- Room name (group name or participant username)
- Type (DIRECT/GROUP)
- Member count
- Admin (for groups)
- **7-character Room ID** (easy to type!)

**Output:**
```
Chat Rooms (2 total)
┌───────────────────┬────────┬─────────┬─────────┬─────────┐
│ Name/Participants │ Type   │ Members │ Admin   │ ID (7)  │
├───────────────────┼────────┼─────────┼─────────┼─────────┤
│ AashiJain123      │ DIRECT │ 2       │ -       │ eff3f48 │
│ Team Project      │ GROUP  │ 5       │ You     │ abc1234 │
└───────────────────┴────────┴─────────┴─────────┴─────────┘
```

---

### 🆕 Create Group Chat
```bash
# Empty group
fylix create "Team Project"

# With initial members
fylix create "Study Group" --members user1@email.com,user2@email.com
fylix create "Work Team" -m alice@email.com,bob@email.com
```

**Result:** You become the admin of the new group

---

### 👥 View Members
```bash
fylix members abc1234
```
**Shows:**
- Username
- Role (ADMIN/MEMBER)
- Join date

**For groups, also shows commands:**
- Add member
- Send file to group
- Delete room (admin only)

---

### ➕ Add Member (Admin Only)
```bash
fylix add abc1234 newuser@email.com
```
- Only group admins can do this
- Works with email, username, or user ID
- Cannot add to direct chats

---

### 🚪 Leave Group
```bash
fylix leave abc1234
```
- Only works for group chats
- Asks for confirmation
- Cannot leave direct chats (they're permanent)

---

### 🗑️ Delete Room (Admin Only)
```bash
fylix delroom abc1234
```
- Only group admins can delete
- Requires confirmation
- Cannot delete direct chats
- **Note:** Backend endpoint may need to be added

---

## Sending Files

### To Individual (Email) - Creates Direct Room
```bash
fylix send document.pdf user@email.com
```
- If no direct room exists with this user, it's **auto-created**
- If room exists, file is sent to existing room
- You don't need to create direct rooms manually

### To Group Chat (Room ID)
```bash
fylix sendroom abc1234 presentation.pptx
```
- Use 7-character room ID from `fylix rooms`
- All group members can see the file
- Shows room name before sending

---

## Quick Workflows

### Starting Fresh
```bash
# 1. See all your rooms
fylix rooms

# 2. Create a group for team
fylix create "Project Alpha" -m teammate1@email.com,teammate2@email.com

# 3. Send file to group
fylix sendroom abc1234 report.pdf

# 4. Add more members
fylix add abc1234 newmember@email.com
```

### Managing Groups
```bash
# View who's in the group
fylix members abc1234

# Send files
fylix sendroom abc1234 update.docx

# Remove yourself
fylix leave abc1234

# Delete group (admin only)
fylix delroom abc1234
```

### Direct Messaging
```bash
# Just send - room auto-creates!
fylix send secret.txt friend@email.com

# Check your direct chats
fylix rooms

# View conversation
fylix inbox 1-10
```

---

## Important Notes

1. **7-Character IDs**: All room IDs shown are shortened to 7 characters for easy typing
2. **Partial Matching**: Commands accept partial IDs (e.g., `abc` matches `abc1234`)
3. **Auto-Creation**: Direct rooms are automatically created when sending files via email
4. **Permissions**: Only group admins can add members or delete rooms
5. **Permanence**: Direct chats cannot be deleted or left (design choice for message history)

---

## Troubleshooting

**"Room not found"**
- Use `fylix rooms` to see all room IDs
- Make sure you're typing at least 7 characters
- Check for typos

**"Only room admins can..."**
- You must be the admin of a group to add members or delete
- Check `fylix rooms` to see who's admin
- Ask current admin to promote you

**"Cannot leave direct chats"**
- This is by design - direct chats are permanent
- They don't take up space and preserve message history

---

## Backend Requirements

Some features may require backend endpoints:
- `DELETE /chat/rooms/{room_id}` - Delete room (admin only)
- `DELETE /chat/rooms/{room_id}/members/{user_id}` - Remove member/leave room

If not implemented, CLI shows appropriate message.
